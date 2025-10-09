def test_env_bool_precedence(monkeypatch):
    from addon.bb8_core import addon_config as ac

    # clear then default
    monkeypatch.delenv("PUBLISH_LED_DISCOVERY", raising=False)
    cfg0, _ = ac.load_config()
    # override to truthy strings
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY", "true")
    cfg1, _ = ac.load_config()
    assert cfg1.get("PUBLISH_LED_DISCOVERY") in (True, "true", "True", 1)


def test_malformed_env_json_fallback(monkeypatch):
    from addon.bb8_core import addon_config as ac

    monkeypatch.setenv("LED_DEFAULT", "{bad json")
    cfg, _ = ac.load_config()
    # presence without crash; fallback path hit
    assert "LED_DEFAULT" in cfg
