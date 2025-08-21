import time

from bb8_core.ble_link import BLELink


def test_ble_link_thread_lifecycle():
    import asyncio

    link = BLELink("00:11:22:33:44:55")
    loop = asyncio.new_event_loop()
    link.set_loop(loop)
    link.start()
    time.sleep(0.1)
    link.stop()
    time.sleep(0.1)
