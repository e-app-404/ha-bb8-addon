#!/usr/bin/env bash
set -euo pipefail

mode="${1:-auto}"
addon="${2:-local_beep_boop_bb8}"

if [[ "$mode" == "supervisor" || ( "$mode" == "auto" && -n "${SUPERVISOR_TOKEN:-}" ) ]]; then
  curl -fsS -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/ping >/dev/null
  curl -fsS -X POST -H "Authorization: Bearer $SUPERVISOR_TOKEN" "http://supervisor/addons/$addon/restart"
  echo "OK: supervisor add-on restart"
  exit 0
fi

if [[ -n "${HA_URL:-}" && -n "${HA_TOKEN:-}" ]]; then
  curl -fsS -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/" >/dev/null
  curl -fsS -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
       -d "{\"addon\":\"$addon\"}" "$HA_URL/api/services/hassio/addon_restart"
  echo "OK: HA API add-on restart"
  exit 0
fi

echo "ERR: No valid context (need SUPERVISOR_TOKEN or HA_URL+HA_TOKEN)"; exit 2