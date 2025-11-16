def test_safe_publish_transient(monkeypatch, caplog):
    from addon.bb8_core import mqtt_dispatcher as md

    calls = {"publishes": 0}

    class StubMid:
        def __init__(self):
            self.mid = 1

        def wait_for_publish(self, timeout=3):
            return True

    class StubClient:
        def __init__(self):
            self._connected = False

        def is_connected(self):
            return self._connected

        def publish(self, topic, payload=None, qos=0, retain=False):
            calls["publishes"] += 1
            return StubMid()

    c = StubClient()

    # Avoid real sleeping to keep test fast
    monkeypatch.setattr(md.time, "sleep", lambda s: None)

    # First call while offline queues and returns False (no publish)
    assert (
        md.safe_publish(
            c,
            "bb8/ack/actuate_probe",
            {"ok": True, "cid": "t"},
        )
        is False
    )
    assert calls["publishes"] == 0

    # Flip to online and publish again → should attempt publish
    c._connected = True
    assert (
        md.safe_publish(
            c,
            "bb8/ack/actuate_probe",
            {"ok": True, "cid": "t2"},
        )
        is True
    )
    assert calls["publishes"] >= 1
