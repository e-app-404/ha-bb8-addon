#!/bin/bash
set -euo pipefail
# STP5 strict attestation evidence collection
WS="$(dirname "$0")/.."
REPORTS="$WS/reports/evidence_strict_attestation"
BROKER_HOST="${MQTT_HOST:-127.0.0.1}"
BROKER_PORT="${MQTT_PORT:-1883}"
mkdir -p "$REPORTS"
# Collect last 200 telemetry messages
mosquitto_sub -C 200 -t 'bb8/telemetry/#' -h "$BROKER_HOST" -p "$BROKER_PORT" > "$REPORTS/telemetry_snapshot.jsonl"
if [ ! -s "$REPORTS/telemetry_snapshot.jsonl" ]; then
    echo "No telemetry messages collected. Exiting."
    exit 1
fi
# Export paths for Python script
export TELEMETRY_PATH="$REPORTS/telemetry_snapshot.jsonl"
export METRICS_PATH="$REPORTS/metrics_summary.json"

# Summarize metrics (simple Python one-liner)
python3 - <<EOF
    lines = []
    with open(telemetry_path) as f:
        for l in f:
            if l.strip():
                try:
                    lines.append(json.loads(l))
                except Exception:
                    pass
summary = {}
if echo_lat:
    summary["echo_latency_p50"] = statistics.median(echo_lat)
    if len(echo_lat) >= 20:
        quantiles = statistics.quantiles(echo_lat, n=20)
        summary["echo_latency_p95"] = quantiles[18] if len(quantiles) > 18 else statistics.median_high(echo_lat)
    else:
        try:
            import numpy as np
            summary["echo_latency_p95"] = float(np.percentile(echo_lat, 95))
        except ImportError:
            summary["echo_latency_p95"] = statistics.median_high(echo_lat)
else:
    summary["echo_latency_p50"] = None
    summary["echo_latency_p95"] = None
if echo_lat:
    summary["echo_latency_p50"] = statistics.median(echo_lat)
    quantiles = statistics.quantiles(echo_lat, n=20) if len(echo_lat) >= 20 else []
    summary["echo_latency_p95"] = quantiles[18] if len(quantiles) > 18 else statistics.median_high(echo_lat)
else:
    summary["echo_latency_p50"] = None
    summary["echo_latency_p95"] = None
summary["connect_attempts"] = sum(1 for l in lines if l.get("try") is not None)
summary["discovery_dupes"] = sum(l.get("duplicates",0) for l in lines if "duplicates" in l)
files = os.environ["FILES"].split("\0")
EOF

export MANIFEST_PATH="$REPORTS/evidence_manifest.json"
export FILES="$REPORTS/telemetry_snapshot.jsonl,$REPORTS/metrics_summary.json"

# Update manifest
python3 - <<EOF
import sys, json, hashlib, os
manifest_path = os.environ["MANIFEST_PATH"]
files = os.environ["FILES"].split(",")
if os.path.exists(manifest_path):
    with open(manifest_path) as f:
        manifest = json.load(f)
else:
    manifest = {}

if "artifacts" not in manifest:
    manifest["artifacts"] = []
if "sha256" not in manifest:
    manifest["sha256"] = {}

def sha256(path):
    h = hashlib.sha256()
    with open(path,"rb") as f:
        while True:
            b = f.read(8192)
            if not b: break
            h.update(b)
    return h.hexdigest()

for f in files:
    fname = os.path.basename(f)
    manifest["sha256"][fname] = sha256(f)

json.dump(manifest, open(manifest_path,"w"), indent=2)
EOF
export FILES="$REPORTS/telemetry_snapshot.jsonl,$REPORTS/metrics_summary.json"
