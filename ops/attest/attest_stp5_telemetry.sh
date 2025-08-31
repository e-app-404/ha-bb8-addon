#!/usr/bin/env bash
set -euo pipefail

# Inputs (env or defaults)
HOST="${MQTT_HOST:-${1:-localhost}}"
PORT="${MQTT_PORT:-${2:-1883}}"
BASE="${MQTT_BASE:-${3:-bb8}}"
USER="${MQTT_USERNAME:-${MQTT_USER:-}}"
PASS="${MQTT_PASSWORD:-${MQTT_PASS:-}}"
WINDOW="${WINDOW:-12}"         # seconds to capture
COUNT="${COUNT:-6}"            # number of pings
OUTDIR="${OUTDIR:-/config/reports/stp5}"
mkdir -p "$OUTDIR"

# Auth array (only if values exist)
AUTH=()
[ -n "${USER:-}" ] && AUTH+=(-u "$USER")
[ -n "${PASS:-}" ] && AUTH+=(-P "$PASS")

# 1) Warm-up subscribe (background)
SNAP="$OUTDIR/telemetry_snapshot.jsonl"
: > "$SNAP"
mosquitto_sub -h "$HOST" -p "$PORT" "${AUTH[@]}" -t "${BASE}/telemetry/#" -v \
  | awk '{topic=$1; $1=""; sub(/^ /,""); print "{\"topic\":\""topic"\",\"payload\":"$0"}"}' \
  > "$SNAP" &
SUB_PID=$!

# 2) Publish echo commands (QoS 0; no bogus flags)
for i in $(seq 1 "$COUNT"); do
  mosquitto_pub -h "$HOST" -p "$PORT" "${AUTH[@]}" -t "${BASE}/echo/cmd" -m "{\"i\":$i}" -q 0 || true
  sleep 1
done

# 3) Wait window, then stop subscriber
sleep "$WINDOW"
kill "$SUB_PID" >/dev/null 2>&1 || true

# 4) Metrics (simple, robust)
MET="$OUTDIR/metrics_summary.json"
python3 - "$SNAP" "$WINDOW" > "$MET" <<'PY'
import json, sys, time, statistics as st
snap=sys.argv[1]; win=float(sys.argv[2])
rows=[]
try:
  with open(snap,'r') as f:
    for ln in f:
      try: rows.append(json.loads(ln))
      except: pass
except FileNotFoundError: pass

# Count echoes from telemetry topic(s)
echo_rows=[r for r in rows if r.get('topic','').endswith('/telemetry/echo_roundtrip')]
rtts=[]
for r in echo_rows:
  try:
    p=json.loads(r.get('payload','{}')) if isinstance(r.get('payload'),str) else r.get('payload',{})
    if 'rtt_ms' in p: rtts.append(int(p['rtt_ms']))
  except: pass

now=int(time.time())
out={
  "window_duration_sec": win,
  "echo_count": len(echo_rows),
  "echo_rtt_ms_mean": (sum(rtts)/len(rtts)) if rtts else None,
  "echo_rtt_ms_p95": (int(st.quantiles(rtts, n=20)[18]) if len(rtts)>=2 else (rtts[0] if rtts else None)),
  "criteria": {
    "window_ge_10s": win>=10,
    "min_echoes_ge_3": len(echo_rows)>=3,
    "rtt_p95_le_250ms": (rtts and ( (int(st.quantiles(rtts, n=20)[18]) if len(rtts)>=2 else rtts[0]) <= 250))
  }
}
out["verdict"]= bool(out["criteria"]["window_ge_10s"] and out["criteria"]["min_echoes_ge_3"] and out["criteria"]["rtt_p95_le_250ms"])
print(json.dumps(out, indent=2))
PY

# 5) Verdict + receipt
if jq -e '.verdict==true' "$MET" >/dev/null 2>&1; then
  echo "TOKEN: TELEMETRY_ATTEST_OK"
else
  echo "FAIL: TELEMETRY_ATTEST"
  echo "SNAP: $SNAP"
  echo "METRICS: $MET"
fi
