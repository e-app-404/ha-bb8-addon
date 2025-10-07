#!/usr/bin/env bash
set -euo pipefail
HOST="${MQTT_HOST:-192.168.0.129}"; USER="${MQTT_USER:-mqtt_bb8}"; PASS="${MQTT_PASSWORD:-mqtt_bb8}"
BASE="${MQTT_BASE:-bb8}"; TS=$(date -u +%Y%m%dT%H%M%SZ)
python3 reports/checkpoints/INT-HA-CONTROL/mqtt_health_echo_test.py \
  --host "$HOST" --port "${MQTT_PORT:-1883}" --user "$USER" --password "$PASS" --base "$BASE" \
  --sla-ms 1000 --out "reports/checkpoints/health/echo_health_${TS}.json"