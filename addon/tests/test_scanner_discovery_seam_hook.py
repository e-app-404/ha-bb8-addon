import importlib
import os
import sys
from unittest.mock import MagicMock


def test_scanner_discovery_seam_hook():
    os.environ["ENABLE_BRIDGE_TELEMETRY"] = "1"
    # Import dispatcher
    md = importlib.import_module("bb8_core.mqtt_dispatcher")
    stub = MagicMock(name="scanner_publish_discovery")
    try:
        # Set the hook on the actual module object used by the dispatcher
        sys.modules["bb8_core.mqtt_dispatcher"].SCANNER_PUBLISH_HOOK = stub
        md._trigger_discovery_connected()
        assert stub.called, "seam-hook: stub was not called"
    finally:
        sys.modules["bb8_core.mqtt_dispatcher"].SCANNER_PUBLISH_HOOK = None
