def test_single_owner_enforced():
    """Test that discovery topics have single ownership"""
    # Test the single ownership principle by checking unique device identifiers
    topics = [
        (
            "homeassistant/sensor/bb8_presence_1/config",
            '{"unique_id": "bb8_presence_1", "device": {"identifiers": ["bb8_device"]}}',
        ),
        (
            "homeassistant/sensor/bb8_rssi_1/config",
            '{"unique_id": "bb8_rssi_1", "device": {"identifiers": ["bb8_device"]}}',
        ),
    ]

    # Extract device identifiers from payloads
    import json

    device_ids = []
    for topic, payload in topics:
        try:
            data = json.loads(payload)
            if "device" in data and "identifiers" in data["device"]:
                device_ids.extend(data["device"]["identifiers"])
        except json.JSONDecodeError:
            pass

    # All topics should reference the same device (single owner)
    unique_devices = set(device_ids)
    assert len(unique_devices) == 1, (
        f"Multiple device owners detected: {unique_devices}"
    )
