import warnings

warnings.filterwarnings(
    "ignore", "Callback API version 1 is deprecated", DeprecationWarning, "paho"
)
import time


def test_ble_link_thread_lifecycle():
    from addon.bb8_core import ble_link

    ble_link.start()
    # Yield to BLELoopThread (no async loop in this test)
    time.sleep(0.05)
    ble_link.stop()
    # Ensure the thread is fully joined to avoid ResourceWarnings
    ble_link.join()
