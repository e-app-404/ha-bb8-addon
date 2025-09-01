import warnings

warnings.filterwarnings(
    "ignore", "Callback API version 1 is deprecated", DeprecationWarning, "paho"
)
import importlib
import sys
import warnings


def test_no_runtimewarning_on_import_order():
    """
    Guard against:
    RuntimeWarning: 'bb8_core.bridge_controller' found in sys.modules after import of
    package 'bb8_core', but prior to execution of 'bb8_core.bridge_controller'
    """
    # Ensure clean state
    for mod in (
        "bb8_core.bridge_controller",
        "bb8_core.bb8_presence_scanner",
        "bb8_core.ble_link",
        "bb8_core",
    ):
        sys.modules.pop(mod, None)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "error",
            message=r".*found in sys\.modules after import of package 'bb8_core'.*",
            category=RuntimeWarning,
        )
        importlib.import_module("bb8_core")  # package first
        importlib.import_module("bb8_core.bridge_controller")  # submodule next
