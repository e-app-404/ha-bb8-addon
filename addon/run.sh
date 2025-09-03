#!/usr/bin/with-contenv bash
set -Eeuo pipefail
# Optional shell tracing for deep diagnostics
if [ "${DIAG_TRACE:-0}" = "1" ]; then set -x; fi

export PYTHONUNBUFFERED=1
export PYTHONPATH=/usr/src/app:${PYTHONPATH:-}
cd /usr/src/app

# ---------- Options & Environment ----------
OPTIONS=/data/options.json
JQ='/usr/bin/jq'

# Helper to read option keys with legacy fallbacks
getopt_opt() { "$JQ" -r "$1 // empty" "$OPTIONS" 2>/dev/null || true; }

# MQTT + feature flags
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
export MQTT_USER="${MQTT_USER:-$MQTT_USERNAME}"
export MQTT_PASS="${MQTT_PASS:-$MQTT_PASSWORD}"

# Feature toggles
ENABLE_ECHO_RAW=$("$JQ" -r '.enable_echo // true' "$OPTIONS" 2>/dev/null || echo "true")
ENABLE_HEALTH_CHECKS=$("$JQ" -r '.enable_health_checks // false' "$OPTIONS" 2>/dev/null || echo "false")
if [ "$ENABLE_HEALTH_CHECKS" = "true" ]; then export ENABLE_HEALTH_CHECKS=1; else export ENABLE_HEALTH_CHECKS=0; fi

# Resolve/add-on version (best-effort)
export ADDON_VERSION="${BUILD_VERSION:-$(cat /etc/BB8_ADDON_VERSION 2>/dev/null || echo unknown)}"

