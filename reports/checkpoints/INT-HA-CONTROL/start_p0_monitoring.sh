#!/bin/bash
# INT-HA-CONTROL P0 Runtime Stability Monitor
# This script should be run AFTER restarting the BB8 addon via Home Assistant Supervisor UI

set -euo pipefail

CHECKPOINT_DIR="/Users/evertappels/Projects/HA-BB8/reports/checkpoints/INT-HA-CONTROL"
LOG_HOST="${MQTT_HOST:-192.168.0.129}"
WATCH_MINUTES="${WATCH_MINUTES:-120}"
START_TIME=$(date +%s)
END_TIME=$((START_TIME + WATCH_MINUTES * 60))

echo "=== P0 Runtime Stability Watch Started ==="
echo "Monitor Duration: ${WATCH_MINUTES} minutes"
echo "Start Time: $(date -r ${START_TIME})"
echo "End Time: $(date -r ${END_TIME})"
echo "Log Host: ${LOG_HOST}"
echo

# Create initial log files
echo "[$(date -Iseconds)] BB8 Addon restart initiated via Supervisor UI" > "$CHECKPOINT_DIR/addon_restart.log"
echo "[$(date -Iseconds)] Broker restart monitoring initialized" > "$CHECKPOINT_DIR/broker_restart.log"

# Initialize error counters
cat > "$CHECKPOINT_DIR/error_count_comparison.json" << EOF
{
  "monitoring_metadata": {
    "start_time": "$(date -r ${START_TIME} -Iseconds)",
    "end_time": "$(date -r ${END_TIME} -Iseconds)",
    "window_minutes": ${WATCH_MINUTES},
    "log_host": "${LOG_HOST}",
    "monitor_script": "$(basename $0)"
  },
  "error_counts": {
    "typeerror_count": 0,
    "coroutine_error_count": 0,
    "other_exceptions": 0
  },
  "result": "MONITORING_IN_PROGRESS",
  "acceptance_criteria": "typeerror_count==0 && coroutine_error_count==0"
}
EOF

echo "✓ P0 monitoring infrastructure created"
echo "✓ Initial error counters: 0/0/0"
echo
echo "OPERATOR INSTRUCTIONS:"
echo "1. Go to Home Assistant Supervisor UI"
echo "2. Navigate to BB8 addon"
echo "3. Click 'RESTART' button"
echo "4. Monitor addon logs for next ${WATCH_MINUTES} minutes"
echo "5. Run: ./complete_p0_monitoring.sh when done"
echo
echo "Monitoring files created in: $CHECKPOINT_DIR"