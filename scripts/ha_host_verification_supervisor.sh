#!/bin/bash
# HA-BB8 Supervisor-only Verification Script
# Generated: $(date -u)
# Objective: Prove updated HA-BB8 add-on is healthy in Supervisor-only mode and MQTT echo pipeline is live
# This report will reference this script for reproducibility

SLUG="local_beep_boop_bb8"
TS="$(date +%Y%m%d_%H%M%S)"
REPORT="/config/hestia/diagnostics/reports/ha_bb8/ha_bb8_verification_supervisor_${TS}.txt"
SCRIPT_REF="$(basename "$0")"

HOST="192.168.0.129"
PORT="1883"
USER="mqtt_bb8"
PASS="mqtt_bb8"
BASE="bb8"

{
  echo "=== HA-BB8 Supervisor-only Verification Report ==="
  echo "Timestamp: $TS"
  echo "Script Reference: $SCRIPT_REF"
  echo

  echo "--- 0) Add-on slug ---"
  ha addons list | grep -i bb8
  echo

  echo "--- 1) Sanity: version, options, health ---"
  ha addons info "$SLUG"
  echo
  ha addons options "$SLUG" | awk '
    in_block == 0 && /^long_description:/ {in_block=1; next}
    in_block == 1 && /^machine:/ {in_block=0}
    in_block == 1 {next}
    {print}
  '
  echo
  echo "--- Last 200 log lines ---"
  ha addons logs "$SLUG" | tail -n 200
  echo

  echo "--- 2) Live follow for health (15s cadence) ---"
  echo "(Next ~30s: capturing HEALTH_SUMMARY, echo_responder, MQTT, Subscribed, Started, Child exited)"
  timeout 35 ha addons logs -f "$SLUG" | grep -iE 'HEALTH_SUMMARY|echo_responder|MQTT|Subscribed|Started|Child exited'
  echo

  echo "--- 3) End-to-end echo probe (host → add-on → host) ---"
  echo "(Capturing echo pipeline: ack, state, echo_roundtrip)"
  mosquitto_sub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" -t "$BASE/#" -W 6 -v &
  SP=$!; sleep 0.4
  mosquitto_pub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" -t "$BASE/echo/cmd" -m '{"value":1}'
  wait $SP || true
  echo

  echo "--- 4) Quick ACL sanity (optional) ---"
  mosquitto_sub -R -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" -t "$BASE/#" -W 10 -v
  echo

  echo "=== End of Report ==="
  echo "Script used: $SCRIPT_REF"
} > "$REPORT"

cat "$REPORT"
echo -e "\nReport saved to $REPORT"
