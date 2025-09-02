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

# DIAG-BEGIN KEEPALIVE
if [[ "${DIAG_KEEPALIVE:-0}" == "1" ]]; then
  echo "$(date -Is) [BB-8] DIAG_KEEPALIVE=1: tail -f /dev/null active (container will not exit until killed)"
  tail -f /dev/null
fi
# DIAG-END KEEPALIVE

# DIAG-BEGIN SUPERVISED-LOOP
RESTART_LIMIT=${RESTART_LIMIT:-5}
RESTART_COUNT=0
RESTART_BACKOFF=${RESTART_BACKOFF:-2}
DISABLE_RESTART_LOOP=${DISABLE_RESTART_LOOP:-0}

trap 'echo "$(date -Is) [BB-8] RUNLOOP received SIGTERM"' SIGTERM
trap 'echo "$(date -Is) [BB-8] RUNLOOP received SIGINT"'  SIGINT

while true; do
  if [[ "$DISABLE_RESTART_LOOP" == "1" ]]; then
    echo "$(date -Is) [BB-8] DISABLE_RESTART_LOOP=1: subprocess auto-restart disabled"
    break
  fi
  RESTART_COUNT=$((RESTART_COUNT+1))
  if [[ "$RESTART_COUNT" -gt "$RESTART_LIMIT" ]]; then
    echo "$(date -Is) [BB-8] RESTART_LIMIT reached ($RESTART_LIMIT): auto-restart suspended"
    : > /tmp/bb8_restart_disabled
    break
  fi

  echo "$(date -Is) [BB-8] RUNLOOP attempt #$RESTART_COUNT"
  "$PY" -u /usr/src/app/main.py &  MAIN_PID=$!
  "$PY" -u /usr/src/app/echo_responder.py &  ECHO_PID=$!
  echo "$(date -Is) [BB-8] Started main.py PID=$MAIN_PID, echo_responder.py PID=$ECHO_PID"

  set +e
  wait -n
  EXIT_CODE=$?
  set -e

  DEAD="unknown"
  if ! kill -0 "$MAIN_PID" 2>/dev/null; then DEAD="main.py($MAIN_PID)"; elif ! kill -0 "$ECHO_PID" 2>/dev/null; then DEAD="echo_responder.py($ECHO_PID)"; fi
  echo "$(date -Is) [BB-8] Child exited: dead=$DEAD exit_code=$EXIT_CODE (main=$MAIN_PID echo=$ECHO_PID)"

  # terminate survivor cleanly then forcefully
  for P in "$MAIN_PID" "$ECHO_PID"; do
    if kill -0 "$P" 2>/dev/null; then
      kill -TERM "$P" 2>/dev/null || true
      sleep 1
      kill -KILL "$P" 2>/dev/null || true
    fi
  done

  [[ -f /tmp/bb8_restart_disabled ]] && { echo "$(date -Is) [BB-8] restart disabled flag present"; break; }
  sleep "$RESTART_BACKOFF"
done
# DIAG-END SUPERVISED-LOOP
