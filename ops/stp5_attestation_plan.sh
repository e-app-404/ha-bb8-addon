
#!/usr/bin/env bash
# ops/stp5_attestation_plan.sh — End-to-End STP5 Attestation Sequence (MQTT Evidence)
# Purpose: Automate and document the STP5 attestation process with explicit token gates and fix/re-run guidance.
set -euo pipefail

# --- Configurable Variables ---
BOOT_SCRIPT="${BOOT_SCRIPT:-bootloader/stp5_attest.sh}"
REPORTS_DIR="${REPORTS_DIR:-/config/reports}"
PHASES_YAML="${PHASES_YAML:-/config/phases.yaml}"
LOGFILE="${LOGFILE:-$REPORTS_DIR/stp5_attestation.log}"

# --- Logging ---
exec > >(tee -a "$LOGFILE") 2>&1

# --- A) Pre-flight Checks ---

echo "[A-1] Verifying environment and dependencies..."
docker ps --format '{{.Names}}' | grep -q addon_local_beep_boop_bb8 || { echo "FAIL: Add-on container not running." >&2; exit 10; }
test -d "$REPORTS_DIR" || { echo "FAIL: $REPORTS_DIR does not exist." >&2; exit 11; }
command -v mosquitto_pub >/dev/null || { echo "FAIL: mosquitto_pub not found." >&2; exit 12; }
command -v mosquitto_sub >/dev/null || { echo "FAIL: mosquitto_sub not found." >&2; exit 13; }
command -v jq >/dev/null || { echo "FAIL: jq not found." >&2; exit 14; }

# --- B) Boot File Placement ---

echo "[B-2] Placing and preparing boot files..."
for f in "$BOOT_SCRIPT"; do
  if [ ! -f "$f" ]; then
    echo "FAIL: $f not found. Place boot files and re-run." >&2
    exit 15
  fi
done
chmod +x "$BOOT_SCRIPT"

# --- C) Attestation Execution ---

echo "[C-3] Running attestation script..."
sudo -E bash "$BOOT_SCRIPT"

# --- D) Artifact Verification ---

echo "[D-4] Verifying output artifacts..."
test -s "$REPORTS_DIR/stp5/telemetry_snapshot.jsonl" || { echo "FAIL: telemetry_snapshot.jsonl missing or empty." >&2; exit 16; }
test -s "$REPORTS_DIR/stp5/metrics_summary.json" || { echo "FAIL: metrics_summary.json missing or empty." >&2; exit 17; }
test -s "$REPORTS_DIR/qa_contract_telemetry_STP5.json" || { echo "FAIL: QA contract missing or empty." >&2; exit 18; }
jq -e '.verdict=="PASS"' "$REPORTS_DIR/qa_contract_telemetry_STP5.json" >/dev/null || { echo "FAIL: QA verdict is not PASS." >&2; exit 19; }
jq -e '.window_duration_sec>=10 and .echo_count>=3 and .echo_rtt_ms_p95<=250' "$REPORTS_DIR/stp5/metrics_summary.json" >/dev/null || { echo "FAIL: Metrics do not meet thresholds." >&2; exit 20; }
grep -F "TOKEN: TELEMETRY_ATTEST_OK" "$REPORTS_DIR/deploy_receipt.txt" || { echo "FAIL: TELEMETRY_ATTEST_OK token missing in receipt." >&2; exit 21; }
grep -F "TOKEN: ECHO_WINDOW_10S_OK" "$REPORTS_DIR/deploy_receipt.txt" || { echo "FAIL: ECHO_WINDOW_10S_OK token missing in receipt." >&2; exit 22; }
grep -F "TOKEN: TELEMETRY_ARTIFACTS_EMITTED" "$REPORTS_DIR/deploy_receipt.txt" || { echo "FAIL: TELEMETRY_ARTIFACTS_EMITTED token missing in receipt." >&2; exit 23; }

# --- D-5) Optional: Minimal function checks (soft gate) ---
echo "[D-5] Optional: Minimal function checks (soft gate)..."
ssh babylon-babes@homeassistant \"mosquitto_sub -h 127.0.0.1 -p 1883 -v -t 'homeassistant/#' -C 1 -W 3 || echo 'INFO: no discovery in 3s window'\"
ssh babylon-babes@homeassistant \"mosquitto_pub -h 127.0.0.1 -p 1883 -t 'bb8/echo/cmd' -m '{\\\"value\\\":1,\\\"ts\\\":'\\$(date +%s)'}'\"
mosquitto_sub -h 127.0.0.1 -p 1883 -v -t 'bb8/echo/#' -C 1 -W 3 || echo "INFO: no echo observed in 3s"

# --- E) Phase Update (On PASS) ---

echo "[E-5] Update phase status in phases.yaml..."
if command -v yq >/dev/null; then
  if [ -f "$PHASES_YAML" ]; then
    yq e '(.[] | select(.id == "P5-TELEMETRY").status) = "completed"' -i "$PHASES_YAML"
    echo "INFO: phases.yaml updated for P5-TELEMETRY."
  else
    echo "WARN: phases.yaml not found, manual update required."
  fi
else
  echo "INFO: yq not available, manual update required for phases.yaml."
fi

# --- F) Guard Report Review ---

echo "[F-6] Reviewing guard report..."
jq '.' "$REPORTS_DIR/stp5_guard_report.json" || { echo "FAIL: Guard report not found or invalid." >&2; exit 24; }

# --- G) Operator ACK & Gate Check ---

echo "[G-7] Awaiting operator acknowledgment."
if [ -f ops/stp5_gate.sh ]; then
  bash ops/stp5_gate.sh || { echo "FAIL: stp5_gate.sh gate check failed." >&2; exit 25; }
else
  read -p "Manual gate check required. Type 'ACK' to continue: " ACK
  if [ "$ACK" != "ACK" ]; then
    echo "FAIL: Operator did not acknowledge. Exiting." >&2
    exit 26
  fi
fi

# --- H) Remediation (On FAIL) ---
# (Remediation steps are handled by exit codes and operator review)

# --- I) Sign-off Block ---
echo "[I] Session complete. Post-PASS: update phases.yaml, archive boot pack checksums, stop, await ACK."
echo "Do NOT modify image settings in config (stay in LOCAL_DEV)."
echo "Do NOT add new patches."
echo "Do NOT rebuild outside HA Supervisor except for diagnostics."
echo "If blocked, use HA UI to rebuild/start add-on. If Supervisor warns 'removed from repository', reload the store and ensure /addons/local/beep_boop_bb8 exists."
echo "Session closeout complete. Further work (telemetry, CI) should be scheduled for a new session."
