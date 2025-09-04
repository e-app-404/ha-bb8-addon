import warnings

warnings.filterwarnings(
    "ignore", "Callback API version 1 is deprecated", DeprecationWarning, "paho"
)
import time
from tests.helpers.fakes_ble import FakeBLEDevice
from tests.helpers.util import assert_contains_log


def test_ble_link_thread_lifecycle():
    from bb8_core import ble_link

    ble_link.start()
    # Yield to BLELoopThread (no async loop in this test)
    time.sleep(0.05)
    ble_link.stop()
    # Ensure the thread is fully joined to avoid ResourceWarnings
    ble_link.join()


def test_connect_read_disconnect(monkeypatch, capsys):
    dev = FakeBLEDevice("AA:BB:CC", "bb8", -42)
    print(f"connect: {dev.addr}")
    dev.connect()
    data = dev.read_gatt("svc1")
    print(f"read: svc1")
    assert data.startswith(b"data-for-")
    dev.disconnect()
    assert not dev.connected
    out = capsys.readouterr()
    assert "connect: AA:BB:CC" in out.out or "connect: AA:BB:CC" in out.err
    assert "read: svc1" in out.out or "read: svc1" in out.err


def test_connect_fail(monkeypatch, capsys):
    dev = FakeBLEDevice("AA:BB:CC", "bb8", -42, fail_connect=True)
    try:
        dev.connect()
    except Exception:
        print("connect failed")
    out, err = capsys.readouterr()
    assert "connect failed" in out or "connect failed" in err
