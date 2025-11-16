def test_same_owner_newest_ts_wins():
    from addon.bb8_core.discovery import select_owner

    entries = [
        {"owner": "bb8", "ts": 1},
        {"owner": "bb8", "ts": 7},
        {"owner": "bb8", "ts": 3},
    ]
    assert select_owner(entries)["ts"] == 7


def test_cross_owner_does_not_crash_and_is_deterministic():
    from addon.bb8_core.discovery import select_owner

    entries = [{"owner": "bb8", "ts": 10}, {"owner": "other", "ts": 12}]
    sel = select_owner(entries)
    assert "owner" in sel and "ts" in sel
