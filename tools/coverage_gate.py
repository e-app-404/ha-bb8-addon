#!/usr/bin/env python3
"""
coverage_gate.py — per-file coverage thresholds.
Usage:
  coverage xml -o coverage.xml
  python tools/coverage_gate.py coverage.xml
"""
import sys, xml.etree.ElementTree as ET

# Map of file -> required % (floats allowed)
REQUIRED = {
    "addon/bb8_core/mqtt_dispatcher.py": 90.0,
    "addon/bb8_core/facade.py": 90.0,
    "addon/bb8_core/core.py": 90.0,
    "addon/bb8_core/mqtt_helpers.py": 90.0,
    "addon/bb8_core/util.py": 90.0,
    "addon/ble_bridge.py": 90.0,
    "addon/ble_link.py": 90.0,
    "addon/ble_gateway.py": 90.0,
    "addon/version_probe.py": 90.0,
    "addon/mqtt_probe.py": 90.0,
}

def main(path):
    tree = ET.parse(path)
    root = tree.getroot()
    failures = []
    for pkg in root.iter("package"):
        for cls in pkg.iter("class"):
            filename = cls.attrib.get("filename", "")
            line_rate = float(cls.attrib.get("line-rate", "0")) * 100.0
            # Normalize path separators (CI/OS-agnostic)
            filename_norm = filename.replace("\\", "/")
            if filename_norm in REQUIRED:
                need = REQUIRED[filename_norm]
                if line_rate + 1e-6 < need:
                    failures.append((filename_norm, line_rate, need))
    if failures:
        print("Per-file coverage gate failed:")
        for f, got, need in failures:
            print(f" - {f}: {got:.1f}% (need ≥ {need:.1f}%)")
        sys.exit(2)
    print("Per-file coverage gate: OK")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "coverage.xml"))
