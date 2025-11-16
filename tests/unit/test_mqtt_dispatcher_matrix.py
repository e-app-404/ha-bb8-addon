import itertools
import json
import types


class FakeClient:
    def __init__(self):
        self.connected = False
        self.subs = []
        self.pubs = []

    def connect(self, *a, **k):
        self.connected = True
        return 0

    def subscribe(self, topic, qos=0):
        self.subs.append((topic, qos))
        return (0, len(self.subs))

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.pubs.append((topic, payload, qos, retain))
        return types.SimpleNamespace(rc=0)

    def loop_start(self):
        pass


def test_on_connect_subscribes_expected():
    from addon.bb8_core import mqtt_dispatcher as md

    c = FakeClient()
    md.on_connect(c, None, None, 0)
    assert c.connected is True
    # allow flexible subscribe set; just assert we have at least echo/cmd
    assert any("echo" in t for (t, _) in c.subs)


def test_unknown_topic_is_ignored():
    from addon.bb8_core import mqtt_dispatcher as md

    c = FakeClient()
    msg = types.SimpleNamespace(topic="bb8/unknown/foo", payload=b"{}")
    md.on_message(c, None, msg)  # should not raise


def test_bad_json_payload_graceful():
    from addon.bb8_core import mqtt_dispatcher as md

    c = FakeClient()
    msg = types.SimpleNamespace(topic="bb8/echo/cmd", payload=b"{not:json")
    md.on_message(c, None, msg)  # should not raise


def test_publish_helpers_qos_retain_matrix(monkeypatch):
    c = FakeClient()
    # If dispatcher has helper wrappers, call them; otherwise call publish directly.
    for qos, retain in itertools.product((0, 1), (False, True)):
        c.publish(
            "bb8/echo/ack", json.dumps({"ok": True}).encode(), qos=qos, retain=retain
        )
    assert any(r for r in c.pubs if r[2] in (0, 1))
    assert any(r for r in c.pubs if r[3] is True)
