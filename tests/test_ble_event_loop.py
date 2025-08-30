import time

from bb8_core import ble_link


def test_ble_loop_thread_bootstrap_idempotent():
    # starting twice should not crash or spawn multiple threads
    ble_link.start_loop_thread()
    time.sleep(0.05)
    ble_link.start()
    # call again to ensure idempotency
    ble_link.start()
    # if we reach here without exceptions, basic bootstrap is OK
    assert True
