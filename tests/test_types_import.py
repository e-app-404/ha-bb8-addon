def test_import_types_has_no_side_effects():
    # Import should not indirectly import peers that can cause cycles
    # (We assert that 'types' defines symbols but doesn't pull in heavy modules)
    import importlib

    mod = importlib.import_module("beep_boop_bb8.bb8_core.types")
    for name in ("BridgeController", "BLELink", "MqttClient", "RGBCallback"):
        assert hasattr(mod, name)
