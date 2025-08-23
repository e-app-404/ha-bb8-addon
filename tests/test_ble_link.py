import time

from bb8_core.ble_link import BLELink


def test_ble_link_thread_lifecycle():
    import asyncio

    link = BLELink("00:11:22:33:44:55")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    link.set_loop(loop)
    link.start()
    time.sleep(0.1)
    link.stop()
    time.sleep(0.1)
    # Run pending tasks to completion and close loop
    pending = asyncio.all_tasks(loop)
    if pending:
        loop.run_until_complete(
            asyncio.gather(*pending, return_exceptions=True)
        )
    loop.close()
    loop.close()
