#!/usr/bin/env python3
"""Debug script to check echo_responder environment issues."""

import os
import sys

print("=== Echo Environment Debug ===")
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Python path: {sys.path}")
print(f"VIRTUAL_ENV: {os.environ.get('VIRTUAL_ENV', 'NOT SET')}")
print(f"PATH: {os.environ.get('PATH', 'NOT SET')}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'NOT SET')}")

print("\n=== Testing imports ===")
try:
    import paho.mqtt.client as mqtt

    print("✅ paho.mqtt.client imported successfully")
    print(f"paho.mqtt location: {mqtt.__file__}")
except ImportError as e:
    print(f"❌ paho.mqtt.client import failed: {e}")

try:
    from addon.bb8_core import echo_responder

    print("✅ addon.bb8_core.echo_responder imported successfully")
except ImportError as e:
    print(f"❌ addon.bb8_core.echo_responder import failed: {e}")

print("\n=== Package check ===")
try:
    import pkg_resources

    installed = [d.project_name for d in pkg_resources.working_set]
    paho_packages = [p for p in installed if "paho" in p.lower()]
    print(f"Paho packages found: {paho_packages}")
except Exception as e:
    print(f"Package check failed: {e}")
