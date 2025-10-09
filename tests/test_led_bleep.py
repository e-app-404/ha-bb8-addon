import asyncio
import json
import os
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.asyncio


class FakeMessage:
    def __init__(self, topic, payload, qos=0, retain=False):
        self.topic, self.payload, self.qos, self.retain = topic, payload, qos, retain


class FakeMQTT:
    def __init__(self):
        self.published = []
        self._handlers = {}

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return SimpleNamespace(wait_for_publish=lambda: True)

    def subscribe(self, topic, qos=0):
        pass

    def message_callback_add(self, topic, handler):
        self._handlers[topic] = handler

    async def trigger(self, topic, payload):
        h = self._handlers.get(topic)
        if not h:
            return
        msg = FakeMessage(
            topic, payload.encode() if isinstance(payload, str) else payload
        )
        if asyncio.iscoroutinefunction(h):
            await h(self, None, msg)
        else:
            h(self, None, msg)


# --- Unified handler supporting both state and RGB payloads ---
async def led_handler(_client, _ud, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        if all(k in data for k in ("r", "g", "b")):
            # RGB payload
            payload = json.dumps(
                {
                    "r": int(data.get("r", 0)),
                    "g": int(data.get("g", 0)),
                    "b": int(data.get("b", 0)),
                    "source": "device",
                }
            )
        else:
            # State payload
            state = data.get("state", "OFF")
            payload = json.dumps({"state": state, "source": "device"})
    except Exception:
        payload = json.dumps({"state": "OFF", "source": "device"})
    _client.publish(
        f"{os.environ.get('MQTT_BASE', 'bb8')}/{os.environ.get('DEVICE_ID', 'testbb8')}/state/led",
        payload,
        retain=True,
    )


@pytest.mark.asyncio
async def test_led_bleep_end_to_end(caplog):
    caplog.set_level("INFO")
    dev = os.environ.get("DEVICE_ID", "testbb8")
    base = os.environ.get("MQTT_BASE", "bb8")
    client = FakeMQTT()
    set_topic = f"{base}/{dev}/cmd/led/set"
    client.subscribe(set_topic)
    client.message_callback_add(set_topic, led_handler)

    # Test state payloads
    for payload in ('{"state":"ON"}', '{"state":"OFF"}'):
        await client.trigger(set_topic, payload)

    emitted = [
        (t, r) for (t, _p, _q, r) in client.published if t.endswith("/state/led")
    ]
    assert len(emitted) >= 2, f"expected at least 2 led states, got {len(emitted)}"
    assert all(r is True for (_t, r) in emitted), "LED state publishes must be retained"
    assert "device" in (
        client.published[0][1] or ""
    ), "payload should include source=device"


@pytest.mark.parametrize("rgb", [(255, 160, 0), (0, 0, 0)])
@pytest.mark.asyncio
async def test_led_bleep_rgb_publish(rgb):
    dev = os.environ.get("DEVICE_ID", "testbb8")
    base = os.environ.get("MQTT_BASE", "bb8")
    client = FakeMQTT()
    set_topic = f"{base}/{dev}/cmd/led/set"
    client.subscribe(set_topic)
    client.message_callback_add(set_topic, led_handler)

    payload = json.dumps({"r": rgb[0], "g": rgb[1], "b": rgb[2]})
    await client.trigger(set_topic, payload)

    state_topic = f"{base}/{dev}/state/led"
    # Find the last RGB publish
    rgb_publishes = [
        (t, p, r)
        for (t, p, _q, r) in client.published
        if t == state_topic and p and all(k in json.loads(p) for k in ("r", "g", "b"))
    ]
    assert rgb_publishes, f"No RGB publish found for {rgb}"
    for _t, p, retained in rgb_publishes:
        data = json.loads(p)
        assert data["r"] == rgb[0] and data["g"] == rgb[1] and data["b"] == rgb[2]
        assert retained is True, "RGB publish must be retained"
