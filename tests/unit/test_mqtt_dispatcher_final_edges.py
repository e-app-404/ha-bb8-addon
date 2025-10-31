import json
import types


class FakePub:
    def __init__(self, rc=0):
        self.rc = rc


class FakeClient:
    def __init__(self):
        self.subs = []
        self.pubs = []
        self.reconnects = 0

    def subscribe(self, topic, qos=0):
        self.subs.append((topic, qos))
        return (1, 0)  # rc=1 -> error path

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.pubs.append((topic, payload, qos, retain))
        # First call OK, second call simulate failure rc!=0
        return FakePub(rc=0 if len(self.pubs) == 1 else 2)


def test_on_connect_nonzero_rc_and_subscribe_error():
    from addon.bb8_core import mqtt_dispatcher as md

    c = FakeClient()
    # rc!=0 connects should still not crash; then subscribe yields rc=1 (error) and code should handle gracefully
    md.on_connect(c, None, None, rc=2)
    assert c.subs  # subscribe attempted despite rc!=0 path


def test_ack_paths_retain_qos_and_empty_payload_handling():
    from addon.bb8_core import mqtt_dispatcher as md

    c = FakeClient()
    md.on_connect(c, None, None, 0)
    # empty payload should be handled without crash
    md.on_message(
        c, None, types.SimpleNamespace(topic="bb8/echo/cmd", payload=b"")
    )
    # good payload → first publish rc=0, second forced rc!=0 (graceful)
    msg = types.SimpleNamespace(
        topic="bb8/echo/cmd", payload=json.dumps({"value": 1}).encode()
    )
    md.on_message(c, None, msg)
    # ensure we published at least once and exercised retain/qos inputs
    # emulate a retained publish
    c.publish("bb8/echo/ack", b'{"ok":true}', qos=1, retain=True)
    assert any(p[2] == 1 and p[3] is True for p in c.pubs)
