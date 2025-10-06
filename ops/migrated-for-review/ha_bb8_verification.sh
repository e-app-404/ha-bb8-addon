#!/bin/bash
SLUG="local_beep_boop_bb8"
TS="$(date +%Y%m%d_%H%M%S)"
REPORT="/config/hestia/diagnostics/reports/ha_bb8/ha_bb8_verification_${TS}.txt"

{
  echo -e "=== Add-on info ==="
  ha addons info "$SLUG"

  echo -e "\n=== Options slice ==="
  OPTIONS_JSON=$(ha addons options "$SLUG" 2>/dev/null)
  if echo "$OPTIONS_JSON" | jq empty >/dev/null 2>&1; then
    echo "$OPTIONS_JSON" | jq -c '{enable_echo,enable_health_checks,log_path,mqtt_host,mqtt_port}'
  else
    echo "$OPTIONS_JSON"
  fi

  echo -e "\n=== Last 400 log lines (key DIAG) ==="
  ha addons logs "$SLUG" -n 400 | grep -E 'run\.sh entry|RUNLOOP attempt|Started bb8_core\.main PID=|Started bb8_core\.echo_responder PID=|Child exited|HEALTH_SUMMARY'

  echo -e "\n=== Heartbeat summary (expect ages to vary over time) ==="
  echo -e "--- SNAPSHOT A ---"
  ha addons logs "$SLUG" -n 200 | grep 'HEALTH_SUMMARY' | tail -n 3
  sleep 12
  echo -e "--- SNAPSHOT B ---"
  ha addons logs "$SLUG" -n 200 | grep 'HEALTH_SUMMARY' | tail -n 3

  echo -e "\n=== Supervisor overall logs (last 200 lines) ==="
  ha supervisor logs -n 200 | grep -iE 'hassio|supervisor|bb8'
} > "$REPORT"

cat "$REPORT"
echo -e "\nReport saved to $REPORT"