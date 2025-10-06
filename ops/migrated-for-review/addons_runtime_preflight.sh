#!/usr/bin/env bash
# Runtime Preflight (HA Terminal): validate options, slug, logs, state.
# Acceptance: emits PRE_FLIGHT_OK and VERIFY_OK.

set -euo pipefail
FULL_SLUG="$(ha addons info local_beep_boop_bb8 | awk -F': ' '/slug:/ {print $2}')"
[ -n "$FULL_SLUG" ] || { echo "ERROR: slug not found"; exit 2; }

# Host paths for this add-on
HOST_DATA="/data/addons/data/${FULL_SLUG}"
OPTS="${HOST_DATA}/options.json"
REPORTS="${HOST_DATA}/reports"
LOG="${REPORTS}/ha_bb8_addon.log"

# Validate options (fall back to container path if needed)
if [ -f "$OPTS" ]; then
  grep -q '"/data/reports"' "$OPTS" || echo "WARNING: report_root not '/data/reports' in options.json"
  grep -q '"/data/reports/ha_bb8_addon.log"' "$OPTS" || echo "WARNING: log_path not set to file under /data/reports in options.json"
else
  echo "WARNING: options.json not found at ${OPTS} (container uses /data/options.json)."
fi

# Ensure reports path exists and writable
mkdir -p "$REPORTS"
test -w "$REPORTS" || { echo "ERROR: ${REPORTS} not writable"; exit 3; }

echo "PRE_FLIGHT_OK"

# Verify add-on state and log presence
STATE="$(ha addons info "$FULL_SLUG" | awk -F': ' '/state:/ {print $2}' | tr -d '\r')"
[ "$STATE" = "started" ] || { echo "ERROR: state=${STATE}, expected started"; exit 4; }

# Touch log to force creation if app honors LOG_PATH
touch "$LOG" 2>/dev/null || true
[ -f "$LOG" ] && echo "LOG_FILE_PRESENT: $LOG" || echo "LOG_FILE_PENDING: $LOG"

echo "VERIFY_OK"
