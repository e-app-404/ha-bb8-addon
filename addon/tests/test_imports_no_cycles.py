def test_imports_clean():
    import importlib

    import addon.bb8_core.bb8_presence_scanner as s
    import addon.bb8_core.bridge_controller as bc

    importlib.reload(s)
    importlib.reload(bc)
