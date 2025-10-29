#!/usr/bin/env bash
set -Eeuo pipefail

# Supervisor-only restart + MQTT-only probes (no docker exec, no host utility scripts)
# Evidence is produced locally first, then mirrored to the HA host under /config/ha-bb8/**.

# Inputs (can be provided via .evidence.env or environment)
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
EVID_LOCAL_BASE="$ROOT_DIR/reports/checkpoints/BB8-FUNC"

if [ -f "$ROOT_DIR/.evidence.env" ]; then
  # shellcheck disable=SC1090
  set -a; source "$ROOT_DIR/.evidence.env"; set +a || true
fi

HOST="${HOST:-homeassistant}"
ADDON="${ADDON:-local_beep_boop_bb8}"

# MQTT to broker (run locally; this is the only control surface for tests)
BROKER="${MQTT_HOST:-${BROKER:-127.0.0.1}}"
PORT="${MQTT_PORT:-1883}"
USER="${MQTT_USER:-mqtt_bb8}"
PASS="${MQTT_PASSWORD:-mqtt_bb8}"
BASE="${MQTT_BASE:-${BASE:-bb8}}"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOCAL_DIR="$EVID_LOCAL_BASE/$TS"
HOST_DIR="/config/ha-bb8/checkpoints/BB8-FUNC/$TS"
mkdir -p "$LOCAL_DIR"

# 1) Supervisor-only restart
if [ "${REBUILD:-0}" = "1" ]; then
  ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$HOST" \
    "ha addons reload && ha addons rebuild '$ADDON' && ha addons restart '$ADDON'" \
    | tee "$LOCAL_DIR/supervisor_restart.log"
else
  ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$HOST" \
    "ha addons reload && ha addons restart '$ADDON'" \
    | tee "$LOCAL_DIR/supervisor_restart.log"
fi

# 2) Telemetry presence (G1)
CID="g2-$TS-$$"
if command -v timeout >/dev/null 2>&1; then
  timeout 30s mosquitto_sub -h "$BROKER" -p "$PORT" -u "$USER" -P "$PASS" \
    -t "$BASE/status/telemetry" -C 1 -W 30 > "$LOCAL_DIR/telemetry.json" || true
else
  mosquitto_sub -h "$BROKER" -p "$PORT" -u "$USER" -P "$PASS" -t "$BASE/status/telemetry" -C 1 \
    > "$LOCAL_DIR/telemetry.json" & P=$!; SECS=0; while [ $SECS -lt 30 ] && kill -0 $P 2>/dev/null; do sleep 1; SECS=$((SECS+1)); done; kill $P 2>/dev/null || true
fi
grep -q '"connected"' "$LOCAL_DIR/telemetry.json" && echo ACCEPT > "$LOCAL_DIR/G1.status" || echo REWORK > "$LOCAL_DIR/G1.status"

# 3) Diagnostics + Actuation (G2) — subscribe then publish
( timeout 14s mosquitto_sub -h "$BROKER" -p "$PORT" -u "$USER" -P "$PASS" \
    -t "$BASE/ack/#" -C 1 -W 14 > "$LOCAL_DIR/c1_scan_ack.json" ) & sleep 0.25
mosquitto_pub -h "$BROKER" -p "$PORT" -u "$USER" -P "$PASS" \
  -t "$BASE/cmd/diag_scan" -m "{\"mac\":\"ED:ED:87:D7:27:50\",\"adapter\":\"hci0\",\"cid\":\"$CID-c1\"}"
wait || true

( timeout 20s mosquitto_sub -h "$BROKER" -p "$PORT" -u "$USER" -P "$PASS" \
    -t "$BASE/ack/#" -C 1 -W 20 > "$LOCAL_DIR/c2_actuation_ack.json" ) & sleep 0.25
mosquitto_pub -h "$BROKER" -p "$PORT" -u "$USER" -P "$PASS" \
  -t "$BASE/cmd/actuate_probe" -m "{\"cid\":\"$CID-c2\"}"
wait || true

OK1=false; OK2=false; CID1=false; CID2=false
grep -q '"ok"[[:space:]]*:[[:space:]]*true' "$LOCAL_DIR/c1_scan_ack.json" 2>/dev/null && OK1=true || true
grep -q '"ok"[[:space:]]*:[[:space:]]*true' "$LOCAL_DIR/c2_actuation_ack.json" 2>/dev/null && OK2=true || true
grep -q "\"cid\"[[:space:]]*:[[:space:]]*\"$CID-c1\"" "$LOCAL_DIR/c1_scan_ack.json" 2>/dev/null && CID1=true || true
grep -q "\"cid\"[[:space:]]*:[[:space:]]*\"$CID-c2\"" "$LOCAL_DIR/c2_actuation_ack.json" 2>/dev/null && CID2=true || true

([ "$OK1" = true ] && [ "$OK2" = true ] && [ "$CID1" = true ] && [ "$CID2" = true ]) && echo ACCEPT > "$LOCAL_DIR/G2.status" || echo REWORK > "$LOCAL_DIR/G2.status"

# 4) Package evidence and compute sha
tar -czf "$LOCAL_DIR/evidence_$TS.tgz" -C "$LOCAL_DIR" .
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$LOCAL_DIR/evidence_$TS.tgz" | tee "$LOCAL_DIR/manifest.sha256" >/dev/null
else
  shasum -a 256 "$LOCAL_DIR/evidence_$TS.tgz" | tee "$LOCAL_DIR/manifest.sha256" >/dev/null
fi

# 5) Mirror to host evidence directory (copy-out only; not deploy)
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$HOST" "mkdir -p '$HOST_DIR'"
scp -q "$LOCAL_DIR"/* "$HOST:$HOST_DIR/" || true

# 6) On G2 REWORK, capture add-on logs for operator review
if [ "$(cat "$LOCAL_DIR/G2.status" 2>/dev/null || echo REWORK)" != "ACCEPT" ]; then
  ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$HOST" "ha addons logs '$ADDON' --lines 300" \
    | tee "$LOCAL_DIR/addon_logs_tail.txt" >/dev/null || true
  scp -q "$LOCAL_DIR/addon_logs_tail.txt" "$HOST:$HOST_DIR/" || true
fi

# 7) Receipt (<=10 lines)
G1=$(cat "$LOCAL_DIR/G1.status" 2>/dev/null || echo REWORK)
G2=$(cat "$LOCAL_DIR/G2.status" 2>/dev/null || echo REWORK)
printf "[Gate]: G1 %s, G2 %s\n" "$G1" "$G2"
echo "- Highlights: diag_scan=$OK1 cid1=$CID1 actuate_probe=$OK2 cid2=$CID2 telemetry_field=$(grep -q '\"connected\"' \"$LOCAL_DIR/telemetry.json\" && echo present || echo missing)"
echo "- Evidence host: $HOST_DIR"
echo "- Evidence local: $LOCAL_DIR"
echo "- SHA256: $(cut -d' ' -f1 \"$LOCAL_DIR/manifest.sha256\")"
echo "- Next: if G2=REWORK → patch handlers in bridge_controller/facade; Supervisor rebuild+restart; rerun"
