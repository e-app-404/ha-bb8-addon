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

##
# Common MQTT options (read both from env and options.json; export dual names)
##
# host/port
export MQTT_HOST=${MQTT_HOST:-$($JQ -r '.mqtt_host // empty' "$OPTIONS" 2>/dev/null || true)}
export MQTT_PORT=${MQTT_PORT:-$($JQ -r '.mqtt_port // empty' "$OPTIONS" 2>/dev/null || true)}

# username/password (export both styles)
_U=${MQTT_USERNAME:-$($JQ -r '.mqtt_user // empty' "$OPTIONS" 2>/dev/null || true)}
_P=${MQTT_PASSWORD:-$($JQ -r '.mqtt_password // empty' "$OPTIONS" 2>/dev/null || true)}
if [ -n "${_U:-}" ]; then export MQTT_USERNAME="$_U"; export MQTT_USER="$_U"; fi
if [ -n "${_P:-}" ]; then export MQTT_PASSWORD="$_P"; export MQTT_PASS="$_P"; fi

# namespace/base
_BASE=${MQTT_BASE:-$($JQ -r '.mqtt_base // empty' "$OPTIONS" 2>/dev/null || true)}
if [ -n "${_BASE:-}" ]; then export MQTT_BASE="$_BASE"; fi

# device hints
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
"$PY" -m bb8_core.main &
"$PY" /usr/src/app/bb8_core/echo_responder.py &
wait -n
