#!/usr/bin/env bash
# Robust add-on restart helper for HA deployment
# Usage: restart_helpers.sh [supervisor|ha|auto] [addon_slug]
set -euo pipefail

mode="${1:-auto}"
addon="${2:-local_beep_boop_bb8}"

# Function to test Supervisor context
test_supervisor() {
  [ -n "${SUPERVISOR_TOKEN:-}" ] || return 1
  curl -fsS -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
    http://supervisor/ping >/dev/null 2>&1
}

# Function to restart via Supervisor API
restart_supervisor() {
  echo "Using Supervisor API..."
  curl -fsS -X POST \
    -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
    -H "Content-Type: application/json" \
    "http://supervisor/addons/$addon/restart"
  echo "OK: Supervisor add-on restart"
}

# Function to restart via HA Core API
restart_ha_api() {
  [ -n "${HA_URL:-}" ] && [ -n "${HA_TOKEN:-}" ] || return 1
  echo "Using HA Core API..."
  curl -fsS -H "Authorization: Bearer $HA_TOKEN" \
    "$HA_URL/api/" >/dev/null
  curl -fsS -X POST \
    -H "Authorization: Bearer $HA_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"addon\":\"$addon\"}" \
    "$HA_URL/api/services/hassio/addon_restart"
  echo "OK: HA API add-on restart"
}

case "$mode" in
  supervisor)
    restart_supervisor
    ;;
  ha)
    restart_ha_api
    ;;
  auto)
    if test_supervisor; then
      restart_supervisor
    elif [ -n "${HA_URL:-}" ] && [ -n "${HA_TOKEN:-}" ]; then
      restart_ha_api
    else
      echo "ERR: No valid context (need SUPERVISOR_TOKEN or HA_URL+HA_TOKEN)"
      exit 2
    fi
    ;;
  *)
    echo "Usage: $0 [supervisor|ha|auto] [addon_slug]"
    exit 64
    ;;
esac