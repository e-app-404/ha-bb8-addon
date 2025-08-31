#!/usr/bin/env bash
set -euo pipefail
MQTT_HOST=${MQTT_HOST:-127.0.0.1}
MQTT_PORT=${MQTT_PORT:-1883}
MOSQ="mosquitto_pub -h $MQTT_HOST -p $MQTT_PORT"
if [[ -n "${MQTT_USERNAME:-}" ]]; then MOSQ="$MOSQ -u $MQTT_USERNAME -P ${MQTT_PASSWORD:-}"; fi
# Remove any retained LED discovery under common legacy component/object_ids
for comp in light switch sensor binary_sensor; do
  for key in bb8_led led bb-8_led; do
    $MOSQ -t "homeassistant/$comp/$key/config" -r -n || true
  done
done
echo "PRUNE: legacy LED discovery topics cleared (if any)."
