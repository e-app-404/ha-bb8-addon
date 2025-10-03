#!/usr/bin/env bash
set -euo pipefail

# ---- Config (override via env) ----
SINK="${SINK:-reports}"
OUT_DIR="$SINK/stp5"
SNAP="$OUT_DIR/telemetry_snapshot.jsonl"
METRICS="$OUT_DIR/metrics_summary.json"
QA="$SINK/qa_contract_telemetry_STP5.json"
RECEIPT="$SINK/deploy_receipt.txt"
GUARD="$SINK/stp5_guard_report.json"

HOST="${HOST:-192.168.0.129}"
PORT="${PORT:-1883}"
USER="${USER:-mqtt_bb8}"
PASS="${PASS:-mqtt_bb8}"
BASE="${BASE:-bb8}"
DURATION="${TELEMETRY_DURATION:-15}"   # capture window seconds (≥10)
REQUIRE_BLE="${REQUIRE_BLE:-false}"    # set true to require at least one ble_ok=true

mkdir -p "$OUT_DIR"

# ---- Nudge echo 3x within the window ----
( sleep 0.20
  for i in 1 2 3; do
    mosquitto_pub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" \
      -t "$BASE/echo/cmd" -m '{"value":1}' || true
    sleep 0.20
  done
) &

# ---- Capture ≥DURATIONs from $BASE/# as JSONL ----
START=$(date -u +%s)
mosquitto_sub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" -v -t "$BASE/#" -W "$DURATION" \
| while IFS= read -r line; do
    topic="${line%% *}"
    payload="${line#* }"
    jq -n --arg topic "$topic" --arg payload "$payload" '{topic: $topic, payload: $payload}'
  done > "$SNAP" || true
END=$(date -u +%s)

if [ ! -s "$SNAP" ]; then
  echo '{"fatal":"empty telemetry snapshot"}' | tee "$GUARD"
  exit 3
fi

# ---- Extract RTT samples (accept .ms or .rtt_ms) and BLE flags ----
RTT_FILE="$OUT_DIR/rtt_values.txt"
TS_FILE="$OUT_DIR/ts_values.txt"
: > "$RTT_FILE"; : > "$TS_FILE"

