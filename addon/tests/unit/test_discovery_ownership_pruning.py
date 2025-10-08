def test_single_owner_pruning():
    from addon.bb8_core.discovery import select_owner
    entries=[
        {"owner":"bb8","ts":10},
        {"owner":"bb8","ts":11},  # newer same owner
        {"owner":"other","ts":9}
    ]
    sel=select_owner(entries)
    assert sel["owner"]=="bb8" and sel["ts"]==11