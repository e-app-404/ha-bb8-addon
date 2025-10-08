def test_echo_only_mode(monkeypatch):
    from addon.bb8_core import bridge_controller as bc
    monkeypatch.setenv("ECHO_ONLY","1")
    mode=bc.resolve_startup_mode()
    assert mode in ("echo_only","full") and mode=="echo_only"

def test_led_gate_no_emit(monkeypatch):
    from addon.bb8_core import bridge_controller as bc
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY","0")
    emitted=bc.plan_discovery_emits(base="bb8")
    assert all("led" not in (e.get("kind","") or "") for e in emitted)