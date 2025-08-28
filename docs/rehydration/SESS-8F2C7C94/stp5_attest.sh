#!/usr/bin/env bash
set -euo pipefail

# --- Canonical paths
SINK_BASE="/config/reports"
OUT_DIR="$SINK_BASE/stp5"
SNAP="$OUT_DIR/telemetry_snapshot.jsonl"
METRICS="$OUT_DIR/metrics_summary.json"
QA="$SINK_BASE/qa_contract_telemetry_STP5.json"
RECEIPT="$SINK_BASE/deploy_receipt.txt"

mkdir -p "$OUT_DIR"

# --- Resolve runtime config (no yq; jq acceptable; fallbacks included)
CFG="/addons/local/beep_boop_bb8/config.yaml"
BASE="${BASE:-bb8}"
HOST="$(grep -E '^ *mqtt_broker:' "$CFG" 2>/dev/null | awk '{print $2}' || echo 127.0.0.1)"
PORT="$(grep -E '^ *mqtt_port:'   "$CFG" 2>/dev/null | awk '{print $2}' || echo 1883)"
USER="$(grep -E '^ *mqtt_username:' "$CFG" 2>/dev/null | awk '{print $2}' || true)"
PASS="$(grep -E '^ *mqtt_password:' "$CFG" 2>/dev/null | awk '{print $2}' || true)"

AUTH=()
[ -n "${USER:-}" ] && AUTH+=(-u "$USER")
[ -n "${PASS:-}" ] && AUTH+=(-P "$PASS")

# --- Locate container & venv python
CID=$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}' || true)
[ -n "$CID" ] || { echo "FATAL: addon container not running"; exit 2; }

# --- Nudge one echo to stimulate device-originated traffic
mosquitto_pub -h "$HOST" -p "$PORT" "${AUTH[@]}" -t "${BASE}/echo/cmd" -m '{"value":1}' -q 0 -r false || true

# --- Capture ≥10s telemetry
mosquitto_sub -h "$HOST" -p "$PORT" "${AUTH[@]}" -v -t "${BASE}/#" -W 12 \
| awk '{topic=$1; $1=""; sub(/^ /,""); payload=$0; gsub(/"/,"\\\"",payload); print "{\"topic\":\""topic"\",\"payload\":\""payload"\"}"}' \
> "$SNAP"

test -s "$SNAP" || { echo "FATAL: empty telemetry snapshot"; exit 3; }
echo "TOKEN: TELEMETRY_SNAPSHOT_OK"

# --- Compute metrics & QA
docker exec "$CID" bash -lc "python - <<'PY'
import json, time, statistics, re
snap = '$SNAP'; metrics = '$METRICS'; qa = '$QA'; base = 'bb8'
echo_topics = (f'{base}/telemetry/echo_roundtrip', f'{base}/echo/state', f'{base}/echo/ack')
lines = []
with open(snap, 'r') as f:
  for l in f:
    l=l.strip()
    if l:
      try: lines.append(json.loads(l))
      except: pass

now = int(time.time())
ts_first = ts_last = now
rtts=[]; echo_count=0
for e in lines:
  ts_last = now
  t = e.get('topic',''); p = e.get('payload','')
  if any(t.startswith(et) for et in echo_topics):
    echo_count += 1
    m = re.search(r'ms\"\\s*:\\s*([0-9]+)', p)
    if not m:
      m = re.search(r'\"ms\"\\s*:\\s*([0-9]+)', p)
    if m:
      try: rtts.append(int(m.group(1)))
      except: pass

window = ts_last - ts_first
p95 = int(statistics.quantiles(rtts, n=20)[18]) if len(rtts) >= 2 else (rtts[0] if rtts else 0)
summary = {
  'window_start_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts_first)),
  'window_end_utc':   time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts_last)),
  'window_duration_sec': window,
  'echo_count': echo_count,
  'echo_rtt_ms_mean': (sum(rtts)/len(rtts)) if rtts else 0.0,
  'echo_rtt_ms_p95': p95,
  'criteria': {
    'window_ge_10s': window >= 10,
    'min_echoes_ge_3': echo_count >= 3,
    'rtt_p95_le_250ms': (p95 <= 250) if rtts else False
  }
}
summary['verdict'] = all(summary['criteria'].values())
open(metrics, 'w').write(json.dumps(summary, indent=2))

qa_doc = {
  'contract_id': 'QA-TELEMETRY-STP5-001',
  'phase': 'P5-TELEMETRY-STP5',
  'objective': 'Echo/telemetry attestation >=10s',
  'acceptance_criteria': [
    'Window duration >= 10s',
    'At least 3 echo ping/pong cycles observed',
    'p95 echo RTT <= 250ms',
    'Artifacts: telemetry_snapshot.jsonl, metrics_summary.json'
  ],
  'artifacts': {
    'telemetry_snapshot': snap,
    'metrics_summary': metrics
  },
  'tokens_emitted': [],
  'verdict': 'PASS' if summary['verdict'] else 'FAIL',
  'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
}
if qa_doc['verdict'] == 'PASS':
  qa_doc['tokens_emitted'] = ['TELEMETRY_ATTEST_OK','ECHO_WINDOW_10S_OK','TELEMETRY_ARTIFACTS_EMITTED']
open(qa, 'w').write(json.dumps(qa_doc, indent=2))
print('WROTE:', metrics, qa)
PY"

# --- Tokenize on PASS
if jq -e '.verdict=="PASS"' "$QA" >/dev/null 2>&1; then
  {
    echo "TOKEN: TELEMETRY_ATTEST_OK"
    echo "TOKEN: ECHO_WINDOW_10S_OK"
    echo "TOKEN: TELEMETRY_ARTIFACTS_EMITTED"
  } | tee -a "$RECEIPT"
  echo "STP5 PASS"
else
  echo "STP5 FAIL — inspect $OUT_DIR and $QA"
fi
