import warnings

warnings.filterwarnings(
    "ignore", "Callback API version 1 is deprecated", DeprecationWarning, "paho"
)


def test_imports_clean():
    import importlib

    import bb8_core.bb8_presence_scanner as s
    import bb8_core.bridge_controller as bc

    importlib.reload(s)
    importlib.reload(bc)
