#!/usr/bin/env bash
set -euo pipefail
# Run these exact commands on the HA host (SSH add-on shell).

# 1) Prepare sink & detect container
mkdir -p /config/reports/stp5
CID=$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}' || true)
test -n "$CID" || { echo "FATAL: addon container not running"; exit 2; }

# 2) Capture ≥10s of live telemetry & echoes
# Adjust broker creds if your add-on uses auth; otherwise omit -u/-P.
MQTT_HOST=$(jq -r '.mqtt_broker' /addons/local/beep_boop_bb8/config.yaml 2>/dev/null || echo 127.0.0.1)
MQTT_PORT=$(jq -r '.mqtt_port // 1883' /addons/local/beep_boop_bb8/config.yaml 2>/dev/null || echo 1883)
MQTT_USER=$(jq -r '.mqtt_username // empty' /addons/local/beep_boop_bb8/config.yaml 2>/dev/null || true)
MQTT_PASS=$(jq -r '.mqtt_password // empty' /addons/local/beep_boop_bb8/config.yaml 2>/dev/null || true)
BASE=$(jq -r '.mqtt_topic_prefix' /addons/local/beep_boop_bb8/config.yaml 2>/dev/null || echo bb8)
AUTH_ARGS=()
[ -n "$MQTT_USER" ] && AUTH_ARGS+=(-u "$MQTT_USER")
[ -n "$MQTT_PASS" ] && AUTH_ARGS+=(-P "$MQTT_PASS")

# Best-effort nudge: send a single echo command so device-originated echo/state fires back
mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" "${AUTH_ARGS[@]}" \
  -t "${BASE}/echo/cmd" -m '{"value":1}' -q 0 -r false || true

# Capture for ~12s and convert "topic payload" -> JSON lines
mosquitto_sub -h "$MQTT_HOST" -p "$MQTT_PORT" "${AUTH_ARGS[@]}" -v -t "${BASE}/#" -W 12 \
| awk '{topic=$1; $1=""; sub(/^ /,""); payload=$0; gsub(/"/,"\\\"",payload); print "{\"topic\":\""topic"\",\"payload\":\""payload"\"}"}' \
> /config/reports/stp5/telemetry_snapshot.jsonl

test -s /config/reports/stp5/telemetry_snapshot.jsonl || { echo "FATAL: empty telemetry snapshot"; exit 3; }
echo "TOKEN: TELEMETRY_SNAPSHOT_OK"

# 3) Compute metrics & emit QA contract (in-container Python venv)
docker exec "$CID" bash -lc '
set -euo pipefail
PY=/opt/venv/bin/python
SNAP=/config/reports/stp5/telemetry_snapshot.jsonl
METRICS=/config/reports/stp5/metrics_summary.json
QA=/config/reports/qa_contract_telemetry_STP5.json
$PY - <<PYCODE
import json, time, statistics, re, sys
snap_path = SNAP
base = "bb8"
echo_topics = (f"{base}/telemetry/echo_roundtrip", f"{base}/echo/state", f"{base}/echo/ack")
ts_first = None; ts_last = None; rtts = []; echo_count = 0
def parse_line(s):
    try: return json.loads(s)
    except: return None
with open(snap_path, "r") as f:
    lines = [parse_line(l) for l in f if l.strip()]
now = int(time.time())
for e in [x for x in lines if x]:
    t = e.get("topic",""); p = e.get("payload","")
    if ts_first is None: ts_first = now
    ts_last = now
    if any(t.startswith(et) for et in echo_topics):
        echo_count += 1
        m = re.search(r'"ms\"\\s*:\\s*([0-9]+)', p)  # crude extraction if present
        if m: rtts.append(int(m.group(1)))
window = (ts_last - ts_first) if ts_first and ts_last else 0
p95 = int(statistics.quantiles(rtts, n=20)[18]) if len(rtts) >= 2 else (rtts[0] if rtts else 0)
summary = {
  "window_start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts_first or now)),
  "window_end_utc":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts_last or now)),
  "window_duration_sec": window,
  "echo_count": echo_count,
  "echo_rtt_ms_mean": (sum(rtts)/len(rtts)) if rtts else 0.0,
  "echo_rtt_ms_p95": p95,
  "criteria": {
    "window_ge_10s": window >= 10,
    "min_echoes_ge_3": echo_count >= 3,
    "rtt_p95_le_250ms": p95 <= 250 if rtts else False
  },
  "verdict": (window >= 10 and echo_count >= 3 and (p95 <= 250 if rtts else False))
}
open(METRICS, "w").write(json.dumps(summary, indent=2))
qa = {
  "contract_id": "QA-TELEMETRY-STP5-001",
  "phase": "P5-TELEMETRY-STP5",
  "objective": "Echo/telemetry attestation with extended window (>=10s)",
  "acceptance_criteria": [
    "Window duration >= 10s",
    "At least 3 echo ping/pong cycles observed",
    "p95 echo RTT <= 250ms",
    "Artifacts emitted: telemetry_snapshot.jsonl, metrics_summary.json"
  ],
  "artifacts": {
    "telemetry_snapshot": SNAP,
    "metrics_summary": METRICS
  },
  "tokens_emitted": [],
  "verdict": "PASS" if summary["verdict"] else "FAIL",
  "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
}
if qa["verdict"] == "PASS":
    qa["tokens_emitted"] = ["TELEMETRY_ATTEST_OK","ECHO_WINDOW_10S_OK","TELEMETRY_ARTIFACTS_EMITTED"]
open(QA, "w").write(json.dumps(qa, indent=2))
print("WROTE:", METRICS, QA)
PYCODE
'

# 4) Tokenize (only if PASS)
if jq -e '.verdict=="PASS"' /config/reports/qa_contract_telemetry_STP5.json >/dev/null; then
  echo "TOKEN: TELEMETRY_ATTEST_OK" | tee -a /config/reports/deploy_receipt.txt
  echo "TOKEN: ECHO_WINDOW_10S_OK" | tee -a /config/reports/deploy_receipt.txt
  echo "TOKEN: TELEMETRY_ARTIFACTS_EMITTED" | tee -a /config/reports/deploy_receipt.txt
  echo "STP5 PASS"
else
  echo "STP5 FAIL — inspect /config/reports/stp5/*"
fi