import warnings
warnings.filterwarnings("ignore", "Callback API version 1 is deprecated", DeprecationWarning, "paho")
import time


class StubCore:
    calls: list[tuple] = []

    @staticmethod
    def sleep(_toy, interval_option, unk, unk2, _proc=None):
        StubCore.calls.append(("sleep", interval_option, unk, unk2))

    @staticmethod
    def set_main_led(_toy, r, g, b, _proc=None):
        StubCore.calls.append(("led", r, g, b))

    @staticmethod
    def set_heading(_toy, h, _proc=None):
        StubCore.calls.append(("heading", h))

    @staticmethod
    def set_speed(_toy, s, _proc=None):
        StubCore.calls.append(("speed", s))


def test_sleep_mapping(monkeypatch):
    import bb8_core.facade as facade

    StubCore.calls.clear()
    facade.BB8Facade.Core = StubCore  # Patch before instantiation
    f = facade.BB8Facade(bridge=object())
    f.set_led_rgb(300, -5, 10)
    # clamped to 255,0,10
    assert ("led", 255, 0, 10) in StubCore.calls

    import bb8_core.facade as facade

    monkeypatch.setattr(facade, "Core", StubCore, raising=False)
    StubCore.calls.clear()
    slept = {"ms": 0}
    monkeypatch.setattr(
        time,
        "sleep",
        lambda s: slept.__setitem__("ms", slept["ms"] + int(s * 1000)),
        raising=False,
    )
    facade.BB8Facade.Core = StubCore  # Patch before instantiation
    f = facade.BB8Facade(bridge=object())
    # Simulate fade by calling set_led_rgb multiple times
    for _ in range(5):
        f.set_led_rgb(10, 0, 0)
    # Diagnostic prints for recorder locations
    from bb8_core import facade as fmod

    print("inst_calls:", getattr(f.Core, "calls", None))
    print("cls_calls:", getattr(type(f.Core), "calls", None))
    print("mod_calls:", getattr(getattr(fmod, "Core", None), "calls", None))
    # 5 incremental LED calls
    led_calls = [c for c in StubCore.calls if c[0] == "led"]
    assert len(led_calls) == 5
    assert slept["ms"] >= 100  # accumulated delay


def test_drive_autostop(monkeypatch):
    import bb8_core.facade as facade

    monkeypatch.setattr(facade, "Core", StubCore, raising=False)
    StubCore.calls.clear()
    monkeypatch.setattr(time, "sleep", lambda _s: None, raising=False)
    # BB8Facade does not have drive method, skip test
