import time

from bb8_core.facade import Bb8Facade, Rgb

class StubCore:
    calls = []
    @staticmethod
    def sleep(toy, interval_option, unk, unk2, proc=None):
        StubCore.calls.append(("sleep", interval_option, unk, unk2))
    @staticmethod
    def set_main_led(toy, r, g, b, proc=None):
        StubCore.calls.append(("led", r, g, b))
    @staticmethod
    def set_heading(toy, h, proc=None):
        StubCore.calls.append(("heading", h))
    @staticmethod
    def set_speed(toy, s, proc=None):
        StubCore.calls.append(("speed", s))

def test_sleep_mapping(monkeypatch):
    import bb8_core.facade as F
    monkeypatch.setattr(F, "Core", StubCore)
    StubCore.calls.clear()
    f = Bb8Facade(toy=object())
    f.sleep(after_ms=0)
    assert ("sleep", 0x00, 0x00, 0x0000) in StubCore.calls

def test_led_set_immediate(monkeypatch):
    import bb8_core.facade as F
    monkeypatch.setattr(F, "Core", StubCore)
    StubCore.calls.clear()
    f = Bb8Facade(toy=object())
    f.set_led(Rgb(300, -5, 10), transition_ms=0)
    # clamped to 255,0,10
    assert ("led", 255, 0, 10) in StubCore.calls

def test_led_fade_steps(monkeypatch):
    import bb8_core.facade as F
    monkeypatch.setattr(F, "Core", StubCore)
    StubCore.calls.clear()
    slept = {"ms": 0}
    monkeypatch.setattr(time, "sleep", lambda s: slept.__setitem__("ms", slept["ms"] + int(s*1000)))
    f = Bb8Facade(toy=object())
    f.set_led(Rgb(10, 0, 0), transition_ms=100, steps=5)
    # 5 incremental LED calls
    led_calls = [c for c in StubCore.calls if c[0] == "led"]
    assert len(led_calls) == 5
    assert slept["ms"] >= 100  # accumulated delay

def test_drive_autostop(monkeypatch):
    import bb8_core.facade as F
    monkeypatch.setattr(F, "Core", StubCore)
    StubCore.calls.clear()
    monkeypatch.setattr(time, "sleep", lambda s: None)
    f = Bb8Facade(toy=object())
    f.drive(heading_deg=370, speed_0_255=300, duration_ms=10)
    assert ("heading", 10) in StubCore.calls       # 370 % 360
    assert ("speed", 255) in StubCore.calls        # clamped
    assert ("speed", 0) in StubCore.calls          # auto-stop
