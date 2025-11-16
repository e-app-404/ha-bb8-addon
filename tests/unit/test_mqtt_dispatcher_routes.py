import types

subs: list[tuple[str, int]] = []
published = []


class FakeClient:
    def __init__(self):
        self.connected = False

    def connect(self, *a, **kw):
        self.connected = True
        return 0

    def subscribe(self, topic, qos=0):
        subs.append((topic, qos))
        return (0, 1)

    def publish(self, topic, payload=None, qos=0, retain=False):
        published.append((topic, payload, qos, retain))
        return types.SimpleNamespace(rc=0)

    def loop_start(self):
        pass


def test_connect_and_subscribe(monkeypatch):
    from addon.bb8_core import mqtt_dispatcher as md

    monkeypatch.setattr(md, "new_paho_client", lambda: FakeClient(), raising=False)
    c = md.new_paho_client()
    assert c.connect() == 0
    md.on_connect(c, None, None, 0)
    assert any(t.endswith("/echo/cmd") for t, _ in subs)


def test_on_message_echo_roundtrip(monkeypatch):
    from addon.bb8_core import mqtt_dispatcher as md

    published.clear()
    payload_seen = []

    def fake_publish(client, topic, payload, **kw):
        published.append((topic, payload))

    monkeypatch.setattr(
        md,
        "_publish_echo_ack",
        lambda client, payload: fake_publish(client, "bb8/echo/ack", payload),
    )
    # simulate message to /echo/cmd
    msg = types.SimpleNamespace(topic="bb8/echo/cmd", payload=b'{"value":1}')
    md.on_message(FakeClient(), None, msg)
    assert any(t.endswith("/echo/ack") for t, _ in published)
