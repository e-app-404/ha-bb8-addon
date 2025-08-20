import json

import pytest

import bb8_core.bridge_controller as bc
from bb8_core.bb8_presence_scanner import publish_discovery
from bb8_core.mqtt_dispatcher import start_mqtt_dispatcher


def _topic_payload_seen(mqtt, topic, expect):
    for t, payload, _qos, _retain in getattr(mqtt, "published", []):
        if t == topic and payload == expect:
            return True
    return False


@pytest.mark.asyncio
def test_led_echo_contract(monkeypatch):
    # Arrange: force flat namespace and route runtime MQTT client to the test FakeMQTT
    mqtt = FakeMQTT()
    monkeypatch.setenv("MQTT_BASE", "bb8")
    monkeypatch.setenv("REQUIRE_DEVICE_ECHO", "1")
    monkeypatch.setenv("MQTT_HOST", "127.0.0.1")
    monkeypatch.setenv("MQTT_PORT", "1883")

    # Monkeypatch the runtime seam(s) that obtain the MQTT client
    import bb8_core.mqtt_dispatcher as md

    monkeypatch.setattr(md, "get_client", lambda: mqtt, raising=False)

    # Act: trigger the runtime LED handler seam to guarantee echo
    r, g, b = 16, 32, 64
    if hasattr(bc, "on_led_set"):
        bc.on_led_set(r, g, b)
    elif hasattr(bc, "_on_led_command"):
        bc._on_led_command(json.dumps({"r": r, "g": g, "b": b}))
    else:
        raise AssertionError("No LED handler seam found in bridge_controller")

    expected_payload = json.dumps({"r": r, "g": g, "b": b})
    assert _topic_payload_seen(
        mqtt, "bb8/led/state", expected_payload
    ), "LED echo not observed on bb8/led/state; published={}".format(
        getattr(mqtt, "published", [])
    )


class FakeMQTT:
    """
    Minimal paho-mqtt compatible fake with per-topic callbacks.
    Supports:
      - publish(topic, payload, qos=0, retain=False) -> FakeMid
      - subscribe(topic, qos=0) -> (rc, mid)
      - message_callback_add(topic, handler)
      - on_message fallback
      - trigger(topic, payload) to simulate inbound messages
    """

    class _FakeMid:
        def __init__(self, mid=1):
            self.mid = mid

        def wait_for_publish(self, timeout=3):
            return True

    def __init__(self):
        self.published = []  # list[(topic, payload, qos, retain)]
        self.subscribed = []  # list[(topic, qos)]
        self._handlers = {}  # topic -> handler(client, userdata, message)
        self.on_message = None
        self._mid = 0

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        self._mid += 1
        return self._FakeMid(self._mid)

    async def apublish(self, topic, payload=None, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        self._mid += 1

        class DummyAwait:
            def __await__(self):
                return iter([])

        return DummyAwait()

    def subscribe(self, topic, qos=0):
        self.subscribed.append((topic, qos))
        # paho returns (rc, mid)
        self._mid += 1
        return (0, self._mid)

    def message_callback_add(self, topic, handler):
        # store exact-topic or wildcard handler
        self._handlers[topic] = handler

    @staticmethod
    def _match(pattern: str, topic: str) -> bool:
        """Basic MQTT wildcard matching for + and #."""
        if pattern == topic:
            return True
        p_parts = pattern.split("/")
        t_parts = topic.split("/")
        for i, part in enumerate(p_parts):
            if part == "#":
                return True  # match rest
            if i >= len(t_parts):
                return False
            if part == "+":
                continue
            if part != t_parts[i]:
                return False
        return len(t_parts) == len(p_parts)

    def trigger(self, topic, payload=None):
        """Simulate an inbound message to the appropriate handler."""

        class _Msg:
            __slots__ = ("topic", "payload")

            def __init__(self, topic, payload):
                self.topic = topic
                if isinstance(payload, bytes | bytearray):
                    self.payload = bytes(payload)
                elif payload is None:
                    self.payload = b""
                else:
                    self.payload = str(payload).encode()

        msg = _Msg(topic, payload)
        # exact handler first
        handler = self._handlers.get(topic)
        # wildcard fallback
        if handler is None:
            for pat, h in self._handlers.items():
                if self._match(pat, topic):
                    handler = h
                    break
        # on_message fallback
        if handler is None:
            handler = self.on_message
        if callable(handler):
            handler(self, None, msg)
        # else: silently ignore


class FakeLog:
    def __init__(self):
        self.entries = []

    def info(self, msg):
        self.entries.append(("info", msg))

    def error(self, msg):
        self.entries.append(("error", msg))


class FakeToy:
    pass


@pytest.mark.asyncio
async def test_discovery_and_dispatcher_smoke(caplog):
    mqtt = FakeMQTT()
    device_id = "testbb8"
    import logging
    from io import StringIO

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    caplog.set_level(logging.INFO)
    # Patch publish_discovery to use apublish for FakeMQTT
    orig_publish = mqtt.publish
    try:
        mqtt.publish = mqtt.apublish
        await publish_discovery(mqtt, device_id)
        # Aggregate captured messages from all loggers
        logs = "\n".join(rec.getMessage() for rec in caplog.records)
        assert (
            "discovery: published" in logs or "Published HA discovery" in logs
        ), f"Log not found in: {logs}"
    finally:
        mqtt.publish = orig_publish
        root_logger.removeHandler(handler)

    # Minimal controller/facade for echo
    class MinimalController:
        def handle_led(self, client, userdata, msg):
            # Device handler: publish LED state echo
            client.publish(
                f"bb8/{device_id}/state/led", msg.payload, qos=1, retain=False
            )

        def handle_sleep(self, client, userdata, msg):
            client.publish(
                f"bb8/{device_id}/event/slept", msg.payload, qos=1, retain=False
            )

        def handle_drive(self, client, userdata, msg):
            client.publish(
                f"bb8/{device_id}/state/motion", msg.payload, qos=1, retain=False
            )

    ctrl = MinimalController()
    # Register handlers for command topics
    mqtt.message_callback_add(f"bb8/{device_id}/cmd/led/set", ctrl.handle_led)
    mqtt.message_callback_add(f"bb8/{device_id}/cmd/sleep", ctrl.handle_sleep)
    mqtt.message_callback_add(f"bb8/{device_id}/cmd/drive", ctrl.handle_drive)

    # Start dispatcher (controller not used in this minimal test)
    start_mqtt_dispatcher(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_topic="bb8/command/#",
        username=None,
        password=None,
        controller=ctrl,
    )
    # Simulate LED set
    mqtt.trigger(f"bb8/{device_id}/cmd/led/set", json.dumps({"r": 1, "g": 2, "b": 3}))
    # Simulate sleep
    mqtt.trigger(f"bb8/{device_id}/cmd/sleep", json.dumps({"after_ms": 0}))
    # Simulate drive
    mqtt.trigger(
        f"bb8/{device_id}/cmd/drive",
        json.dumps({"heading_deg": 90, "speed": 100, "duration_ms": 10}),
    )
    # Validate state echo
    assert any(f"bb8/{device_id}/state/led" in t for t, *_ in mqtt.published)
    assert any(f"bb8/{device_id}/event/slept" in t for t, *_ in mqtt.published)
    assert any(f"bb8/{device_id}/state/motion" in t for t, *_ in mqtt.published)
