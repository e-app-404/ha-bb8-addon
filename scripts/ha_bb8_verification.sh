
#!/bin/bash
SLUG="local_beep_boop_bb8"
TS="$(date +%Y%m%d_%H%M%S)"
REPORT_DIR="/config/hestia/diagnostics/reports/ha_bb8"
REPORT="${REPORT_DIR}/ha_bb8_verification_${TS}.txt"

# Sleep duration between heartbeat snapshots (in seconds)
HEARTBEAT_SLEEP=12

# Ensure the report directory exists
mkdir -p "$REPORT_DIR"

{
  OPTIONS_JSON=$(ha addons options "$SLUG" 2>/dev/null)
  if [[ -z "$OPTIONS_JSON" ]]; then
    echo "Error: Unable to retrieve options for $SLUG or output is empty."
  elif echo "$OPTIONS_JSON" | jq empty >/dev/null 2>&1; then
    echo "$OPTIONS_JSON" | jq -c '{enable_echo,enable_health_checks,log_path,mqtt_host,mqtt_port}'
  else
    echo "$OPTIONS_JSON"
  fi
  LOG_GREP_PATTERN='run\.sh entry|RUNLOOP attempt|Started bb8_core\.main PID=|Started bb8_core\.echo_responder PID=|Child exited|HEALTH_SUMMARY'
  ha addons logs "$SLUG" -n 400 | grep -E "$LOG_GREP_PATTERN"
  echo -e "\n=== Last 400 log lines (key DIAG) ==="
  ha addons logs "$SLUG" -n 400 | grep -E "$LOG_GREP_PATTERN"
  ha addons logs "$SLUG" -n 400 | grep -E "$LOG_GREP_PATTERN"
  sleep "$HEARTBEAT_SLEEP"
  echo -e "--- SNAPSHOT B ---"
  ha addons logs "$SLUG" -n 200 | grep 'HEALTH_SUMMARY' | tail -n 3
  ha addons logs "$SLUG" -n 200 | grep 'HEALTH_SUMMARY' | tail -n 3
} > "$REPORT" 2> "${REPORT}.err"

cat "$REPORT"
if [[ -s "${REPORT}.err" ]]; then
  echo -e "\nErrors captured during execution:"
  cat "${REPORT}.err"
fi
echo -e "\nReport saved to $REPORT"

cat "$REPORT"
echo -e "\nReport saved to $REPORT"