#!/bin/bash
set -euo pipefail
ts=$(date -u +%Y%m%d_%H%M%SZ)
mkdir -p reports/preflight
BB8_MAC="${BB8_MAC:-ED:ED:87:D7:27:50}"
MQTT_HOST="${MQTT_HOST:-192.168.0.129}"
LOG_BEFORE="reports/preflight/verify_before_${ts}.log"
LOG_AFTER="reports/preflight/verify_after_${ts}.log"
LOG_AFTER_LED="reports/preflight/verify_after_led_${ts}.log"
STATUS_FILE="reports/preflight/INT_HA_CONTROL_${ts}.status"

# Baseline retained discovery
python tools/discovery_migrate.py
python tools/verify_discovery.py | tee "$LOG_BEFORE"


# Automated timeout: waits for user input or 2 minutes, whichever comes first
echo "== Pause: restart the MQTT broker now, then press Enter (or wait 2 minutes) =="
read -t 120 -p "Press Enter to continue immediately, or wait for timeout..."
sleep 3

unset PUBLISH_LED_DISCOVERY || true
python tools/verify_discovery.py | tee "$LOG_AFTER"

AFTER_LED=""
BASELINE="FAIL"
AFTER_RESTART="FAIL"
AFTER_LED_STATUS=""

if grep -q "PASS" "$LOG_BEFORE"; then BASELINE="PASS"; fi
if grep -q "PASS" "$LOG_AFTER"; then AFTER_RESTART="PASS"; fi

# Optional LED path
if [ "${RUN_LED:-0}" = "1" ]; then
  export PUBLISH_LED_DISCOVERY=1
  python tools/discovery_migrate.py
  python tools/verify_discovery.py | tee "$LOG_AFTER_LED"
  if grep -q "PASS" "$LOG_AFTER_LED"; then AFTER_LED_STATUS="PASS"; else AFTER_LED_STATUS="FAIL"; fi
  AFTER_LED="$LOG_AFTER_LED"
fi

RECEIPTS="$LOG_BEFORE $LOG_AFTER"
if [ -n "$AFTER_LED" ]; then RECEIPTS="$RECEIPTS $AFTER_LED"; fi

cat > "$STATUS_FILE" <<EOF
INT_HA_CONTROL: Preflight
TIME: $ts
REAL_MAC: $BB8_MAC
HOST: $MQTT_HOST
BASELINE: $BASELINE
AFTER_RESTART: $AFTER_RESTART
AFTER_LED: $AFTER_LED_STATUS
RECEIPTS: $RECEIPTS
EOF

# Exit nonzero if AFTER_RESTART != PASS
if [ "$AFTER_RESTART" != "PASS" ]; then
  exit 1
fi
