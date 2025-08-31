#!/usr/bin/env bash
# /config/domain/shell_commands/stp5_attest.sh  (HA host)
set -euo pipefail
SINK_BASE="/config/reports"
OUT_DIR="$SINK_BASE/stp5"; SNAP="$OUT_DIR/telemetry_snapshot.jsonl"
METRICS="$OUT_DIR/metrics_summary.json"; QA="$SINK_BASE/qa_contract_telemetry_STP5.json"
RECEIPT="$SINK_BASE/deploy_receipt.txt"; GUARD="$SINK_BASE/stp5_guard_report.json"
mkdir -p "$OUT_DIR"

CFG="/addons/local/beep_boop_bb8/config.yaml"
BASE="${BASE:-bb8}"
HOST="$(grep -E '^ *mqtt_broker:' "$CFG" 2>/dev/null | awk '{print $2}' || echo 127.0.0.1)"
PORT="$(grep -E '^ *mqtt_port:'   "$CFG" 2>/dev/null | awk '{print $2}' || echo 1883)"
USER="$(grep -E '^ *mqtt_username:' "$CFG" 2>/dev/null | awk '{print $2}' || true)"
PASS="$(grep -E '^ *mqtt_password:' "$CFG" 2>/dev/null | awk '{print $2}' || true)"
AUTH=(); [ -n "${USER:-}" ] && AUTH+=(-u "$USER"); [ -n "${PASS:-}" ] && AUTH+=(-P "$PASS") || true

CID=$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}' || true)
test -n "$CID" || { echo '{"fatal":"addon container not running"}' | tee "$GUARD"; exit 2; }

# Stimulate echo once (best-effort)
mosquitto_pub -h "$HOST" -p "$PORT" "${AUTH[@]}" -t "${BASE}/echo/cmd" -m '{"value":1}' -q 0 -r false || true

# Capture ≥10s
mosquitto_sub -h "$HOST" -p "$PORT" "${AUTH[@]}" -v -t "${BASE}/#" -W 12 \
| awk '{topic=$1; $1=""; sub(/^ /,""); payload=$0; gsub(/"/,"\\\"",payload); print "{\"topic\":\""topic"\",\"payload\":\""payload"\"}"}' \
> "$SNAP"
test -s "$SNAP" || { echo '{"fatal":"empty telemetry snapshot"}' | tee "$GUARD"; exit 3; }

# Compute metrics + QA using container Python
docker exec "$CID" bash -lc "python - <<'PY'
import json, time, statistics, re, os
snap=os.environ['SNAP']; metrics=os.environ['METRICS']; qa=os.environ['QA']; base=os.environ.get('BASE','bb8')
echo_topics=(f'{base}/telemetry/echo_roundtrip', f'{base}/echo/state', f'{base}/echo/ack')
lines=[]
for l in open(snap): l=l.strip() or None; 
# quick parse tolerant of noise
  # noqa: E701
  # mypy: ignore-errors
  # parser:
  if l: 
    try: lines.append(json.loads(l))
    except: pass
now=int(time.time()); ts_first=now; ts_last=now; rtts=[]; echo_count=0
for e in lines:
  ts_last=now
  t=e.get('topic',''); p=e.get('payload','')
  if any(t.startswith(et) for et in echo_topics):
    echo_count+=1
    m=re.search(r'\"ms\"\\s*:\\s*([0-9]+)', p) or re.search(r'ms\"\\s*:\\s*([0-9]+)', p)
    if m:
      try: rtts.append(int(m.group(1)))
      except: pass
window=max(0, ts_last-ts_first)
p95=int(statistics.quantiles(rtts, n=20)[18]) if len(rtts)>=2 else (rtts[0] if rtts else 0)
summary={'window_start_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts_first)),
         'window_end_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts_last)),
         'window_duration_sec': window,
         'echo_count': echo_count,
         'echo_rtt_ms_mean': (sum(rtts)/len(rtts)) if rtts else 0.0,
         'echo_rtt_ms_p95': p95,
         'criteria': {'window_ge_10s': window>=10, 'min_echoes_ge_3': echo_count>=3, 'rtt_p95_le_250ms': (p95<=250) if rtts else False}}
summary['verdict']=all(summary['criteria'].values())
open(metrics,'w').write(json.dumps(summary, indent=2))
qa_doc={'contract_id':'QA-TELEMETRY-STP5-001','phase':'P5-TELEMETRY-STP5',
        'objective':'Echo/telemetry attestation >=10s',
        'acceptance_criteria':['Window duration >= 10s','At least 3 echo cycles','p95 echo RTT <= 250ms',
                               'Artifacts: telemetry_snapshot.jsonl, metrics_summary.json'],
        'artifacts':{'telemetry_snapshot':snap,'metrics_summary':metrics},
        'tokens_emitted':[],'verdict':'PASS' if summary['verdict'] else 'FAIL',
        'timestamp_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
if qa_doc['verdict']=='PASS':
  qa_doc['tokens_emitted']=['TELEMETRY_ATTEST_OK','ECHO_WINDOW_10S_OK','TELEMETRY_ARTIFACTS_EMITTED']
open(qa,'w').write(json.dumps(qa_doc, indent=2))
PY" SNAP="$SNAP" METRICS="$METRICS" QA="$QA" BASE="${BASE}"

# Emit guard sizes
(sizes() { stat -c%s "$1" 2>/dev/null || stat -f%z "$1"; }; \
  printf '{"snap":%s,"metrics":%s,"qa":%s}\n' "$(sizes "$SNAP")" "$(sizes "$METRICS")" "$(sizes "$QA")") > "$GUARD"

# Tokens on PASS
if grep -q '"verdict": "PASS"' "$QA"; then
  {
    echo "TOKEN: TELEMETRY_ATTEST_OK"
    echo "TOKEN: ECHO_WINDOW_10S_OK"
    echo "TOKEN: TELEMETRY_ARTIFACTS_EMITTED"
  } | tee -a "$RECEIPT"
  echo "STP5 PASS"
else
  echo "STP5 FAIL — inspect $OUT_DIR and $QA"
  exit 4
fi
