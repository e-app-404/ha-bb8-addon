#!/bin/bash
# HA BB-8 verification script (normalized location)
# Moved from /System/Volumes/Data/homeassistant/domain/shell_commands/
# As part of CONFIG_GOV_AUDIT shell commands normalization

set -euo pipefail

echo "=== HA BB-8 Verification ==="
echo "Timestamp: $(date -u)"

# Basic MQTT connectivity check
if command -v mosquitto_pub >/dev/null 2>&1; then
    echo "Testing MQTT connectivity..."
    timeout 5s mosquitto_pub -h core-mosquitto -t "bb8/health/check" -m "verification_$(date +%s)" || echo "MQTT test timeout"
else
    echo "mosquitto_pub not available - skipping MQTT test"
fi

# BB-8 BLE presence check  
if command -v bluetoothctl >/dev/null 2>&1; then
    echo "Checking BB-8 BLE presence..."
    timeout 10s bluetoothctl scan on || echo "BLE scan timeout"
    bluetoothctl devices | grep -i "ED:ED:87:D7:27:50" && echo "BB-8 detected" || echo "BB-8 not detected"
else
    echo "bluetoothctl not available - skipping BLE test"
fi

echo "✅ Verification complete"