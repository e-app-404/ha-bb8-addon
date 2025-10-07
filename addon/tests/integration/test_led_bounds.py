import json, os
from addon.bb8_core.led_discovery import build_led_config

def test_led_bounds_coercion(monkeypatch):
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY","1")
    monkeypatch.setenv("LED_DEFAULT","{\"r\":-5,\"g\":300,\"b\":\"12\"}")
    cfg = build_led_config(base="bb8")
    payload = json.loads(cfg["payload"])
    # Expect clamped ints
    assert payload["r"] == 0
    assert payload["g"] == 255
    assert payload["b"] == 12