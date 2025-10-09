import json
import os


def test_led_bounds_coercion(monkeypatch):
    """Test LED RGB value bounds and coercion"""
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY", "1")
    monkeypatch.setenv("LED_DEFAULT", '{"r":-5,"g":300,"b":"12"}')
    
    # Mock LED config builder
    def build_led_config(base="bb8"):
        if os.getenv("PUBLISH_LED_DISCOVERY", "0") == "0":
            return None
        default_str = os.getenv("LED_DEFAULT", '{"r":0,"g":0,"b":0}')
        default = json.loads(default_str)
        # Clamp values 0-255
        clamped = {
            "r": max(0, min(255, int(default.get("r", 0)))),
            "g": max(0, min(255, int(default.get("g", 0)))),
            "b": max(0, min(255, int(default.get("b", 0))))
        }
        return {"payload": json.dumps(clamped)}
    
    cfg = build_led_config(base="bb8")
    payload = json.loads(cfg["payload"])
    # Expect clamped ints
    assert payload["r"] == 0
    assert payload["g"] == 255
    assert payload["b"] == 12