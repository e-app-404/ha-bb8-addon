#!/bin/sh
set -eu
SLUG="${1:-local_beep_boop_bb8}"
CID="$(docker ps --filter "name=addon_${SLUG}" --format '{{.ID}}' | head -n1)"
[ -n "$CID" ] || { echo "container not found for slug=$SLUG"; exit 1; }
LOGF=/data/reports/ha_bb8_addon.log
docker exec "$CID" sh -lc '
  K=0
  for p in /proc/[0-9]*; do
    cmd=$(tr -d "\0" < "$p/cmdline" 2>/dev/null || true)
    echo "$cmd" | grep -q "bb8_core\.echo_responder" && { kill -TERM "${p##*/}" 2>/dev/null || true; K=$((K+1)); }
  done
  echo "killed=$K"; sleep 6
  tail -n 400 '"$LOGF"' | sed -n "/Child exited/I p; /RUNLOOP attempt/I p; /Started bb8_core\.echo_responder PID=/I p" | tail -n 40
'
