
#!/usr/bin/env bash
set -euo pipefail
: "${MQTT_HOST:?set}"; : "${MQTT_PORT:=1883}"
USER_FLAG=""; PASS_FLAG=""
if [ "${MQTT_USERNAME:-}" != "" ]; then USER_FLAG="-u ${MQTT_USERNAME}"; fi
if [ "${MQTT_PASSWORD:-}" != "" ]; then PASS_FLAG="-P ${MQTT_PASSWORD}"; fi
for t in \
  'homeassistant/sensor/bb8_rssi/config' \
  'homeassistant/binary_sensor/bb8_presence/config'
do
  echo "PRUNE $t"
  mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" $USER_FLAG $PASS_FLAG -t "$t" -r -n
done
echo "DONE"
