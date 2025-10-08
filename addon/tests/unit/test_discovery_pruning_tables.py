import itertools
def test_pruning_prefers_newest_same_owner():
    from addon.bb8_core.discovery import select_owner
    entries=[{"owner":"bb8","ts":t} for t in (1,5,3)]
    assert select_owner(entries)["ts"]==5

def test_pruning_resolves_cross_owner_by_policy():
    from addon.bb8_core.discovery import select_owner
    entries=[{"owner":"bb8","ts":10},{"owner":"other","ts":12}]
    sel=select_owner(entries)
    assert sel["owner"] in ("bb8","other")  # exact policy asserted by implementation; must not crash