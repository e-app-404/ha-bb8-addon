#!/bin/bash
SLUG="local_beep_boop_bb8"
TS="$(date +%Y%m%d_%H%M%S)"
REPORT="/config/hestia/diagnostics/reports/ha_bb8/ha_bb8_verification_${TS}.txt"

{
    echo "=== Restart add-on ==="
    ha addons restart "$SLUG" || true
    sleep 5

    echo "=== Add-on state/version ==="
    ha addons info "$SLUG" 2>/dev/null | jq -r '.state+" @ "+.version'

    echo "=== Options slice ==="
    ha addons options "$SLUG" 2>/dev/null | jq -c '{enable_echo,enable_health_checks,log_path,mqtt_host,mqtt_port}'

    echo "=== DIAG (expect entries NOW) ==="
    ha addons logs "$SLUG" --lines 400 \
    | grep -E 'run\.sh entry|RUNLOOP attempt|Started bb8_core\.(main|echo_responder) PID|Child exited|HEALTH_SUMMARY' || true

    echo "=== Heartbeat snapshots (ages must change) ==="
    echo "--- A ---"; ha addons logs "$SLUG" --lines 200 | grep HEALTH_SUMMARY | tail -n 3
    sleep 15
    echo "--- B ---"; ha addons logs "$SLUG" --lines 200 | grep HEALTH_SUMMARY | tail -n 3

    echo "=== MQTT smoke via HA Core (publish echo ping) ==="
    ha service call mqtt.publish -d '{"topic":"bb8/echo/cmd","payload":"{\"value\":\"ping-from-ha\"}"}' && sleep 2
    ha addons logs "$SLUG" --lines 200 | grep -E 'Connected to MQTT|Subscribed to bb8/echo/cmd|echo_responder' || true
} > "$REPORT"

cat "$REPORT"
echo -e "\nReport saved to $REPORT"