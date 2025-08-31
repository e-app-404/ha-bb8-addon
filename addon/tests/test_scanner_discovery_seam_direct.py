import warnings
warnings.filterwarnings("ignore", "Callback API version 1 is deprecated", DeprecationWarning, "paho")
import importlib
import os
from unittest.mock import MagicMock


def test_scanner_discovery_seam_direct():
    os.environ["ENABLE_BRIDGE_TELEMETRY"] = "1"
    md = importlib.import_module("bb8_core.mqtt_dispatcher")
    stub = MagicMock(name="scanner_publish_discovery")
    # Patch the seam function so invocation MUST use our stub
    from unittest.mock import patch

    with patch("bb8_core.mqtt_dispatcher._get_scanner_publisher", return_value=stub):
        print("HOOK id before:", id(getattr(md, "SCANNER_PUBLISH_HOOK", None)))
        print("stub id:", id(stub))
        print("dispatcher func id:", id(md._trigger_discovery_connected))
        md._trigger_discovery_connected()
        print("HOOK id after:", id(getattr(md, "SCANNER_PUBLISH_HOOK", None)))
        assert stub.called, "seam: stub was not called via _get_scanner_publisher"
