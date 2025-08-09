#!/usr/bin/env bash
set -euo pipefail

# Version for Strategos audit and reporting
VERSION="2025.8.5"

# Robust version reporting: fallback to build-time injected value or /app/VERSION
VERSION="${ADDON_VERSION:-$(cat /app/VERSION 2>/dev/null || echo unknown)}"

# Load config from Home Assistant options.json (mounted at /data/options.json)
CONFIG_FILE="/data/options.json"
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Config file not found: $CONFIG_FILE" >&2
  exit 1
fi

mkdir -p /data

BB8_MAC="$(jq -r '.bb8_mac // ""' "$CONFIG_FILE")"
SCAN_SEC="$(jq -r '.scan_seconds // 5' "$CONFIG_FILE")"
RESCAN="$(jq -r '.rescan_on_fail // true' "$CONFIG_FILE")"
TTL_HR="$(jq -r '.cache_ttl_hours // 720' "$CONFIG_FILE")"

export BB8_MAC_OVERRIDE="${BB8_MAC:-}"
export BB8_SCAN_SECONDS="${SCAN_SEC:-5}"
export BB8_RESCAN_ON_FAIL="${RESCAN:-true}"
export BB8_CACHE_TTL_HOURS="${TTL_HR:-720}"
export BB8_CACHE_PATH="/data/bb8_cache.json"

export PYTHONPATH=/app

# Parse MQTT_BROKER (URL or host:port) to set MQTT_HOST and MQTT_PORT
parse_mqtt_url() {
  url="$1"
  url_no_proto="${url#mqtt://}"
  if echo "$url_no_proto" | grep -q ':'; then
    host="${url_no_proto%%:*}"
    port="${url_no_proto##*:}"
  else
    host="$url_no_proto"
    port="1883"
  fi
  export MQTT_HOST="$host"
  export MQTT_PORT="$port"
}

parse_mqtt_url "$MQTT_BROKER"

export MQTT_USER="$MQTT_USERNAME"
export MQTT_PASSWORD="$MQTT_PASSWORD"
export MQTT_TOPIC="${MQTT_TOPIC_PREFIX}/command"
export STATUS_TOPIC="${MQTT_TOPIC_PREFIX}/status"

echo "==== BB-8 Add-on Startup ===="
echo "Version: $VERSION"
echo "Build Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Container Started: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "============================="
echo "BB8_MAC: $BB8_MAC"
echo "MQTT_BROKER: $MQTT_BROKER"
echo "MQTT_USERNAME: $MQTT_USERNAME"
echo "MQTT_TOPIC_PREFIX: $MQTT_TOPIC_PREFIX"
echo "BLE_ADAPTER: $BLE_ADAPTER"
echo "Python version: $(python3 --version 2>&1)"
echo "Python path: $(which python3)"
echo "Current working directory: $(pwd)"
echo "Running as user: $(id -u -n) (UID: $(id -u))"
echo "Contents of /app:"
ls -l /app
echo "Contents of /app/bb8_core:"
ls -l /app/bb8_core
echo "============================="

echo "[BB-8] Running BLE adapter check..."
python3 /app/test_ble_adapter.py

# Start the Python service
exec python -m bb8_core.main \
  --bb8-mac "${BB8_MAC_OVERRIDE}" \
  --scan-seconds "${BB8_SCAN_SECONDS}" \
  --rescan-on-fail "${BB8_RESCAN_ON_FAIL}" \
  --cache-ttl-hours "${BB8_CACHE_TTL_HOURS}"
