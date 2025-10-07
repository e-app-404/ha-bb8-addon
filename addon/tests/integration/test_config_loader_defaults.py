def test_config_defaults(monkeypatch):
    from addon.bb8_core.addon_config import load_config
    monkeypatch.delenv("PUBLISH_LED_DISCOVERY", raising=False)
    cfg = load_config()
    assert cfg["publish_led_discovery"] in (0, False)