---
goal: "Full HA↔MQTT↔BB-8 control — end-to-end implementation plan"
version: "1"
date_created: "2025-10-24"
last_updated: "2025-10-24"
owner: "HA-BB8 Team"
status: "In progress"
tags: ["feature", "architecture"]
---

# Introduction

![Status: In progress](https://img.shields.io/badge/status-In%20progress-yellow)

This plan delivers end-to-end control for HA↔MQTT↔BB-8, with deterministic, machine-executable phases and binary acceptance criteria.

## 1. Requirements & Constraints

- **REQ-001**: Provide movement, lighting, and power control via MQTT (`core-mosquitto`) with safety features enabled.
- **REQ-002**: Maintain ADR-compliant paths and foreground-supervised processes.
- **SEC-001**: Validate and clamp all external inputs; fail closed on violations.
- **CON-001**: No background daemons; no non-ADR path writes.
- **GUD-001**: Publish ACK/NACK for every command with correlation ID.
- **PAT-001**: Facade pattern with distinct safety/lighting/session modules.

## 2. Implementation Steps

### Phase 1 — MQTT Command Surfaces (Schemas & ACK/NACK)

**GOAL-001:** Define and validate `bb8/cmd/*` payloads and `bb8/ack/*` responses.

| Task        | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Action   | Path                       | Validation                                                                                                   | Exit |
|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|----------------------------|--------------------------------------------------------------------------------------------------------------|------|
| **TASK-001** | Write command/ack schemas (v1). Create `addon/schemas/bb8_v1.json` with a single JSON object containing: `$schema:"https://json-schema.org/draft/2020-12/schema"`, top-level `definitions` for commands `drive, stop, led, power, estop, clear_estop` and `ack` shape `{ok: boolean, cid: string?, reason: string?}`; each command includes exact fields and ranges: `drive:{speed:0..255, heading:0..359, ms:0..5000, cid?:string}`, `stop:{cid?:string}`, `led:{r:0..255,g:0..255,b:0..255,cid?:string}`, `power:{action:"wake" | "sleep",cid?:string}`, `estop:{cid?:string}`, `clear_estop:{cid?:string}`. | create   | addon/schemas/bb8_v1.json  | assert_json_schema(addon/schemas/bb8_v1.json, {"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object"}) | PASS |
| **TASK-002** | Wire facade handlers for `drive/stop/led/power/estop/clear_estop`. Perform regex replacement in `addon/bb8_core/facade.py` anchoring at `# MQTT handlers BEGIN` and `# MQTT handlers END`: replace the block with functions `_on_drive_cmd`, `_on_stop_cmd`, `_on_led_cmd`, `_on_power_cmd`, `_on_estop_cmd`, `_on_clear_estop_cmd` that (a) validate via `addon/schemas/bb8_v1.json`, (b) publish acks on `bb8/ack/<cmd>`, (c) reject malformed with `reason`. | replace  | addon/bb8_core/facade.py   | assert_regex_match(addon/bb8_core/facade.py, "def _on_led_cmd(")        | PASS |
| **TASK-003** | Route tests using paho-mqtt. Run `python3 scripts/b2_route_tester.py --host core-mosquitto --schema addon/schemas/bb8_v1.json --out reports/checkpoints/BB8-FUNC/b2_route_tests.log` and ensure all valid payloads ack and malformed reject with `reason`. | run      | scripts/b2_route_tester.py | assert_no_error_in_log(reports/checkpoints/BB8-FUNC/b2_route_tests.log, "ERROR | REJECT without reason") | PASS |

_Phase 1 dependencies: none. Phases are atomic._

### Phase 2 — Safety & Emergency Stop

**GOAL-002:** Enforce rate, speed, and duration caps; implement latched estop.

| Task        | Description                                                                                                                                                                                                                                                                                                                                 | Action   | Path                                         | Validation                                                                                                      | Exit |
|-------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|----------------------------------------------|---------------------------------------------------------------------------------------------------------------|------|
| **TASK-004** | Implement `MotionSafetyController`. Create file with class `MotionSafetyController` providing: `normalize_drive(speed,heading,ms)`, `gate_drive(now_monotonic)`, `activate_estop(reason)`, `clear_estop()`, properties `min_interval_ms>=50`, `max_duration_ms<=2000`, `max_speed<=180`, and atomic latch. | create   | addon/bb8_core/safety.py                     | assert_regex_match(addon/bb8_core/safety.py, "class MotionSafetyController")                                    | PASS |
| **TASK-005** | Integrate authoritative estop gating in facade. Replace motion entrypoints in `facade.py` so `drive()` first checks `safety.estop_latched` and returns NACK if true; call `normalize_drive()` then `gate_drive()`; update `_on_estop_cmd` to cancel active motion and publish telemetry; `_on_clear_estop_cmd` to clear and ack. | replace  | addon/bb8_core/facade.py                     | assert_regex_match(addon/bb8_core/facade.py, "def\s+drive(.*estop")                                             | PASS |
| **TASK-006** | Emit safety tests report. Run `pytest -q addon/tests/integration/test_safety_estop.py --json-report --json-report-file=/tmp/b3_safety_tests.json` then copy to `reports/checkpoints/BB8-FUNC/b3_safety_tests.json`. | run      | addon/tests/integration/test_safety_estop.py | assert_json_schema(reports/checkpoints/BB8-FUNC/b3_safety_tests.json, {"type":"object","required":["summary"]}) | PASS |

_Phase 2 dependencies: TASK-005 depends on [TASK-004]. TASK-006 depends on [TASK-004, TASK-005]._

### Phase 3 — Lighting & Presets

**GOAL-003:** Non-blocking LED presets with cancellation and estop behavior.

| Task        | Description                                                                                                                                                                                                                                                                                                                                                     | Action   | Path                          | Validation                                                             | Exit |
|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|-------------------------------|------------------------------------------------------------------------|------|
| **TASK-007** | Implement `lighting.py` with presets. Create functions `async set_static(r,g,b)`, `async run_preset(name,cancel_token)`, `cancel_active()`. Presets: `off=(0,0,0)`, `white=(255,255,255)`, `police=[(0,0,255,200ms),(255,0,0,200ms)]×10]`, `sunset=[(255,80,0,300ms),(255,20,0,300ms),(120,0,10,300ms)]×2]`; cancel on estop or new LED command. | create   | addon/bb8_core/lighting.py    | assert_regex_match(addon/bb8_core/lighting.py, "async def run_preset") | PASS |
| **TASK-008** | Generate LED matrix evidence. Run `python3 scripts/b4_emit_led_matrix.py --out reports/checkpoints/BB8-FUNC/b4_led_matrix.json` to write input→clamped output grid and preset step specs. | run      | scripts/b4_emit_led_matrix.py | assert_file_exists(reports/checkpoints/BB8-FUNC/b4_led_matrix.json)    | PASS |
| **TASK-009** | Demo sequence with logs. Run `python3 scripts/b4_led_demo.py --broker core-mosquitto --out reports/checkpoints/BB8-FUNC/b4_led_demo.log` to perform: start `police` → static orange override → start `sunset` → estop (cancel) → static `white` (allowed) → clear_estop → `sunset`. | run      | scripts/b4_led_demo.py        | assert_file_exists(reports/checkpoints/BB8-FUNC/b4_led_demo.log)       | PASS |

_Phase 3 dependencies: TASK-009 depends on [TASK-007]._

### Phase 4 — E2E Demo & Stabilization

**GOAL-004:** Full sequence with echo health recheck.

| Task        | Description                                                                                                                                                                                                                                                                                         | Action   | Path                               | Validation                                                                    | Exit |
|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|------------------------------------|--------------------------------------------------------------------------------|------|
| **TASK-010** | Run E2E runner (wake→preset→drive→stop→sleep). Run `python3 addon/scripts/b5_e2e_run.py --host core-mosquitto --wake sunset --drive-speed 120 --drive-heading 90 --drive-ms 1500 --stop --sleep --log reports/checkpoints/BB8-FUNC/b5_e2e_demo.log --cids b5-1,b5-2,b5-3,b5-4,b5-5`. | run      | addon/scripts/b5_e2e_run.py        | assert_no_error_in_log(reports/checkpoints/BB8-FUNC/b5_e2e_demo.log, "NACK | safety_violation"); assert_mqtt_ack("bb8/ack/power", "b5-1"); assert_mqtt_ack("bb8/ack/led_preset", "b5-2"); assert_mqtt_ack("bb8/ack/drive", "b5-3"); assert_mqtt_ack("bb8/ack/stop", "b5-4"); assert_mqtt_ack("bb8/ack/power", "b5-5") | PASS |
| **TASK-011** | Append echo health to summary. Run `python3 addon/scripts/echo_health_probe.py --host core-mosquitto --out reports/checkpoints/BB8-FUNC/b5_summary.md --append` to measure round-trip and write "echo green" line. | run      | addon/scripts/echo_health_probe.py | assert_regex_match(reports/checkpoints/BB8-FUNC/b5_summary.md, "echo.*green") | PASS |

_Phase 4 dependencies: TASK-011 depends on [TASK-010]._

## 3. Alternatives

- **ALT-001**: HTTP control surface (rejected: adds another surface; MQTT already scoped).
- **ALT-002**: Blocking LED animations (rejected: event loop contention).

## 4. Dependencies

- **DEP-001**: `paho-mqtt>=2,<3`, `bleak==0.22.3`, `spherov2==0.12.1`
- **DEP-002**: HA internal broker hostname `core-mosquitto`

## 5. Files

- **FILE-001**: addon/bb8_core/facade.py (MQTT handlers + acks)
- **FILE-002**: addon/bb8_core/safety.py (rate caps + estop)
- **FILE-003**: addon/bb8_core/lighting.py (LED presets)

## 6. Testing

- **TEST-001**: `b3_safety_tests.json` shows failed=0
- **TEST-002**: `b4_led_matrix.json` includes step specs; demo log shows cancellation ≤100 ms
- **TEST-003**: `b5_e2e_demo.log` has all ACKs; `b5_summary.md` shows echo green

## 7. Risks & Assumptions

- **RISK-001**: BLE intermittency increases latency
- **ASSUMPTION-001**: Broker reachable as `core-mosquitto` in-container

## 8. Related Specifications / Further Reading

- ADR-0024 Canonical Paths (internal)
- MQTT discovery notes (internal)

## 9. Template Compliance Checklist (AUTO-VERIFY)

- [x] Front matter present + fields populated
- [x] Status badge uses mapped color
- [x] All sections 1–8 present
- [x] IDs sequential and prefixed
- [x] Tasks include action/path/validation/exit
- [x] No placeholders; no undefined terms

