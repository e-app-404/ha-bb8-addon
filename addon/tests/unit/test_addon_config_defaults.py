def test_defaults_and_env(monkeypatch):
    from addon.bb8_core.addon_config import load_config
    monkeypatch.delenv("PUBLISH_LED_DISCOVERY", raising=False)
    cfg = load_config()
    assert cfg.get("publish_led_discovery") in (0, False)
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY","1")
    cfg2 = load_config()
    assert cfg2.get("publish_led_discovery") in (1, True)