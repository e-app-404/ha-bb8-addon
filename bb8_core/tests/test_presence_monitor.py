from addon.bb8_core import auto_detect


def test_async_monitor_bb8_presence_basic(monkeypatch):
    # Mock BLE scan always finds device
    async def mock_ble_scan(scan_seconds=5, adapter=None):
        return [{"name": "BB-8", "address": "AA:BB:CC:DD:EE:FF", "rssi": -60}]

    results = []

    def mock_mqtt_publish(topic, payload):
        results.append((topic, payload))

    import asyncio

    async def run_and_cancel():
        task = asyncio.create_task(
            auto_detect.async_monitor_bb8_presence(
                scan_interval=0.1,
                absence_timeout=0.2,
                debounce_count=1,
                async_ble_scan_fn=mock_ble_scan,
                mqtt_publish_fn=mock_mqtt_publish,
            )
        )
        await asyncio.sleep(0.3)  # Let it run a few iterations
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(run_and_cancel())
    assert any("present" in str(payload) for _, payload in results)


def test_monitor_bb8_presence_absence(monkeypatch):
    # Mock BLE scan alternates between found and not found
    scan_calls = [True, False, False]

    def mock_ble_scan(scan_seconds=5, adapter=None):
        found = scan_calls.pop(0) if scan_calls else False
        if found:
            return [{"name": "BB-8", "address": "AA:BB:CC:DD:EE:FF", "rssi": -60}]
        return []

    results = []

    def mock_mqtt_publish(topic, payload):
        results.append((topic, payload))

    monitor = auto_detect.monitor_bb8_presence(
        scan_interval=1,
        absence_timeout=2,
        debounce_count=1,
        ble_scan_fn=mock_ble_scan,
        mqtt_publish_fn=mock_mqtt_publish,
    )
    # Run only 3 iterations for test
    for _ in range(3):
        next(monitor)
    assert any("absent" in str(payload) for _, payload in results)
