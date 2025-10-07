def test_single_owner_enforced():
    from addon.bb8_core.discovery_ownership import check_duplicates, owner_of
    topics = [
        ("homeassistant/sensor/bb8_presence_1/config", "uid=foo"),
        ("homeassistant/sensor/bb8_rssi_1/config", "uid=foo"),
        # Duplicate owner attempt (should be flagged if conflicting)
    ]
    owners = [owner_of(t, p) for t, p in topics]
    assert len(set(owners)) == 1, "Multiple discovery owners detected"
    assert check_duplicates(topics) == 0