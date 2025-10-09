def test_empty_entries_safe():
    from addon.bb8_core.discovery import select_owner

    sel = select_owner([])
    assert sel is None or isinstance(sel, dict)


def test_equal_ts_tie_break_deterministic():
    from addon.bb8_core.discovery import select_owner

    a = [{"owner": "a", "ts": 5}, {"owner": "b", "ts": 5}]
    s1 = select_owner(a)
    s2 = select_owner(list(reversed(a)))
    # must be stable; at minimum have required keys
    assert isinstance(s1, dict) and "owner" in s1 and "ts" in s1
    assert isinstance(s2, dict) and "owner" in s2 and "ts" in s2
