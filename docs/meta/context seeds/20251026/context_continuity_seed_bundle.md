---
id: "OPS-CONTEXT_CONTINUITY_SEED-01"
title: "Context Continuity Seed Bundle — Strategos Session Anchor v3"
authors: "HA-BB8 Team"
source: ""
slug: "context-continuity-seed-bundle"
type: "guide"
tags: ["governance", "oversight", "home-assistant", "addon", "mqtt", "ble", "evidence-first"]
date: "2025-10-27"
last_updated: "2024-06-13"
url: ""
related: ""
adr: ""
---

# Context Continuity Seed Bundle — Strategos Session Anchor v3

## Operating posture (non-negotiable)

- Supervisor-only deploy: `ha addons reload|rebuild|restart` (inside HA host context).
- MQTT-only checks and actuation via add-on topics; **no other control surface**.
- Host writes confined to `/config/ha-bb8/**` (evidence only). Container writes confined to `/data/**`.
- Foreground supervision only (no background daemons beyond add-on supervisor model).
- Proof = artifacts first; analysis second. **Binary gates** on every phase.
- **Forbidden:** host utility scripts, rsync/git of code to HA host, “offer lines”, fluff, or speculation. **Never lie.** When uncertain, return the evidence and the limit.
- **Receipts:** ≤10 lines, deterministic fields only.

## Execution etiquette

- Quiet/command-first. Avoid questions when a best-effort execution with receipts is possible.
- Partial results beat delays; always emit artifacts + manifest before commentary.

---

## Continuity Seed v3 — HA↔MQTT↔BB-8

```yaml
project:
    name: "HA-BB8"
    component: "bb8-integration"
    roadmap_hint: "plan-feature-bb8-integration-1.md"  # use as mental model/guardrails

governance:
    supervisor_only: true
    adr_0024_paths: true
    host_evidence_dir: "/config/ha-bb8/checkpoints/BB8-FUNC"
    container_runtime_root: "/data"
    foreground_supervision: true
    safety_first: true
    mqtt_ack_with_cid: true
    no_host_scripts: true
    no_offer_lines: true
    truth_over_speed: true

runtime:
    broker:
        host: "core-mosquitto"
        base_topic: "bb8"
    device:
        mac_primary: "ED:ED:87:D7:27:50"        # current target
        adapter: "hci0"
    addon:
        slug: "local_beep_boop_bb8"

status:
    phases:
        B1: "ACCEPT"
        B2: "ACCEPT"
        B3: "ACCEPT"
        B4: "ACCEPT"
        B5: "ACCEPT (E2E 5/5 ACKs, echo green)"
    token_block:
        requires: [ADR_0024_COMPLIANT_PATHS, FOREGROUND_SUPERVISION_OK, INTERNAL_BROKER_HOST_OK, BLE_SESSION_WATCHDOG_OK, EVIDENCE_FIRST_OK]
        accepted: [B1_BLE_LINK_OK, B2_CMD_SCHEMA_WIRED_OK, B3_SAFETY_ESTOP_OK, B4_LED_PRESETS_OK, B5_E2E_DEMO_OK]

workspace_archives:
    resolution_policy:
        order: ["repo", "host", "sandbox"]
        on_missing: "request_reupload"
        verify_checksums: true

receipts_contract:
    fields: [gate, highlights, evidence_host, evidence_local, next, confidence, drift]
    max_lines: 10

telemetry_contract:
    required_fields: [connected, estop, last_cmd_ts, battery_pct, ts]
    tolerance: {connected: [true, false]}
```

---

## Prime Prompt (Strategos → Copilot)

**Objective:** Deliver real on-device evidence for diagnostics and actuation using Supervisor-only deploy and MQTT-only probes; stage artifacts under governed paths; emit a ≤10-line receipt.

### Inputs (env/assumptions)

- SSH alias to HA host: `homeassistant` (or use the script’s auto-detection).
- MQTT auth via env: `MQTT_USER`, `MQTT_PASSWORD` (defaults acceptable if broker permits).
- Add-on slug: `local_beep_boop_bb8`.

### Outputs (must exist)

- Host evidence dir: `/config/ha-bb8/checkpoints/BB8-FUNC/<TS>/` with:
    - `supervisor_restart.log`, `telemetry.json`, `c1_scan_ack.json`, `c2_actuation_ack.json`, optional `addon_logs_tail.txt`
    - `evidence_<TS>.tgz`, `manifest.sha256` (sha256 of the tgz)
    - Gate status files: `G1.status`, `G2.status`
- Optional local mirror: `reports/checkpoints/BB8-FUNC/<TS>/` (copy-out only)

**Gates:**

- **G1 (Supervisor/telemetry):** ACCEPT when `telemetry.json` contains `"connected"` field within 30s after rebuild+restart.
- **G2 (Diagnostics+Actuation):** ACCEPT when both ACK files contain `"ok": true`.

### Command block (run as-is)

Strategos → Copilot (execute exactly; quiet)

