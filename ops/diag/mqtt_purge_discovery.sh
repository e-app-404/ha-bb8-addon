#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 --device-id <id> [--base <mqtt_base>] [--dry-run|--execute]"
  echo "Defaults: --dry-run; requires explicit --execute for actual purge."
  exit 2
}

BASE="${MQTT_BASE:-bb8}"
DEVICE_ID=""
MODE="dry"  # default safety

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base) BASE="$2"; shift 2;;
    --device-id) DEVICE_ID="$2"; shift 2;;
    --dry-run) MODE="dry"; shift;;
    --execute) MODE="exec"; shift;;
    *) usage;;
  esac
done

[[ -z "$DEVICE_ID" ]] && { echo "ERR: --device-id is required"; exit 3; }

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing $1 (install mosquitto-clients)"; exit 4; }; }
need mosquitto_pub

set -a; [ -f .evidence.env ] && source .evidence.env; set +a
HOST="${MQTT_HOST:?set MQTT_HOST in .evidence.env}"
PORT="${MQTT_PORT:-1883}"
USER="${MQTT_USER:-}"
PASS="${MQTT_PASSWORD:-${MQTT_PASS:-}}"
AUTH=(); [[ -n "$USER" ]] && AUTH+=( -u "$USER" ); [[ -n "$PASS" ]] && AUTH+=( -P "$PASS" )

PREFIX="homeassistant"
FILTER="$PREFIX/#/${DEVICE_ID}/#"

echo "Target (scoped): $FILTER"
TOPICS=()
if command -v mosquitto_sub >/dev/null 2>&1; then
  # short timeout to avoid hanging when no retained topics
  mapfile -t TOPICS < <(timeout 2s mosquitto_sub -h "$HOST" -p "$PORT" "${AUTH[@]}" -t "$FILTER" -v 2>/dev/null | awk '{print $1}' | sort -u)
fi

if [[ "$MODE" = "dry" ]]; then
  echo "DRY-RUN: would purge ${#TOPICS[@]} retained topics under $FILTER"; printf "%s\n" "${TOPICS[@]}"; exit 0
fi

# exec (requires --execute)
for t in "${TOPICS[@]}"; do
  echo "Purging retain: $t"
  mosquitto_pub -h "$HOST" -p "$PORT" "${AUTH[@]}" -t "$t" -n -r
done
echo "DONE"
