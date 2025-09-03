ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 home-assistant 'timeout 60 sh -s' <<'REMOTE'
set -euo pipefail
HOST="192.168.0.129"
PORT="1883"
USER="mqtt_bb8"
PASS="mqtt_bb8"
BASE="bb8"
ATT="/config/domain/shell_commands/stp5_supervisor_ble_attest.sh"
OUT_BASE="/config/reports/stp5_runs"
RUN_TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$OUT_BASE/$RUN_TS"
mkdir -p "$OUT_DIR"
need() { command -v "$1" >/dev/null || { echo "[ERR] missing tool: $1" >&2; exit 2; }; }
need mosquitto_pub; need mosquitto_sub; need jq
NONCE="stp5.$(date +%s%N)"
if ! timeout 8 sh -c '
  set -e
  mosquitto_sub -h "'$HOST'" -p "'$PORT'" -u "'$USER'" -P "'$PASS'" \
    -t "'$BASE'/selftest/'$NONCE'" -C 1 -W 3 -q 1 -v >/dev/null 2>&1 & SP=$!
  sleep 0.25
  mosquitto_pub -h "'$HOST'" -p "'$PORT'" -u "'$USER'" -P "'$PASS'" \
    -t "'$BASE'/selftest/'$NONCE'" -m ok -q 1
  wait $SP
'; then
  echo "SUMMARY: AUTH_FAIL (MQTT auth/ACL failed) ARTIFACTS=$OUT_DIR"
  exit 3
fi
export HOST PORT USER PASS BASE
if ! timeout 35 env DURATION=18 BURST_COUNT=8 BURST_GAP_MS=1500 REQUIRE_BLE=false "$ATT"; then
  echo "[WARN] attestation runner returned nonzero; continuing to collect artifacts"
fi
cp -f /config/reports/qa_contract_telemetry_STP5.json         "$OUT_DIR/QA_no_ble.json"                   2>/dev/null || true
cp -f /config/reports/stp5/echo_roundtrip.jsonl               "$OUT_DIR/echo_roundtrip_no_ble.jsonl"      2>/dev/null || true
cp -f /config/reports/stp5/metrics_summary.json               "$OUT_DIR/metrics_no_ble.json"              2>/dev/null || true
cp -f /config/reports/stp5/telemetry_snapshot.jsonl           "$OUT_DIR/telemetry_snapshot_no_ble.jsonl"  2>/dev/null || true
cp -f /config/reports/deploy_receipt.txt                      "$OUT_DIR/deploy_receipt.txt"               2>/dev/null || true
V="$(jq -r .verdict "$OUT_DIR/QA_no_ble.json" 2>/dev/null || echo NA)"
W="$(jq -r .metrics.window_duration_sec "$OUT_DIR/QA_no_ble.json" 2>/dev/null || echo NA)"
E="$(jq -r .metrics.echo_count_total    "$OUT_DIR/QA_no_ble.json" 2>/dev/null || echo NA)"
P95="$(jq -r .metrics.echo_rtt_ms_p95   "$OUT_DIR/QA_no_ble.json" 2>/dev/null || echo NA)"
echo "SUMMARY: NO_BLE verdict=$V window=${W}s echoes=${E} p95_ms=${P95} ARTIFACTS=$OUT_DIR"
REMOTE