```bash
# Supervisor-only deploy & MQTT probes (evidence confined; ADR-0024/0031)
set -Eeuo pipefail
HOST="${HOST:-homeassistant}"
ADDON="${ADDON:-local_beep_boop_bb8}"
BROKER="${BROKER:-core-mosquitto}"
PORT="${MQTT_PORT:-1883}"
USER="${MQTT_USER:-mqtt_bb8}"
PASS="${MQTT_PASSWORD:-mqtt_bb8}"
BASE="${BASE:-bb8}"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
DIR="/config/ha-bb8/checkpoints/BB8-FUNC/$TS"
CID="g2-$TS-$$"
mkdir -p "$DIR"

# Deploy via Supervisor only (rebuild optional)
if [ "${REBUILD:-0}" = "1" ]; then
    ssh "$HOST" "ha addons reload && ha addons rebuild $ADDON && ha addons restart $ADDON" | tee "$DIR/supervisor_restart.log"
else
    ssh "$HOST" "ha addons reload && ha addons restart $ADDON" | tee "$DIR/supervisor_restart.log"
fi

# Telemetry presence (G1)
timeout 30s mosquitto_sub -h "$BROKER" -p "$PORT" -u "$USER" -P "$PASS" \
    -t "$BASE/status/telemetry" -C 1 -W 30 > "$DIR/telemetry.json" || true
grep -q '"connected"' "$DIR/telemetry.json" && echo ACCEPT > "$DIR/G1.status" || echo REWORK > "$DIR/G1.status"

# Probes (G2) — subscribe first, then publish
( timeout 14s mosquitto_sub -h "$BROKER" -p "$PORT" -u "$USER" -P "$PASS" \
        -t "$BASE/ack/#" -C 1 -W 14 > "$DIR/c1_scan_ack.json" ) & sleep 0.25
mosquitto_pub -h "$BROKER" -p "$PORT" -u "$USER" -P "$PASS" \
    -t "$BASE/cmd/diag_scan" -m "{\"mac\":\"ED:ED:87:D7:27:50\",\"adapter\":\"hci0\",\"cid\":\"$CID-c1\"}"
wait || true

( timeout 20s mosquitto_sub -h "$BROKER" -p "$PORT" -u "$USER" -P "$PASS" \
        -t "$BASE/ack/#" -C 1 -W 20 > "$DIR/c2_actuation_ack.json" ) & sleep 0.25
mosquitto_pub -h "$BROKER" -p "$PORT" -u "$USER" -P "$PASS" \
    -t "$BASE/cmd/actuate_probe" -m "{\"cid\":\"$CID-c2\"}"
wait || true

# Gate + receipts (≤10 lines)
tar -czf "$DIR/evidence_$TS.tgz" -C "$DIR" . ; sha256sum "$DIR/evidence_$TS.tgz" | tee "$DIR/manifest.sha256"
OK1=$(grep -q '"ok": *true' "$DIR/c1_scan_ack.json" && echo true || echo false)
OK2=$(grep -q '"ok": *true' "$DIR/c2_actuation_ack.json" && echo true || echo false)
G2=$([ "$OK1" = true ] && [ "$OK2" = true ] && echo ACCEPT || echo REWORK)
[ "$G2" = REWORK ] && ssh "$HOST" "ha addons logs $ADDON --lines 300" | tee "$DIR/addon_logs_tail.txt" >/dev/null || true

printf "[Gate]: G1 %s, G2 %s\n" "$(cat "$DIR/G1.status")" "$G2"
echo "- Highlights: diag_scan=$OK1 actuate_probe=$OK2 telemetry_field=$(grep -q '\"connected\"' "$DIR/telemetry.json" && echo present || echo missing)"
echo "- Evidence host: $DIR"
echo "- SHA256: $(cut -d' ' -f1 "$DIR/manifest.sha256")"
echo "- Next: if G2=REWORK → patch handlers in bridge_controller/facade; Supervisor rebuild+restart; rerun this block"
```

---

## Guardrails & Token Gates

- **Always honor:** `supervisor_only`, `no_host_scripts`, `adr_0024_paths`, `mqtt_ack_with_cid`, `evidence_first`.
- **Never** add files outside `/config/ha-bb8/**` (host) and `/data/**` (container).
- **No offer lines; no flattery; no deflection.**
- If blocked: emit the smallest reproducible log excerpt and a 2-step remediation.

---

## Handoff Checklist (for any assistant picking up)

1. Read this anchor and seed; treat it as the sole source of operating truth until superseded.
2. Execute the **Command block** verbatim to establish/refresh evidence.
3. If G2 is REWORK: patch `bridge_controller` (register `diag_scan`, `diag_gatt`, `actuate_probe`) and `facade` (`diag_scan`, `diag_gatt`), rebuild via Supervisor, re-run probes.
4. Keep receipts ≤10 lines; mirror artifacts locally under `reports/checkpoints/BB8-FUNC/<TS>/`.
5. Never deviate from Supervisor-first and MQTT-only boundaries.

