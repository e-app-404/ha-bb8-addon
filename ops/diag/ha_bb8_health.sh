#!/bin/sh
set -eu
SLUG="${1:-local_beep_boop_bb8}"
CID="$(docker ps --filter "name=addon_${SLUG}" --format '{{.ID}}' | head -n1)"
[ -n "$CID" ] || { echo "container not found for slug=$SLUG"; exit 1; }
LOGF=/data/reports/ha_bb8_addon.log
docker exec "$CID" sh -lc '
  echo "=== DIAG tail ==="
  tail -n 200 '"$LOGF"' | sed -n "/RUNLOOP attempt/I p; /Child exited/I p; /Started bb8_core\\./I p" | tail -n 40
  echo "=== heartbeats ==="
  for f in /tmp/bb8_heartbeat_main /tmp/bb8_heartbeat_echo; do
    t1=$(tail -1 "$f" 2>/dev/null || echo 0); sleep 6; t2=$(tail -1 "$f" 2>/dev/null || echo 0)
    awk -v n="$f" -v a="$t1" -v b="$t2" 'BEGIN{printf "%s drift=%.2fs\n", n, (b-a)}'
  done
'