# Decode payload when it is JSON; ignore if not JSON
jq -r --arg base "$BASE" '
  def mj: (try (.payload|fromjson) catch null);
  select(.topic|startswith($base + "/")) as $l
  | (mj) as $p
  | if $p!=null then
      # RTT candidates from echo telemetry or state
      (if (.topic|startswith($base+"/telemetry/echo_roundtrip") or
           .topic|startswith($base+"/echo/state"))
       then ($p.ms // $p.rtt_ms // empty) else empty end) as $ms
      | ($p.ts // empty) as $ts
      | (if $ms|type=="number" then $ms else empty end),
        (if $ts|type=="number" then "TS:\($ts)" else empty end)
    else empty end
' "$SNAP" | while IFS= read -r line; do
  case "$line" in
    TS:*) echo "${line#TS:}" >> "$TS_FILE" ;;
    *)    [ -n "$line" ] && printf '%s\n' "$line" >> "$RTT_FILE" ;;
  esac
done

# Echo event count (acks/states/telemetry)
ECHO_COUNT=$(jq -r --arg base "$BASE" '
  select(.topic|startswith($base+"/echo/") or
         .topic|startswith($base+"/telemetry/echo_roundtrip")) | 1' "$SNAP" | wc -l | tr -d ' ')

# Any BLE ok?
BLE_OK_ANY=false
jq -r --arg base "$BASE" '
  def mj: (try (.payload|fromjson) catch null);
  select(.topic|startswith($base+"/telemetry/echo_roundtrip"))
  | (mj) as $p | if $p!=null then $p.ble_ok // empty else empty end
' "$SNAP" | grep -qi '^true$' && BLE_OK_ANY=true

# Window duration: prefer payload ts min/max; else wall clock
if [ -s "$TS_FILE" ]; then
  TS_MIN=$(sort -n "$TS_FILE" | head -1)
  TS_MAX=$(sort -n "$TS_FILE" | tail -1)
  WINDOW=$(( TS_MAX - TS_MIN ))
else
  WINDOW=$(( END - START ))
fi
[ "$WINDOW" -lt 0 ] && WINDOW=0

# RTT stats
P95=0; MEAN=0; HAVE_RTT=false
if [ -s "$RTT_FILE" ]; then
  SUM=0
  for v in "${SORTED[@]}"; do
    if [[ "$v" =~ ^-?[0-9]+$ ]]; then
      SUM=$((SUM + v))
    fi
  done
  N=$(wc -l < "$RTT_FILE" | tr -d ' ')
  readarray -t SORTED < <(sort -n "$RTT_FILE")
  # mean
  SUM=0; for v in "${SORTED[@]}"; do SUM=$((SUM + v)); done
  MEAN=$(awk -v s="$SUM" -v n="$N" 'BEGIN{ if(n>0){printf("%.2f", s/n)} else {print "0.00"} }')
  # p95 = ceil(0.95*N) using rank = ceil(19*N/20)
  IDX=$(( (19 * N + 19) / 20 ))
  [ "$IDX" -lt 1 ] && IDX=1
  P95="${SORTED[$((IDX-1))]}"
C_RTT=$([ "$HAVE_RTT" = true ] && [ "${P95:-999999}" -le 250 ] && echo true || echo false)

# Criteria
C_WIN=$([ "$WINDOW" -ge 10 ] && echo true || echo false)
C_ECH=$([ "$ECHO_COUNT" -ge 3 ] && echo true || echo false)
C_RTT=$({ $HAVE_RTT && [ "${P95:-999999}" -le 250 ]; } && echo true || echo false)
if [ "$REQUIRE_BLE" = "true" ]; then
  if [ "$BLE_OK_ANY" = "true" ]; then
    C_BLE=true
  else
    C_BLE=false
  fi
else
  C_BLE=true
fi

VERDICT=false
if $C_WIN && $C_ECH && $C_RTT && $C_BLE; then VERDICT=true; fi

# Write metrics
jq -n \
  --arg start "$(date -u -d "@$START" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -r "$START" +%Y-%m-%dT%H:%M:%SZ)" \
  --arg end   "$(date -u -d "@$END"   +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -r "$END"   +%Y-%m-%dT%H:%M:%SZ)" \
  --argjson window "$WINDOW" \
  --argjson echo_count "$ECHO_COUNT" \
  --arg mean "$MEAN" \
  --argjson p95 "${P95:-0}" \
  --argjson have_rtt "$([ "$HAVE_RTT" = true ] && echo true || echo false)" \
  --argjson ble_ok_any "$([ "$BLE_OK_ANY" = true ] && echo true || echo false)" \
  --argjson window_ge_10s "$C_WIN" \
  --argjson min_echoes_ge_3 "$C_ECH" \
  --argjson rtt_p95_le_250ms "$C_RTT" \
  --argjson ble_requirement_met "$C_BLE" \
  --arg verdict "$([ "$VERDICT" = true ] && echo PASS || echo FAIL)" '
{
  window_start_utc: $start,
  window_end_utc: $end,
  window_duration_sec: $window,
  echo_count: $echo_count,
  echo_rtt_ms_mean: ($mean|tonumber? // 0),
  echo_rtt_ms_p95: $p95,
  have_rtt_samples: $have_rtt,
  ble_ok_any: $ble_ok_any,
  criteria: {
    window_ge_10s: $window_ge_10s,
    min_echoes_ge_3: $min_echoes_ge_3,
    rtt_p95_le_250ms: $rtt_p95_le_250ms,
    ble_requirement_met: $ble_requirement_met
  },
  verdict: $verdict
}' > "$METRICS"

# Write QA contract
jq -n \
  --arg verdict "$([ "$VERDICT" = true ] && echo PASS || echo FAIL)" \
  --arg base "$BASE" \
  --arg snap "$SNAP" --arg metrics "$METRICS" \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '
{
  contract_id: "QA-TELEMETRY-STP5-001",
  phase: "P5-TELEMETRY-STP5",
  objective: "Echo/telemetry attestation >=10s",
  acceptance_criteria: [
    "Window duration >= 10s",
    "At least 3 echo ping/pong cycles observed",
    "p95 echo RTT <= 250ms",
    "Artifacts: telemetry_snapshot.jsonl, metrics_summary.json"
  ],
  artifacts: { telemetry_snapshot: $snap, metrics_summary: $metrics },
  tokens_emitted: (if $verdict=="PASS" then ["TELEMETRY_ATTEST_OK","ECHO_WINDOW_10S_OK","TELEMETRY_ARTIFACTS_EMITTED"] else [] end),
  mqtt_base: $base,
  verdict: $verdict,
  timestamp_utc: $ts
}' > "$QA"

# Guard report with file sizes
jq -n --arg snap "$SNAP" --arg metrics "$METRICS" --arg qa "$QA" \
  --argjson snap_size "$(stat -c%s "$SNAP" 2>/dev/null || stat -f%z "$SNAP")" \
  --argjson metrics_size "$(stat -c%s "$METRICS" 2>/dev/null || stat -f%z "$METRICS")" \
  --argjson qa_size "$(stat -c%s "$QA" 2>/dev/null || stat -f%z "$QA")" \
  '{artifacts:{snap:$snap,metrics:$metrics,qa:$qa,sizes:{snap:$snap_size,metrics:$metrics_size,qa:$qa_size}}}' > "$GUARD"

else
  echo "STP5 FAIL - inspect $OUT_DIR and $QA"
  exit 4
fi  echo "TOKEN: TELEMETRY_ATTEST_OK"
    echo "TOKEN: ECHO_WINDOW_10S_OK"
    echo "TOKEN: TELEMETRY_ARTIFACTS_EMITTED"
  } | tee -a "$RECEIPT"
  echo "STP5 PASS"
else
  echo "STP5 FAIL — inspect $OUT_DIR and $QA"
  exit 4
fi