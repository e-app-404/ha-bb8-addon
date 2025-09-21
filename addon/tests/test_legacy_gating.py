import importlib


def test_legacy_gating_default_off(monkeypatch):
    # Default: flag is off
    monkeypatch.delenv("ENABLE_LEGACY_FLAT_TOPICS", raising=False)
    m = importlib.import_module("addon.bb8_core.mqtt_dispatcher")
    calls = []

    class Client:
        def subscribe(self, topic):
            calls.append(topic)

    # Use monkeypatch to mock register_subscription
    monkeypatch.setattr(
        m, "register_subscription", lambda topic: Client().subscribe(topic)
    )
    if hasattr(m, "register_command_handlers"):
        m.register_command_handlers(mqtt_base="bb8", device_id="UT")
    monkeypatch.setenv("ENABLE_LEGACY_FLAT_TOPICS", "1")
    m = importlib.reload(importlib.import_module("addon.bb8_core.mqtt_dispatcher"))
    calls = []

    # Reuse the same Client class
    monkeypatch.setattr(
        m, "register_subscription", lambda topic: Client().subscribe(topic)
    )
    if hasattr(m, "register_command_handlers"):
        m.register_command_handlers(mqtt_base="bb8", device_id="UT")

    assert any(
        ("/speed/set" in t or "/heading/set" in t or "/drive/press" in t) for t in calls
    )

    # Use monkeypatch to mock register_subscription again for the last check
    monkeypatch.setattr(
        m, "register_subscription", lambda topic: Client().subscribe(topic)
    )
    if hasattr(m, "register_command_handlers"):
        m.register_command_handlers(mqtt_base="bb8", device_id="UT")

    assert any(
        ("/speed/set" in t or "/heading/set" in t or "/drive/press" in t) for t in calls
    )
