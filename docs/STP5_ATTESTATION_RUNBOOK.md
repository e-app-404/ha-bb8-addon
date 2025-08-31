# STP5_ATTESTATION_RUNBOOK.md — End-to-End Attestation Sequence (MQTT Evidence)

> Canonical, machine-friendly checklist for STP5 attestation, suitable for manual execution or automation. Use as reference for future sessions and as a basis for scripting.

---

## A) Pre-flight Checks

1. **Verify environment and dependencies:**
   - Ensure add-on container is running:
     - `docker ps --format '{{.Names}}' | grep -q addon_local_beep_boop_bb8`
   - Ensure evidence sink exists:
     - `test -d /config/reports`
   - Ensure required tools are available:
     - `command -v mosquitto_pub >/dev/null`
     - `command -v mosquitto_sub >/dev/null`
     - `command -v jq >/dev/null`

---

## B) Boot File Placement

2. **Place and prepare boot files:**
   - Copy provided boot files to `./bootloader/`
   - Make attestation script executable:
     - `chmod +x bootloader/stp5_attest.sh`

---

## C) Attestation Execution

3. **Run attestation script:**
   - Optionally set `BASE=bb8` (defaults to `bb8`)
   - Execute:
     - `sudo -E bash bootloader/stp5_attest.sh`

---

## D) Artifact Verification

4. **Verify output artifacts:**
   - Artifacts must exist and be non-empty:
     - `test -s /config/reports/stp5/telemetry_snapshot.jsonl`
     - `test -s /config/reports/stp5/metrics_summary.json`
     - `test -s /config/reports/qa_contract_telemetry_STP5.json`
   - QA verdict must be PASS:
     - `jq -e '.verdict=="PASS"' /config/reports/qa_contract_telemetry_STP5.json >/dev/null`
   - Metrics must meet thresholds:
     - `jq -e '.window_duration_sec>=10 and .echo_count>=3 and .echo_rtt_ms_p95<=250' /config/reports/stp5/metrics_summary.json >/dev/null`
   - Tokens must be appended to receipt (on PASS only):
     - `grep -F "TOKEN: TELEMETRY_ATTEST_OK" /config/reports/deploy_receipt.txt`
     - `grep -F "TOKEN: ECHO_WINDOW_10S_OK" /config/reports/deploy_receipt.txt`
     - `grep -F "TOKEN: TELEMETRY_ARTIFACTS_EMITTED" /config/reports/deploy_receipt.txt`

---

## E) Phase Update (On PASS)

5. **Update phase status:**
   - Mark `P5-TELEMETRY` as completed in `phases.yaml`.
   - Append/patch outputs as needed.

---

## F) Guard Report Review

6. **Review guard report:**
   - Inspect `/config/reports/stp5_guard_report.json` for artifact paths and sizes.
   - Ensure all referenced files are >0 bytes.

---

## G) Operator ACK & Gate Check

7. **Stop and await operator acknowledgment.**
   - No further phases until ACK.
   - Use `stp5_gate.sh` for binary PASS/FAIL check.

---

## H) Remediation (On FAIL)

8. **Intervene and remediate:**
   - If container not running: start/redeploy add-on, re-run attestation.
   - If no echoes: re-run, nudge with `mosquitto_pub`.
   - If broker auth fails: correct credentials in config, re-run.
   - Use guard report and logs for triage.

---

## I) Sign-off Block

- **Post-PASS:** Update `phases.yaml`, archive boot pack checksums, stop, await ACK.
- **Post-FAIL:** Do not append tokens; use guard report and logs to remediate, then re-run.

---

## What NOT to Change

- Do not modify image settings in config (stay in LOCAL_DEV).
- Do not add new patches.
- Do not rebuild outside HA Supervisor except for diagnostics.

---

## If Blocked

- Use HA UI to rebuild/start add-on.
- If Supervisor warns "removed from repository", reload the store and ensure `/addons/local/beep_boop_bb8` exists.

---

## Session Closeout

- Once all gates are passed and the add-on is started, the session is considered stable and closed. Further work (telemetry, CI) should be scheduled for a new session.
