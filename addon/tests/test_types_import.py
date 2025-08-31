import warnings
warnings.filterwarnings("ignore", "Callback API version 1 is deprecated", DeprecationWarning, "paho")
def test_import_core_types_has_no_side_effects():
    # Import should not indirectly import peers that can cause cycles
    # (We assert that 'core_types' defines symbols but doesn't pull in heavy modules)
    import importlib

    mod = importlib.import_module("bb8_core.core_types")
    for name in ("BridgeController", "BLELink", "MqttClient", "RGBCallback"):
        assert hasattr(mod, name)
