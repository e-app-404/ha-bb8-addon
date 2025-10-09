import json


def test_led_clamp_and_types(monkeypatch):
    from addon.bb8_core.led_discovery import build_led_config
    # try a grid of mixed inputs; make sure clamp [0,255] and ints
    cases = [("-1", "300", "12.7"), ("0", "0", "0"), ("255", "255", "255"), (None, "9", "-5")]
    for r, g, b in cases:
        if r is not None: monkeypatch.setenv("LED_R", str(r))
        if g is not None: monkeypatch.setenv("LED_G", str(g))
        if b is not None: monkeypatch.setenv("LED_B", str(b))
        cfg = build_led_config("bb8")
        payload = json.loads(cfg["payload"])
        assert 0 <= payload["r"] <= 255
        assert 0 <= payload["g"] <= 255
        assert 0 <= payload["b"] <= 255
        assert all(isinstance(v, int) for v in payload.values())