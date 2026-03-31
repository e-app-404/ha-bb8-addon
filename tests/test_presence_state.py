from bb8_core import bridge_controller


class FakeClient:
    def __init__(self):
        self.calls = []

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.calls.append(
            {
                "topic": topic,
                "payload": payload,
                "qos": qos,
                "retain": retain,
            }
        )


def test_presence_detected_publishes_correct_payload(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr(bridge_controller, "client", fake_client)

    bridge_controller._auto_detect_presence_publish_adapter(
        "bb8/presence/C9:5A:63:6B:B5:4A",
        {"state": "present", "mac": "C9:5A:63:6B:B5:4A"},
    )

    assert fake_client.calls == [
        {
            "topic": "bb8/state/presence",
            "payload": "detected",
            "qos": 0,
            "retain": True,
        }
    ]


def test_presence_not_detected_publishes_correct_payload(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr(bridge_controller, "client", fake_client)

    bridge_controller._auto_detect_presence_publish_adapter(
        "bb8/presence/C9:5A:63:6B:B5:4A",
        {"state": "absent", "mac": "C9:5A:63:6B:B5:4A"},
    )

    assert fake_client.calls == [
        {
            "topic": "bb8/state/presence",
            "payload": "not_detected",
            "qos": 0,
            "retain": True,
        }
    ]


def test_presence_initial_state_is_not_detected():
    fake_client = FakeClient()

    bridge_controller._publish_presence_state("not_detected", mqtt_client=fake_client)

    assert fake_client.calls == [
        {
            "topic": "bb8/state/presence",
            "payload": "not_detected",
            "qos": 0,
            "retain": True,
        }
    ]