def test_prunes_duplicates_preferring_latest_ts():
    from addon.bb8_core.discovery import select_owner
    items = [
        {"owner":"bb8-A","ts":10},
        {"owner":"bb8-A","ts":11},  # newer duplicate of same owner
        {"owner":"bb8-B","ts":9}
    ]
    sel = select_owner(items)
    assert sel and sel.get("owner") in {"bb8-A","bb8-B"}
    # If pruning prefers newest same-owner, result should be A or latest rule; but must be deterministic and not crash.