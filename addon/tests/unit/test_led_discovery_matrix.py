import json, os
def test_env_precedence_matrix(monkeypatch):
    from addon.bb8_core.led_discovery import build_led_config
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY","1")
    monkeypatch.setenv("LED_DEFAULT",'{"r":256,"g":-5,"b":"9"}')
    cfg=build_led_config("bb8")
    payload=json.loads(cfg["payload"])
    assert payload=={"r":255,"g":0,"b":9}
    assert "device" in cfg and isinstance(cfg["device"], dict)

def test_gate_off(monkeypatch):
    from addon.bb8_core.led_discovery import should_publish_led
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY","0")
    assert should_publish_led() is False