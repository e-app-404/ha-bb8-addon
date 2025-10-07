#!/usr/bin/env bash
# INT-HA-CONTROL Step B: P0 Stability Monitor
# Monitors echo responder for 120 minutes (or test duration) for TypeError/coroutine errors

set -euo pipefail

CHECKPOINT_DIR="$(pwd)/reports/checkpoints/INT-HA-CONTROL"
DURATION_MINUTES="${P0_DURATION:-5}"  # Default 5 min for testing, set P0_DURATION=120 for full test
START_TIME=$(date +%s)
END_TIME=$((START_TIME + DURATION_MINUTES * 60))
LOG_FILE="$CHECKPOINT_DIR/p0_monitor.log"
START_SNAPSHOT="$CHECKPOINT_DIR/error_count_snapshot_start.json"
END_SNAPSHOT="$CHECKPOINT_DIR/error_count_snapshot_end.json"
COMPARISON_FILE="$CHECKPOINT_DIR/error_count_comparison.json"

echo "=== INT-HA-CONTROL Step B: P0 Stability Monitor ===" | tee "$LOG_FILE"
echo "Duration: ${DURATION_MINUTES} minutes" | tee -a "$LOG_FILE"
echo "Start: $(date -r $START_TIME)" | tee -a "$LOG_FILE"
echo "End: $(date -r $END_TIME)" | tee -a "$LOG_FILE"
echo

# Ensure required environment variables
export MQTT_HOST=${MQTT_HOST:-core-mosquitto}
export HA_URL=${HA_URL:-http://192.168.0.129:8123}
export HA_TOKEN=${HA_TOKEN:-}

if [[ -z "$HA_TOKEN" ]]; then
    echo "ERROR: HA_TOKEN not set. Source .evidence.env first." | tee -a "$LOG_FILE"
    exit 1
fi

# Take initial error count snapshot
echo "Taking initial error count snapshot..." | tee -a "$LOG_FILE"
INITIAL_ERRORS=$(curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/hassio/addons/local_beep_boop_bb8/logs" | egrep -c "TypeError|coroutine" || echo "0")

cat > "$START_SNAPSHOT" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "epoch": $START_TIME,
  "typeerror_count": $INITIAL_ERRORS,
  "coroutine_count": $INITIAL_ERRORS,
  "total_errors": $INITIAL_ERRORS
}
EOF

echo "Initial error count: $INITIAL_ERRORS" | tee -a "$LOG_FILE"

# Monitor loop
echo "Starting continuous monitoring..." | tee -a "$LOG_FILE"
SAMPLE_COUNT=0
while [[ $(date +%s) -lt $END_TIME ]]; do
    CURRENT_TIME=$(date +%s)
    ELAPSED_MINUTES=$(( (CURRENT_TIME - START_TIME) / 60 ))
    REMAINING_MINUTES=$(( (END_TIME - CURRENT_TIME) / 60 ))
    
    # Sample current error count
    CURRENT_ERRORS=$(curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/hassio/addons/local_beep_boop_bb8/logs" | egrep -c "TypeError|coroutine" || echo "0")
    NEW_ERRORS=$((CURRENT_ERRORS - INITIAL_ERRORS))
    
    SAMPLE_COUNT=$((SAMPLE_COUNT + 1))
    echo "[$(date -Iseconds)] Sample $SAMPLE_COUNT: Elapsed ${ELAPSED_MINUTES}m, Remaining ${REMAINING_MINUTES}m, Errors: ${CURRENT_ERRORS} (New: ${NEW_ERRORS})" | tee -a "$LOG_FILE"
    
    # Alert on new errors
    if [[ $NEW_ERRORS -gt 0 ]]; then
        echo "⚠️  NEW ERRORS DETECTED: $NEW_ERRORS" | tee -a "$LOG_FILE"
        echo "❌ P0 STABILITY FAILED" | tee -a "$LOG_FILE"
        exit 1
    fi
    
    # Sample every 30 seconds for demonstration (adjust for full test)
    sleep 30
done

# Take final snapshot
echo "Taking final error count snapshot..." | tee -a "$LOG_FILE"
FINAL_ERRORS=$(curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/hassio/addons/local_beep_boop_bb8/logs" | egrep -c "TypeError|coroutine" || echo "0")

cat > "$END_SNAPSHOT" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "epoch": $(date +%s),
  "typeerror_count": $FINAL_ERRORS,
  "coroutine_count": $FINAL_ERRORS,
  "total_errors": $FINAL_ERRORS
}
EOF

# Generate comparison
NEW_ERRORS=$((FINAL_ERRORS - INITIAL_ERRORS))
if [[ $NEW_ERRORS -eq 0 ]]; then
    RESULT="OK"
    STATUS="PASS"
else
    RESULT="FAIL"
    STATUS="FAIL"
fi

cat > "$COMPARISON_FILE" <<EOF
{
  "window_minutes": $DURATION_MINUTES,
  "start_errors": $INITIAL_ERRORS,
  "end_errors": $FINAL_ERRORS,
  "new_errors": $NEW_ERRORS,
  "result": "$RESULT",
  "status": "$STATUS",
  "samples_taken": $SAMPLE_COUNT,
  "monitoring_complete": "$(date -Iseconds)"
}
EOF

echo "=== P0 Monitoring Complete ===" | tee -a "$LOG_FILE"
echo "Duration: ${DURATION_MINUTES} minutes" | tee -a "$LOG_FILE"
echo "Samples taken: $SAMPLE_COUNT" | tee -a "$LOG_FILE"
echo "Initial errors: $INITIAL_ERRORS" | tee -a "$LOG_FILE"
echo "Final errors: $FINAL_ERRORS" | tee -a "$LOG_FILE"
echo "New errors: $NEW_ERRORS" | tee -a "$LOG_FILE"
echo "Result: $RESULT" | tee -a "$LOG_FILE"

if [[ "$RESULT" == "OK" ]]; then
    echo "✅ P0 STABILITY: PASS" | tee -a "$LOG_FILE"
    exit 0
else
    echo "❌ P0 STABILITY: FAIL" | tee -a "$LOG_FILE"
    exit 1
fi