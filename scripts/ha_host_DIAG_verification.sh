SLEEP_DURATION=${SLEEP_DURATION:-2}

[ -f /tmp/bb8_restart_disabled ] && { echo "present"; ls -l /tmp/bb8_restart_disabled; } || echo "absent"

# Example usage after killing processes:
# sleep "$SLEEP_DURATION"
# Override by exporting ADDON_SLUG before running.
# Example: export ADDON_SLUG=my_custom_addon
addon_slug="${ADDON_SLUG:-local_beep_boop_bb8}"
cid="$(docker ps --filter "name=addon_${addon_slug}" --format '{{.ID}}' | head -n1)"
echo "cid=${cid:-<none>}  slug=$addon_slug"
[ -n "$cid" ] || { echo "ERROR: add-on container not found"; exit 1; }

docker exec "$cid" sh -lc '
set -e
OPT=/data/options.json
for cmd in jq awk sed tail grep tr dirname ls cat; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: Required command '\''$cmd'\'' not found"; exit 2; }
done
LOGF="/data/reports/ha_bb8_addon.log"
if [ -f "$OPT" ]; then
  tmp_logf="$(jq -r ".log_path // empty" "$OPT" 2>/dev/null)"
  [ -n "$tmp_logf" ] && LOGF="$tmp_logf"
fi

echo "=== VERSION ==="
cat /etc/BB8_ADDON_VERSION 2>/dev/null || echo "(no /etc/BB8_ADDON_VERSION)"
[ -f /usr/src/app/VERSION ] && echo "APP_VERSION=$(cat /usr/src/app/VERSION)" || true

echo "=== services wiring ==="
if [ -f /etc/services.d/ble_bridge/run ]; then
  sed -n "1,6p" /etc/services.d/ble_bridge/run
else
  echo "(missing /etc/services.d/ble_bridge/run)"
fi
[ -f /etc/services.d/echo_responder/down ] && echo "echo_responder/down: PRESENT" || echo "echo_responder/down: ABSENT"

echo "=== options.json slice ==="
if [ -f "$OPT" ]; then
  jq -c "{enable_echo,enable_health_checks,log_path,mqtt_host,mqtt_port}" "$OPT" 2>/dev/null
else
  echo "(no options.json)"
fi

echo "=== log path sanity ==="
echo "LOGF=$LOGF"
P="$(dirname "$LOGF")"
[ -d "$P" ] && echo "parent dir: $P (exists)" || echo "parent dir: $P (missing)"
[ -w "$P" ] && echo "parent writable: OK" || echo "parent writable: NO"
[ -f "$LOGF" ] && echo "file exists: OK" || echo "file exists: MISSING"

echo "=== DIAG (key lines) ==="
if [ -f "$LOGF" ]; then
  tail -n 1000 "$LOGF" | sed -n "/run.sh entry/I p; /RUNLOOP attempt/I p; /Started bb8_core\.main PID=/I p; /Started bb8_core\.echo_responder PID=/I p; /Child exited/I p"
else
  echo "(log file missing at $LOGF)"
fi

echo "=== processes (pre-kill) ==="
for p in /proc/[0-9]*; do
  cmd=$(tr -d "\0" < "$p/cmdline" 2>/dev/null) || true
  echo "$cmd" | grep -Eq "bb8_core\.main|bb8_core\.echo_responder" && echo "${p##*/}: $cmd"
done

echo "=== heartbeats (drift) ==="
HEARTBEAT_SLEEP="${HEARTBEAT_SLEEP:-6}"
for f in /tmp/bb8_heartbeat_main /tmp/bb8_heartbeat_echo; do
  if [ -f "$f" ]; then
    t1=$(head -n 1 "$f" 2>/dev/null)
    t2=$(tail -n 1 "$f" 2>/dev/null)
    awk -v n="$f" -v a="$t1" -v b="$t2" '\''BEGIN { printf "%s: before=%s after=%s delta=%.3f\n", n, a, b, (b-a) }'\''
  else
    echo "$f: (absent)"
  fi
done

K=0
for p in /proc/[0-9]*; do
  if ! cmd=$(tr -d "\0" < "$p/cmdline" 2>/dev/null); then
    cmd=""
  fi
  echo "$cmd" | grep -q "bb8_core\.echo_responder" && { kill -TERM "${p##*/}" 2>/dev/null || true; K=$((K+1)); }
done
echo "killed=$K"; sleep 6

echo "=== DIAG (after kill) ==="
[ -f "$LOGF" ] && tail -n 1000 "$LOGF" | sed -n "/Child exited/I p; /RUNLOOP attempt/I p; /Started bb8_core\.main PID=/I p; /Started bb8_core\.echo_responder PID=/I p"

echo "=== processes (post-kill) ==="
for p in /proc/[0-9]*; do
  cmd=$(tr -d "\0" < "$p/cmdline" 2>/dev/null) || true
  echo "$cmd" | grep -Eq "bb8_core\.main|bb8_core\.echo_responder" && echo "${p##*/}: $cmd"
done

echo "=== supervision check ==="
[ -f /etc/services.d/echo_responder/down ] && echo "s6 echo_responder: DOWN" || echo "s6 echo_responder: ACTIVE"
if [ -f "$LOGF" ]; then
  spawned_by_runsh=$(grep -c "Started bb8_core\.echo_responder PID=" "$LOGF" 2>/dev/null)
else
  spawned_by_runsh=0
fi
echo "spawned_by_runsh=$spawned_by_runsh"

echo "=== restart cap flag ==="
[ -f /tmp/bb8_restart_disabled ] && { echo "present"; ls -l /tmp/bb8_restart_disabled; } || echo "absent"
'
