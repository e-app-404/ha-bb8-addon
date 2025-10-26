---
applyTo: '*'
description: 'Phase B5 — End-to-End Demo & Stabilization execution guidance for Copilot and operators'
---

# Phase B5 — End-to-End Demo & Stabilization
This instruction file outlines the steps to implement and validate the Phase B5 end-to-end demonstration for the HA-BB8 add-on, ensuring full control via Home Assistant through MQTT while maintaining all safety features intact.

## Execution mandate

```json
{
  "target_paths": [
    "addon/bb8_core/bridge_controller.py",
    "addon/scripts/b5_e2e_run.py",
    "reports/checkpoints/BB8-FUNC/b5_e2e_demo.log",
    "reports/checkpoints/BB8-FUNC/b5_summary.md"
  ],
  "objective": "Demonstrate full HA↔MQTT↔BB-8 control with safety intact: wake → preset → drive → stop → sleep; capture acks/telemetry and re-check echo health.",
  "acceptance": {
    "gate": "B5_E2E_DEMO_OK",
    "criteria": [
      "Scripted run completes: wake → preset (sunset) → drive (≤2s) → stop → sleep",
      "All MQTT acks present with no errors; no safety violations",
      "Telemetry present (connected/estop/last_cmd_ts/battery)",
      "Echo responder health re-run still green; no regressions",
      "b5_e2e_demo.log and b5_summary.md present with timings and success stats"
    ],
    "artifacts": [
      "reports/checkpoints/BB8-FUNC/b5_e2e_demo.log",
      "reports/checkpoints/BB8-FUNC/b5_summary.md"
    ]
  },
  "risk": [
    "Real-broker DNS/resolution outside container",
    "BLE intermittency increasing command latencies",
    "Race between stop and sleep on slow links"
  ],
  "rollback": "If any step fails, abort remaining motion; publish explicit NACK with reason; keep device in safe state (stopped) and do not sleep."
}
```

## Implement: Task List

### 1) E2E runner (script)

Create `addon/scripts/b5_e2e_run.py` that:

- Publishes the sequence to `core-mosquitto` in-container:
  1. `bb8/cmd/power {"action":"wake","cid":"b5-1"}`
  2. `bb8/cmd/led_preset {"name":"sunset","cid":"b5-2"}`
  3. `bb8/cmd/drive {"speed":120,"heading":90,"ms":1500,"cid":"b5-3"}`
  4. `bb8/cmd/stop {"cid":"b5-4"}`
  5. `bb8/cmd/power {"action":"sleep","cid":"b5-5"}`
- Subscribes to `bb8/ack/#` and `bb8/status/#` during the run and writes a single timeline to `reports/checkpoints/BB8-FUNC/b5_e2e_demo.log` (timestamps + topics + payloads).
- Exits non-zero if any NACK or safety violation appears.

### 2) Echo health re-check

- After the run, re-invoke the echo harness (same tool used in INT-HA-CONTROL Gate A). Append a brief "echo OK" line with round-trip latency (ms) to `reports/checkpoints/BB8-FUNC/b5_summary.md`.

### 3) Summarize results

Create `reports/checkpoints/BB8-FUNC/b5_summary.md` (human-readable):

- Latencies: mean ACK time per command; any retries
- Telemetry presence checklist
- Final status: PASS/FAIL
- Deviations or notes (e.g., early preset cancellation by override)

### 4) Operator runbook (for HA shell)

```bash
# In the add-on container
python3 addon/scripts/b5_e2e_run.py | tee reports/checkpoints/BB8-FUNC/b5_e2e_demo.log

# (Optional) Manual drive smoke
mosquitto_pub -h core-mosquitto -t bb8/cmd/power -m '{"action":"wake","cid":"smoke-1"}'
mosquitto_pub -h core-mosquitto -t bb8/cmd/drive -m '{"speed":100,"heading":0,"ms":1000,"cid":"smoke-2"}'
mosquitto_pub -h core-mosquitto -t bb8/cmd/stop -m '{"cid":"smoke-3"}'
mosquitto_pub -h core-mosquitto -t bb8/cmd/power -m '{"action":"sleep","cid":"smoke-4"}'
```

### 5) Governance hygiene

- Keep all evidence under `reports/checkpoints/BB8-FUNC/…` and include a `manifest.sha256`.
- No background daemons—runner exits on completion with a clear code.
- Use `core-mosquitto` as broker host in-container.

## B5 Status cadence (10‑liner)

```arduino
[B5 Verdict]: PENDING/ACCEPT/REWORK
- Run sequence: wake → preset → drive → stop → sleep
- MQTT acks: all received (no errors)
- Telemetry: present (connected/estop/last_cmd_ts/battery)
- Safety violations: none
- Echo health: green (round-trip X ms)
- Evidence: b5_e2e_demo.log, b5_summary.md attached
- ADR-0024 paths: OK
- Foreground supervision: OK
- Notes: (retries/timeouts if any)
```
