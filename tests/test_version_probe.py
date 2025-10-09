import addon.bb8_core.version_probe as vp


def test_probe_all_present(monkeypatch):
    monkeypatch.setattr(vp, "version", lambda pkg: f"{pkg}-ver")
    result = vp.probe()
    assert result["event"] == "version_probe"
    assert result["bleak"] == "bleak-ver"
    assert result["paho-mqtt"] == "paho-mqtt-ver"
    assert result["spherov2"] == "spherov2-ver"


def test_probe_some_missing(monkeypatch):
    def fake_version(pkg):
        if pkg == "paho-mqtt":
            raise vp.E
        return f"{pkg}-ver"

    monkeypatch.setattr(vp, "version", fake_version)
    result = vp.probe()
    assert result["bleak"] == "bleak-ver"
    assert result["paho-mqtt"] == "missing"
    assert result["spherov2"] == "spherov2-ver"


def test_probe_all_missing(monkeypatch):
    monkeypatch.setattr(vp, "version", lambda pkg: (_ for _ in ()).throw(vp.E))
    result = vp.probe()
    assert result["bleak"] == "missing"
    assert result["paho-mqtt"] == "missing"
    assert result["spherov2"] == "missing"
