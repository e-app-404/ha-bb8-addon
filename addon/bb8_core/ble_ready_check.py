#!/usr/bin/env python3
"""
ble_ready_check.py: Checks if BB-8 BLE device is awake and ready.
Emits a JSON summary artifact and returns exit code 0 if detected, 1 if not.
Leverages existing BLE scan logic from bb8_core modules.
"""
import sys
import time
import json
import os
from pathlib import Path


# Import existing BLE scan logic (adjust imports as needed)
try:
    from bb8_core.auto_detect import scan_for_bb8
except ImportError:
    print(json.dumps({"error": "Could not import scan_for_bb8"}))
    sys.exit(2)

SCAN_TIMEOUT = int(os.environ.get("BLE_SCAN_TIMEOUT", "45"))  # seconds
RETRY_INTERVAL = float(os.environ.get("BLE_SCAN_RETRY_INTERVAL", "2.0"))  # seconds
MAX_ATTEMPTS = int(os.environ.get("BLE_SCAN_MAX_ATTEMPTS", str(SCAN_TIMEOUT // int(RETRY_INTERVAL))))
ARTIFACT_PATH = os.environ.get("BLE_READY_ARTIFACT", "/tmp/ble_ready_summary.json")

summary = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "attempts": 0,
    "detected": False,
    "device_info": None,
    "error": None,
}


def main():
    for attempt in range(1, MAX_ATTEMPTS + 1):
        summary["attempts"] = attempt
        try:
            devices = scan_for_bb8(int(RETRY_INTERVAL), adapter=None)
            if devices:
                summary["detected"] = True
                summary["device_info"] = devices[0]
                break
        except Exception as e:
            summary["error"] = str(e)
        time.sleep(RETRY_INTERVAL)
    # Emit artifact
    try:
        Path(os.path.dirname(ARTIFACT_PATH)).mkdir(parents=True, exist_ok=True)
        with open(ARTIFACT_PATH, "w") as f:
            json.dump(summary, f, indent=2)
    except Exception as e:
        print(json.dumps({"error": f"Failed to write artifact: {e}"}))
    # Print summary to stdout
    print(json.dumps(summary))
    sys.exit(0 if summary["detected"] else 1)

if __name__ == "__main__":
    main()
