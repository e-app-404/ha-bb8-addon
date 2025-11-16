def test_mac_and_name_normalization(monkeypatch):
    from addon.bb8_core.facade import normalize_mac, normalize_name

    assert normalize_mac("AA:bb:CC:dd:EE:ff") == "aa:bb:cc:dd:ee:ff"
    assert normalize_name("  BB8  ") == "bb8"


def test_getters_use_cache(monkeypatch):
    from addon.bb8_core import facade

    calls = {"load": 0}

    def fake_load():
        calls["load"] += 1
        return {"mac": "aa:bb:cc:dd:ee:ff", "name": "bb8"}

    monkeypatch.setattr(facade, "load_identity", fake_load)
    a = facade.get_identity()
    b = facade.get_identity()
    assert a == b and calls["load"] == 1