# ---------- Log path normalization ----------
# Prefer options.json log_path; fall back to /data/reports/ha_bb8_addon.log
LP="$($JQ -r '.log_path // empty' "$OPTIONS" 2>/dev/null || true)"
[ -z "$LP" ] && LP="/data/reports/ha_bb8_addon.log"
# Remap any host-only path to container /data
case "$LP" in
  /addons/*) LP="/data/reports/ha_bb8_addon.log" ;;
esac
mkdir -p "$(dirname "$LP")" 2>/dev/null || true
export BB8_LOG_PATH="$LP"

# ---------- Logging helpers (FD-based; no tee race) ----------
LOG_FD=""
# ---------- Logging helpers (tee-append; flush every emit) ----------
diag_emit() {
  local ts msg; ts="$(date -Is)"; msg="$*"
  if [ -n "${BB8_LOG_PATH:-}" ] && [ -w "$(dirname "$BB8_LOG_PATH")" ]; then
    printf "%s [BB-8] %s\n" "$ts" "$msg" | tee -a "$BB8_LOG_PATH" >/dev/null || printf "%s [BB-8] %s\n" "$ts" "$msg"
    sync || true
  else
    printf "%s [BB-8] %s\n" "$ts" "$msg"
  fi
}
trap 'diag_emit "RUNLOOP received SIGTERM"; exit 143' SIGTERM
trap 'diag_emit "RUNLOOP received SIGINT";  exit 130' SIGINT
trap 'diag_emit "RUNLOOP EXIT trap"' EXIT

diag_emit "run.sh entry (version=${ADDON_VERSION}) wd=$(pwd) LOG=${BB8_LOG_PATH} HEALTH=${ENABLE_HEALTH_CHECKS} ECHO=${ENABLE_ECHO_RAW}"

# ---------- Python selection ----------
VIRTUAL_ENV="${VIRTUAL_ENV:-/opt/venv}"
PY="${VIRTUAL_ENV}/bin/python"
if [ ! -x "$PY" ]; then PY="$(command -v python3 || command -v python)"; fi
export PATH="${VIRTUAL_ENV}/bin:${PATH}"


# ---------- Single control-plane guard for echo_responder ----------
S6_ECHO_RUN="/etc/services.d/echo_responder/run"
S6_ECHO_DOWN="/etc/services.d/echo_responder/down"
RUNSH_MUST_SPAWN_ECHO=1
if [ -f "$S6_ECHO_RUN" ] && [ ! -f "$S6_ECHO_DOWN" ]; then
  RUNSH_MUST_SPAWN_ECHO=0
  diag_emit "NOTICE: s6-managed echo_responder detected; run.sh will NOT spawn echo (avoid dual supervision)"
fi


# ---------- Supervised loop ----------
RESTART_LIMIT=${RESTART_LIMIT:-0}      # 0 = unlimited (we rely on manual flag /tmp/bb8_restart_disabled)
RESTART_COUNT=0
RESTART_BACKOFF=${RESTART_BACKOFF:-5}  # default backoff hardened to 5s

while true; do
  # Optional kill switch
  if [ -f /tmp/bb8_restart_disabled ]; then
    diag_emit "restart disabled flag present; halting run loop"
    break
  fi
  RESTART_COUNT=$((RESTART_COUNT+1))
  if [ "$RESTART_LIMIT" -gt 0 ] && [ "$RESTART_COUNT" -gt "$RESTART_LIMIT" ]; then
    diag_emit "RESTART_LIMIT reached ($RESTART_LIMIT): auto-restart suspended"
    : > /tmp/bb8_restart_disabled
    break
  fi

  diag_emit "RUNLOOP attempt #$RESTART_COUNT"

  # Start main
  "$PY" -u -m bb8_core.main &  MAIN_PID=$!
  diag_emit "Started bb8_core.main PID=$MAIN_PID"

  # Start echo if enabled and not s6-managed
  ECHO_PID=0
  if [ "$ENABLE_ECHO_RAW" = "true" ] && [ "$RUNSH_MUST_SPAWN_ECHO" = "1" ]; then
    "$PY" -u -m bb8_core.echo_responder &  ECHO_PID=$!
    # NOTE: DIAG grep depends on this exact token
    diag_emit "Started bb8_core.echo_responder PID=$ECHO_PID"
  else
    reason="echo_responder disabled"
    [ "$ENABLE_ECHO_RAW" = "true" ] && [ "$RUNSH_MUST_SPAWN_ECHO" = "0" ] && reason="echo_responder supervised by s6"
    diag_emit "Started bb8_core.main PID=$MAIN_PID (${reason})"
  fi

  # Wait for first child to exit
  set +e
  wait -n
  EXIT_CODE=$?
  set -e

  DEAD="unknown"
  if [ "$MAIN_PID" -ne 0 ] && ! kill -0 "$MAIN_PID" 2>/dev/null; then
    DEAD="main.py($MAIN_PID)"
  elif [ "$ECHO_PID" -ne 0 ] && ! kill -0 "$ECHO_PID" 2>/dev/null; then
    DEAD="echo_responder.py($ECHO_PID)"
  fi
  diag_emit "Child exited: dead=$DEAD exit_code=$EXIT_CODE (main=$MAIN_PID echo=$ECHO_PID)"

  # Terminate survivor cleanly then forcefully
  for P in "$MAIN_PID" "$ECHO_PID"; do
    if [ "${P:-0}" -ne 0 ] && kill -0 "$P" 2>/dev/null; then
      kill -TERM "$P" 2>/dev/null || true
      sleep 1
      kill -KILL "$P" 2>/dev/null || true
    fi
  done

  sleep "$RESTART_BACKOFF"
done

# --- DIAG helper (console + file; always line-buffered) ---
log_diag() {
  # Print to stdout and append to log file if set/exists
  # Use printf for predictable formatting; tee -a when log file is writable
  local ts msg; ts="$(date -Is)"; msg="$*"
  if [ -n "${BB8_LOG_PATH:-}" ] && [ -w "$(dirname "$BB8_LOG_PATH")" ]; then
    printf "%s [BB-8] %s\n" "$ts" "$msg" | tee -a "$BB8_LOG_PATH" >/dev/null || printf "%s [BB-8] %s\n" "$ts" "$msg"
  else
    printf "%s [BB-8] %s\n" "$ts" "$msg"
  fi
}

# ---------- Single control-plane guard for echo_responder ----------
# If an s6 echo_responder service is present *and not marked down*, do not spawn echo from run.sh.
S6_ECHO_RUN="/etc/services.d/echo_responder/run"
S6_ECHO_DOWN="/etc/services.d/echo_responder/down"
if [ -f "$S6_ECHO_RUN" ] && [ ! -f "$S6_ECHO_DOWN" ]; then
  RUNSH_MUST_SPAWN_ECHO=0
  log_diag "NOTICE: s6-managed echo_responder detected; run.sh will NOT spawn echo (avoid dual supervision)"
else
  RUNSH_MUST_SPAWN_ECHO=1
fi

#!/usr/bin/with-contenv bash
set -euo pipefail
# Enable shell tracing when DIAG_TRACE=1 (helps catch silent failures)
if [ "${DIAG_TRACE:-0}" = "1" ]; then set -x; fi

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

# Toggle: health checks (propagate to Python to create heartbeats)
ENABLE_HEALTH_CHECKS_RAW=$($JQ -r '.enable_health_checks // false' "$OPTIONS" 2>/dev/null || echo "false")
if [ "$ENABLE_HEALTH_CHECKS_RAW" = "true" ]; then
  export ENABLE_HEALTH_CHECKS=1
else
  export ENABLE_HEALTH_CHECKS=0
fi

# Toggle: health checks (propagate to Python so heartbeats are created)
ENABLE_HEALTH_CHECKS_RAW=$($JQ -r '.enable_health_checks // false' "$OPTIONS" 2>/dev/null || echo "false")
if [ "$ENABLE_HEALTH_CHECKS_RAW" = "true" ]; then
  export ENABLE_HEALTH_CHECKS=1
else
  export ENABLE_HEALTH_CHECKS=0
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

log_diag "Starting bridge controller… (ENABLE_BRIDGE_TELEMETRY=${ENABLE_BRIDGE_TELEMETRY})"

umask 0022

# ---------- Safe option readers ----------
# Resolve jq path safely; tolerate absence of jq and options.json
JQ_BIN="$(command -v jq 2>/dev/null || echo '')"
opt_str() {
  # $1: jq expr, $2: default
  if [ -n "$JQ_BIN" ] && [ -f "$OPTIONS" ]; then
    "$JQ_BIN" -r "$1 // empty" "$OPTIONS" 2>/dev/null || true
  else
    echo ""
  fi
}
opt_bool() {
  # $1: jq expr, $2: default(true|false)
  local dflt="${2:-false}" v=""
  if [ -n "$JQ_BIN" ] && [ -f "$OPTIONS" ]; then
    v=$("$JQ_BIN" -r "$1 // ${dflt}" "$OPTIONS" 2>/dev/null || echo "${dflt}")
  else
    v="${dflt}"
  fi
  printf '%s' "$v"
}

# ---------- Read options with explicit defaults ----------
# Bridge telemetry (default: false)
ENABLE_BRIDGE_TELEMETRY_RAW="$(opt_bool '.enable_bridge_telemetry' false)"
if [ "$ENABLE_BRIDGE_TELEMETRY_RAW" = "true" ]; then export ENABLE_BRIDGE_TELEMETRY=1; else export ENABLE_BRIDGE_TELEMETRY=0; fi

# Health checks (default: false) — drives Python heartbeats
ENABLE_HEALTH_CHECKS_RAW="$(opt_bool '.enable_health_checks' false)"
if [ "$ENABLE_HEALTH_CHECKS_RAW" = "true" ]; then export ENABLE_HEALTH_CHECKS=1; else export ENABLE_HEALTH_CHECKS=0; fi

# Echo responder (default: true per UI)
ENABLE_ECHO_RAW="$(opt_bool '.enable_echo' true)"

# Optional log path override (string); empty -> use default later
LP="$(opt_str '.log_path')"
if [ -n "$LP" ]; then BB8_LOG_PATH="$LP"; fi

echo "$(date -Is) [BB-8] Starting bridge controller… (ENABLE_BRIDGE_TELEMETRY=${ENABLE_BRIDGE_TELEMETRY})"

# ---------- Log path normalization ----------
normalize_log_path() {
  local p="${BB8_LOG_PATH:-}"
  # Default if unset/empty
  if [ -z "$p" ]; then p="/data/reports/ha_bb8_addon.log"; fi
  # If relative, anchor under /data/reports
  case "$p" in
    /*) : ;;
    *)  p="/data/reports/$p" ;;
  esac
  # Remap known host mounts to /data
  case "$p" in
    /addons/*|/config/*|/media/*|/share/*|/ssl/*|/mnt/*|/homeassistant/*)
      p="/data/reports/ha_bb8_addon.log"
      ;;
  esac
  # Ensure parent dir exists (or fallback to /tmp)
  local dir; dir="$(dirname "$p")"
  if ! mkdir -p "$dir" 2>/dev/null; then
    p="/tmp/bb8_addon.log"
    dir="/tmp"
    mkdir -p "$dir" 2>/dev/null || true
  fi
  # Verify writeability by touching file; fallback to /tmp on failure
  if ! ( : > "$p" ) 2>/dev/null; then
    p="/tmp/bb8_addon.log"
    : > "$p" 2>/dev/null || true
  fi
  BB8_LOG_PATH="$p"
  export BB8_LOG_PATH
}

# Single point logging helper (logs to file if possible, else stderr)
log_diag() {
  # $1: message (without timestamp)
  local ts; ts="$(date -Is)"
  if [ -n "${BB8_LOG_PATH:-}" ] && [ -w "$(dirname "$BB8_LOG_PATH")" ]; then
    printf "%s %s\n" "$ts" "$1" | tee -a "$BB8_LOG_PATH" >/dev/null || printf "%s %s (filelog failed)\n" "$ts" "$1" >&2
  else
    printf "%s %s\n" "$ts" "$1" >&2
  fi
}

normalize_log_path
log_diag "run.sh entry (version=${ADDON_VERSION}) wd=$(pwd) LOG=${BB8_LOG_PATH} HEALTH=${ENABLE_HEALTH_CHECKS} ECHO=${ENABLE_ECHO_RAW}"


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
RESTART_BACKOFF=${RESTART_BACKOFF:-5}  # default backoff hardened to 5s
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

  log_diag "RUNLOOP attempt #$RESTART_COUNT"
  # Use module execution to avoid path drift; PYTHONPATH already includes /usr/src/app
  "$PY" -u -m bb8_core.main &  MAIN_PID=$!
  log_diag "Started bb8_core.main PID=$MAIN_PID"

  # Spawn echo only if:
  # (a) enable_echo is true, and
  # (b) run.sh is the designated supervisor (no active s6 run without down)
  if [ "$ENABLE_ECHO_RAW" = "true" ] && [ "$RUNSH_MUST_SPAWN_ECHO" = "1" ]; then
    "$PY" -u -m bb8_core.echo_responder &  ECHO_PID=$!
    # NOTE: The grep in diagnostics relies on this exact token "Started bb8_core.echo_responder PID="
    log_diag "Started bb8_core.echo_responder PID=$ECHO_PID"
  else
    ECHO_PID=0
    reason="echo_responder disabled"
    [ "$ENABLE_ECHO_RAW" = "true" ] && [ "$RUNSH_MUST_SPAWN_ECHO" = "0" ] && reason="echo_responder supervised by s6"
    log_diag "Started bb8_core.main PID=$MAIN_PID (${reason})"
  fi

  set +e
  wait -n
  EXIT_CODE=$?
  set -e

  DEAD="unknown"
  if ! kill -0 "$MAIN_PID" 2>/dev/null; then
    DEAD="main.py($MAIN_PID)"
  elif [ "$ECHO_PID" -gt 0 ] && ! kill -0 "$ECHO_PID" 2>/dev/null; then
    DEAD="echo_responder.py($ECHO_PID)"
  fi
  log_diag "Child exited: dead=$DEAD exit_code=$EXIT_CODE (main=$MAIN_PID echo=$ECHO_PID)"

  # terminate survivor cleanly then forcefully
  for P in "$MAIN_PID" ${ECHO_PID:-0}; do
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
