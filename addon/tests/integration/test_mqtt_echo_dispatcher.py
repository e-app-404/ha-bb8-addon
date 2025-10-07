import importlib
import json
from types import SimpleNamespace


def test_echo_roundtrip(monkeypatch):
    # Arrange: stub broker client with simple in-memory topics
    inbox, outbox = [], []

    class FakeClient:
        def __init__(self): self.on_message = None
        def connect(self, *a, **kw): return 0
        def loop_start(self): pass
        def subscribe(self, topic, qos=0): assert topic.endswith("/echo/cmd")
        def publish(self, topic, payload, qos=0, retain=False): outbox.append((topic, payload))
        def message_callback_add(self, topic, cb): self.on_message = cb
    fake = FakeClient()

    # Patch paho client factory inside module under test
    import addon.bb8_core.mqtt_dispatcher as mqttd
    monkeypatch.setattr(mqttd, "new_paho_client", lambda: fake, raising=False)

    # Act: initialize dispatcher and emulate inbound "cmd"
    if "addon.bb8_core.echo_responder" in globals():
        importlib.reload(mqttd)
    mqttd.init_echo_paths(base="bb8")  # expected in module under test
    # Emulate broker delivering a message to echo handler
    msg = SimpleNamespace(topic="bb8/echo/cmd", payload=b'{"ping":1}')
    assert callable(fake.on_message)
    fake.on_message(fake, None, msg)

    # Assert: module should publish bb8/echo/ack with JSON
    assert outbox, "No mqtt publish captured"
    topic, payload = outbox[-1]
    assert topic.endswith("/echo/ack")
    data = json.loads(payload)
    assert data.get("ok") is True