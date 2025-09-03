

#!/bin/bash
# === BB-8 BLE GATE + ECHO SMOKE + BLE STP5 ATTEST ===
set -euo pipefail

# --------- Run directory + helpers ---------
RUN_DIR="/config/reports/stp5_runs/$(date +%Y%m%d_%H%M%S)"
READY_JSON="$RUN_DIR/ble_ready_summary.json"
SMOKE_OUT="$RUN_DIR/echo_smoke.txt"
mkdir -p "$RUN_DIR"
trap 'echo "Artifacts: $RUN_DIR"' EXIT

# --------- Robust summary artifact ---------
emit_summary() {
  _status="$1"; shift
  _reason="$1"; shift
  _extra="$1"; shift
  local summary="{\"status\":\"$_status\",\"reason\":\"$_reason\",\"artifacts\":\"$RUN_DIR\",$_extra}"
  echo "$summary" >"$RUN_DIR/run_summary.json"
  echo "$summary"
}

# --------- Configurable Inputs ---------
HOST="${HOST:-192.168.0.129}"
PORT="${PORT:-1883}"
USER="${USER:-mqtt_bb8}"
PASS="${PASS:-mqtt_bb8}"
BASE="${BASE:-bb8}"

DURATION="${DURATION:-45}"
BURST_COUNT="${BURST_COUNT:-12}"
BURST_GAP_MS="${BURST_GAP_MS:-1500}"
REQUIRE_BLE="${REQUIRE_BLE:-true}"

READY_TIMEOUT="${READY_TIMEOUT:-10}"
READY_ATTEMPTS="${READY_ATTEMPTS:-5}"
READY_RETRY="${READY_RETRY:-1.5}"

SMOKE_TIMEOUT="${SMOKE_TIMEOUT:-8}"
SMOKE_EXPECT="${SMOKE_EXPECT:-3}"


# --------- Tooling Sanity ---------
for tool in jq mosquitto_pub mosquitto_sub; do
  if ! command -v "$tool" >/dev/null; then
    mkdir -p "$RUN_DIR"
    emit_summary "ERROR" "missing_tool" "\"tool\":\"$tool\""
    exit 2
  fi
done


# --------- 1) BLE readiness via MQTT shim ---------
NONCE="ble.$(date +%s%N)"
mosquitto_sub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" \
  -t "$BASE/ble_ready/summary" -C 1 -W "$READY_TIMEOUT" -v >"$READY_JSON" 2>/dev/null &
SP=$!; sleep 0.5
mosquitto_pub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" \
  -t "$BASE/ble_ready/cmd" \
  -m "{\"timeout_s\":$READY_TIMEOUT,\"retry_interval_s\":$READY_RETRY,\"max_attempts\":$READY_ATTEMPTS,\"nonce\":\"$NONCE\"}" >/dev/null 2>&1 || true
wait $SP || true

if ! [ -s "$READY_JSON" ]; then
    emit_summary "SKIP" "ble_not_ready" "\"details\":\"BLE readiness summary not received. Check MQTT and add-on logs.\""
    exit 1
fi

DET=$(jq -r 'try (fromjson | .detected) // "unknown"' <"$READY_JSON" 2>/dev/null || echo "unknown")
echo "BLE_READY_SUMMARY=$(cat "$READY_JSON")"

if [ "$DET" != "true" ]; then
    emit_summary "SKIP" "ble_not_detected" "\"details\":\"Wake BB-8 (tap/charger), place near host, rerun.\""
    exit 0
fi


# --------- 2) Echo SMOKE ---------
mosquitto_sub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" \
  -t "$BASE/echo/#" -C "$SMOKE_EXPECT" -W "$SMOKE_TIMEOUT" -v >"$SMOKE_OUT" 2>/dev/null &
SP=$!; sleep 0.5
mosquitto_pub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" \
  -t "$BASE/echo/cmd" -m '{"value":1}' >/dev/null 2>&1 || true
wait $SP || true

ACKS=$(grep -c "^$BASE/echo/ack " "$SMOKE_OUT" 2>/dev/null || echo 0)
STATES=$(grep -c "^$BASE/echo/state " "$SMOKE_OUT" 2>/dev/null || echo 0)
TEL=$(grep -c "^$BASE/telemetry/echo_roundtrip " "$SMOKE_OUT" 2>/dev/null || echo 0)
echo "ECHO_SMOKE ack=$ACKS state=$STATES telemetry=$TEL file=$SMOKE_OUT"

if [ "$ACKS" -lt 1 ] || [ "$STATES" -lt 1 ] || [ "$TEL" -lt 1 ]; then
    emit_summary "SKIP" "echo_pipeline_not_responding" "\"details\":\"See $SMOKE_OUT and Supervisor logs.\""
    exit 0
fi


# --------- 3) BLE-enforced STP5 attestation ---------
HOST=$HOST PORT=$PORT USER=$USER PASS=$PASS BASE=$BASE \
DURATION=$DURATION BURST_COUNT=$BURST_COUNT BURST_GAP_MS=$BURST_GAP_MS REQUIRE_BLE=$REQUIRE_BLE \
/config/domain/shell_commands/stp5_supervisor_ble_attest.sh || {
  emit_summary "ERROR" "attestation_failed" "\"details\":\"Attestation script failed.\""
  exit 1
}


# --------- Summarize ---------
QA="$RUN_DIR/QA_ble.json"; [ -f "$QA" ] || QA=/config/reports/qa_contract_telemetry_STP5.json
if ! [ -f "$QA" ]; then
  emit_summary "ERROR" "qa_artifact_missing" "\"details\":\"QA_ble.json not found.\""
  exit 1
fi
VERDICT=$(jq -r ".verdict" "$QA" 2>/dev/null || echo UNKNOWN)
WIN=$(jq -r ".metrics.window_duration_sec" "$QA" 2>/dev/null || echo 0)
ECHOES=$(jq -r ".metrics.echo_count_total" "$QA" 2>/dev/null || echo 0)
BLEC=$(jq -r ".metrics.ble_true_count" "$QA" 2>/dev/null || echo 0)
P95=$(jq -r ".metrics.echo_rtt_ms_p95" "$QA" 2>/dev/null || echo 0)

emit_summary "$VERDICT" "complete" "\"window_s\":$WIN,\"echoes\":$ECHOES,\"ble_true\":$BLEC,\"p95_ms\":$P95"