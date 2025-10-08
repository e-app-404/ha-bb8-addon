import json, os
def test_led_payload_bounds(monkeypatch):
    from addon.bb8_core.led_discovery import build_led_config
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY","1")
    monkeypatch.setenv("LED_DEFAULT",'{"r":-1,"g":999,"b":"7"}')
    cfg=build_led_config("bb8")
    payload=json.loads(cfg["payload"])
    assert payload["r"]==0 and payload["g"]==255 and payload["b"]==7
    assert "device" in cfg and isinstance(cfg["device"], dict)