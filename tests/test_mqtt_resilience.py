import types
import logging

import bb8_core.mqtt_dispatcher as md


class FakeMID:
    def wait_for_publish(self, timeout: float = 1.0):
        return True


class FakeClient:
    def __init__(self):
        self._connected = False
        self.publishes = []

    def is_connected(self):
        return self._connected

    def set_connected(self, state: bool):
        self._connected = state

    def publish(self, topic, payload, qos=0, retain=False):
        # record and return a mid-like object
        self.publishes.append((topic, payload, qos, retain))
        return FakeMID()


def test_safe_publish_queues_offline_and_flushes(caplog):
    caplog.set_level(logging.DEBUG)
    client = FakeClient()

    # offline path: should queue and return False
    ok = md.safe_publish(client, "bb8/test", {"x": 1}, qos=0, retain=False)
    assert ok is False
    assert len(client.publishes) == 0

    # flip to connected; flush queued messages
    client.set_connected(True)
    md._flush_queue(client, max_age_s=5.0)

    # expect exactly one publish of the queued message
    # metrics may be published as part of flush; ensure our queued topic is present
    pubs = [pub for pub in client.publishes if pub[0] == "bb8/test"]
    assert len(pubs) == 1
    topic, payload, qos, retain = pubs[0]
    assert isinstance(payload, str) and payload
    assert qos == 0 and retain is False

    # no ERROR-level logs containing 'mqtt_' events
    errs = [
        rec for rec in caplog.records
        if rec.levelno >= logging.ERROR and isinstance(rec.msg, dict) and str(rec.msg.get("event", "")).startswith("mqtt_")
    ]
    assert not errs


def test_safe_publish_online_success(caplog):
    caplog.set_level(logging.DEBUG)
    client = FakeClient()
    client.set_connected(True)

    ok = md.safe_publish(client, "bb8/now", {"ok": True}, qos=1, retain=True)
    assert ok is True
    assert len(client.publishes) == 1
    t, p, q, r = client.publishes[0]
    assert t == "bb8/now" and q == 1 and r is True

    # ensure no schema error produced
    messages = [str(rec.msg) for rec in caplog.records]
    assert not any("mqtt_publish_schema_error" in m for m in messages)
