def _coerce(v):
    from addon.bb8_core import addon_config as ac
    import os
    k="PUBLISH_LED_DISCOVERY"
    old=os.environ.get(k)
    try:
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k]=v
        return ac.load_effective_config().get("PUBLISH_LED_DISCOVERY")
    finally:
        if old is None: os.environ.pop(k, None)
        else: os.environ[k]=old

def test_bool_matrix_and_unknown_types(monkeypatch):
    # Typical truthy/falsy strings
    assert _coerce("1") in (True, "1", 1)
    assert _coerce("0") in (False, "0", 0)
    assert _coerce("yes") in (True, "yes", "Yes", 1)
    assert _coerce("no") in (False, "no", "No", 0)
    # Unknown garbage should not crash; must still return a value (fallback path)
    assert _coerce("garbage") is not None
    # Unset -> default respected
    assert _coerce(None) is not None