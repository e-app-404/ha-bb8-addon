#!/usr/bin/env bash
set -euo pipefail

OUT="${1:?usage: evidence_preflight.sh <out_dir>}"
mkdir -p "$OUT"

: "${MQTT_BASE:=bb8}"
: "${REQUIRE_DEVICE_ECHO:=1}"
: "${ENABLE_BRIDGE_TELEMETRY:=1}"

TS="$(date -u +%Y%m%d_%H%M%SZ)"
RUNLOG="$OUT/run.log"
TRACE_JSONL="$OUT/ha_mqtt_trace_snapshot.jsonl"
MANIFEST="$OUT/evidence_manifest.json"

echo "[evidence] ts=$TS base=$MQTT_BASE require_echo=$REQUIRE_DEVICE_ECHO" | tee -a "$RUNLOG"
echo "[evidence] broker=${MQTT_HOST:-}:${MQTT_PORT:-} user=${MQTT_USERNAME:-}" | tee -a "$RUNLOG"


echo "[evidence] step=probe" | tee -a "$RUNLOG"
python /Users/evertappels/Projects/HA-BB8/ops/evidence/mqtt_probe.py --timeout 8 --require-echo "$REQUIRE_DEVICE_ECHO" 2>&1 | tee -a "$RUNLOG" || true

echo "[evidence] step=capture" | tee -a "$RUNLOG"
python /Users/evertappels/Projects/HA-BB8/ops/evidence/capture_trace.py --duration 12 --out "$TRACE_JSONL" 2>&1 | tee -a "$RUNLOG" || true

ROUNDTRIP="FAIL"
grep -q "probe: roundtrip=PASS" "$RUNLOG" && ROUNDTRIP="PASS"

SCHEMA="UNKNOWN"
grep -q "schema=PASS" "$RUNLOG" && SCHEMA="PASS"
grep -q "schema=FAIL" "$RUNLOG" && SCHEMA="FAIL"

echo "[evidence] step=collector" | tee -a "$RUNLOG"
if python /Users/evertappels/Projects/HA-BB8/ops/evidence/collect_stp4.py 2>&1 | tee -a "$RUNLOG"; then
  :
else
  echo "[evidence] collector exited nonzero (continuing; manifest will record verdicts)" | tee -a "$RUNLOG"
fi

echo "[evidence] step=manifest" | tee -a "$RUNLOG"
python - <<'PY' "$MANIFEST" "$TRACE_JSONL" "$RUNLOG" "$ROUNDTRIP" "$SCHEMA"
import json, sys, time
mp, trace, runlog, rt, sc = sys.argv[1:]
m = {
  "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "roundtrip": rt,
  "schema": sc,
  "files": {"trace": trace if trace else None, "manifest_self": mp, "run_log": runlog}
}
with open(mp, "w") as f: json.dump(m, f, indent=2)
print(f"[evidence] manifest written: {mp}")
PY

echo "[evidence] complete: roundtrip=$ROUNDTRIP schema=$SCHEMA" | tee -a "$RUNLOG"
