#!/usr/bin/with-contenv bash
set -euo pipefail
export PYTHONUNBUFFERED=1
export PYTHONPATH=/usr/src/app:${PYTHONPATH:-}
cd /usr/src/app

# Load HA add-on options
OPTIONS=/data/options.json
JQ='/usr/bin/jq'

# Toggle: bridge telemetry
ENABLE_BRIDGE_TELEMETRY_RAW=$($JQ -r '.enable_bridge_telemetry // false' "$OPTIONS" 2>/dev/null || echo "false")
if [ "$ENABLE_BRIDGE_TELEMETRY_RAW" = "true" ]; then
  export ENABLE_BRIDGE_TELEMETRY=1
else
  export ENABLE_BRIDGE_TELEMETRY=0
fi

# Common MQTT options (if you expose them in options.json; keep existing exports too)
export MQTT_HOST=${MQTT_HOST:-$($JQ -r '.mqtt_host // empty' "$OPTIONS" 2>/dev/null || true)}
export MQTT_PORT=${MQTT_PORT:-$($JQ -r '.mqtt_port // empty' "$OPTIONS" 2>/dev/null || true)}
export MQTT_USERNAME=${MQTT_USERNAME:-$($JQ -r '.mqtt_user // empty' "$OPTIONS" 2>/dev/null || true)}
export MQTT_PASSWORD=${MQTT_PASSWORD:-$($JQ -r '.mqtt_password // empty' "$OPTIONS" 2>/dev/null || true)}
export BB8_NAME=${BB8_NAME:-$($JQ -r '.bb8_name // empty' "$OPTIONS" 2>/dev/null || true)}
export BB8_MAC=${BB8_MAC:-$($JQ -r '.bb8_mac // empty' "$OPTIONS" 2>/dev/null || true)}

# Add-on version (best-effort)
export ADDON_VERSION="${BUILD_VERSION:-$(cat /etc/BB8_ADDON_VERSION 2>/dev/null || echo unknown)}"

# optional log path override (if jq exists and value set)
if command -v jq >/dev/null 2>&1; then
  LP="$($JQ -r '.log_path // empty' "$OPTIONS" 2>/dev/null || true)"
  if [ -n "$LP" ] ; then export BB8_LOG_PATH="$LP"; fi
fi

echo "$(date -Is) [BB-8] Starting bridge controller… (ENABLE_BRIDGE_TELEMETRY=${ENABLE_BRIDGE_TELEMETRY})"

VIRTUAL_ENV="${VIRTUAL_ENV:-/opt/venv}"
PY="${VIRTUAL_ENV}/bin/python"
if [ ! -x "$PY" ]; then PY="$(command -v python3 || command -v python)"; fi
export PATH="${VIRTUAL_ENV}/bin:${PATH}"
# Optional probe for receipts
if [ "${PRINT_INTERP:-0}" = "1" ]; then echo "$PY"; exit 0; fi
exec "$PY" -m bb8_core.main
