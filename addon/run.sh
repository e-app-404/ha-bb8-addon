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

getopt_opt() { "$JQ" -r "$1 // empty" "$OPTIONS" 2>/dev/null || true; }
# Accept both legacy and canonical option names
H=$(getopt_opt '.mqtt_host // .mqtt_broker')
U=$(getopt_opt '.mqtt_user // .mqtt_username')
P=$(getopt_opt '.mqtt_password // .mqtt_pass')
B=$(getopt_opt '.mqtt_base // .mqtt_topic_prefix')
PORT=$(getopt_opt '.mqtt_port // .mqtt_broker_port')
[ -z "$PORT" ] && PORT=1883
[ -z "$B" ] && B=bb8
export MQTT_HOST="${MQTT_HOST:-$H}"
export MQTT_PORT="${MQTT_PORT:-$PORT}"
export MQTT_USERNAME="${MQTT_USERNAME:-$U}"
export MQTT_PASSWORD="${MQTT_PASSWORD:-$P}"
export MQTT_BASE="${MQTT_BASE:-$B}"
# Also export the alternative var names used by some modules
export MQTT_USER="${MQTT_USER:-$MQTT_USERNAME}"
export MQTT_PASS="${MQTT_PASS:-$MQTT_PASSWORD}"
export BB8_NAME=${BB8_NAME:-$(getopt_opt '.bb8_name')}
export BB8_MAC=${BB8_MAC:-$(getopt_opt '.bb8_mac')}

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
# Start main and echo responder in background, block until one exits
"$PY" -m bb8_core.main &
python3 -u /usr/src/app/echo_responder.py &
# Block until either process exits (Supervisor will restart on failure)
wait -n
