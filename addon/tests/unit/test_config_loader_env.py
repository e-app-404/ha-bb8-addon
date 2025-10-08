

def test_config_env_matrix(monkeypatch):
    from addon.bb8_core import addon_config as ac
    monkeypatch.delenv("PUBLISH_LED_DISCOVERY", raising=False)
    cfg = ac.load_effective_config()
    assert isinstance(cfg, dict)
    # Set env to override and malformed to hit fallback
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY", "1")
    cfg2 = ac.load_effective_config()
    assert cfg2.get("PUBLISH_LED_DISCOVERY") in (True, "1", 1)


def test_malformed_json_fallback(monkeypatch):
    from addon.bb8_core import addon_config as ac
    monkeypatch.setenv("LED_DEFAULT", "{bad json")
    cfg = ac.load_effective_config()
    # Should not crash; either ignores or uses fallback
    assert "LED_DEFAULT" in cfg