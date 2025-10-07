import json

from addon.bb8_core.led_discovery import build_led_config


def test_led_off_gates_discovery(monkeypatch):
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY", "0")
    assert build_led_config(base="bb8") is None


def test_led_on_emits_strict_schema(monkeypatch):
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY", "1")
    cfg = build_led_config(base="bb8")
    assert cfg is not None
    payload = json.loads(cfg["payload"])
    assert set(payload.keys()) == {"r", "g", "b"}
    assert all(isinstance(payload[k], int) and 0 <= payload[k] <= 255 for k in ("r", "g", "b"))