def test_cache_miss_returns_none(tmp_path, monkeypatch):
    from addon.bb8_core import auto_detect as ad

    monkeypatch.setenv("BB8_CACHE_PATH", str(tmp_path / "missing.json"))
    assert ad.load_mac_from_cache() in (None, "")


def test_malformed_cache_graceful(tmp_path, monkeypatch):
    from addon.bb8_core import auto_detect as ad

    p = tmp_path / "cache.json"
    p.write_text("{bad json")
    monkeypatch.setenv("BB8_CACHE_PATH", str(p))
    assert ad.load_mac_from_cache() in (None, "")


def test_invalid_mac_rejected():
    from addon.bb8_core import auto_detect as ad

    try:
        ok = ad._valid_mac("not-a-mac")
    except AttributeError:
        ok = False
    assert ok is False
