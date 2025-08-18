import importlib
import os
import time
from unittest.mock import MagicMock, patch


def test_scanner_discovery_uses_hook_when_set():
    os.environ["ENABLE_BRIDGE_TELEMETRY"] = "1"
    md = importlib.import_module("bb8_core.mqtt_dispatcher")
    stub = MagicMock(name="scanner_publish_discovery")
    try:
        # 1) Module-level hook so **any** thread can see it
        md.SCANNER_PUBLISH_HOOK = stub
        # 2) Patch the seam function so lookup MUST return our stub
        with patch(
            "bb8_core.mqtt_dispatcher._get_scanner_publisher", return_value=stub
        ):
            md.start_mqtt_dispatcher(controller=MagicMock())
            # Wait briefly for async on_connect callback to invoke the stub
            for _ in range(40):  # ~2s with 50ms sleeps
                if stub.called:
                    break
                time.sleep(0.05)
        assert stub.called, "seam: hook/seam stub was not called"
    finally:
        md.SCANNER_PUBLISH_HOOK = None


def test_scanner_only_discovery_when_bridge_telemetry_enabled():
    os.environ["ENABLE_BRIDGE_TELEMETRY"] = "1"
    md = importlib.import_module("bb8_core.mqtt_dispatcher")
    stub = MagicMock(name="scanner_publish_discovery")
    try:
        # 1) Set the module-level hook so *any* thread can see it
        md.SCANNER_PUBLISH_HOOK = stub
        # 2) Patch the seam to return the stub (covers any aliasing/caching)
        with patch(
            "bb8_core.mqtt_dispatcher._get_scanner_publisher", return_value=stub
        ):
            md.start_mqtt_dispatcher(controller=MagicMock())
            # Wait briefly for on_connect callback to run
            import time

            for _ in range(40):  # ~2s with 50ms sleeps
                if stub.called:
                    break
                time.sleep(0.05)
        assert stub.called, "dispatcher: scanner publish_discovery was not called"
    finally:
        md.SCANNER_PUBLISH_HOOK = None
