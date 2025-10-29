---
id: "PLAN-SUPERVISOR-DEPLOYMENT-01"
title: "Supervisor-First Corrective Plan for HA-BB8 Add-on Deployment and Diagnostics"
authors: "Strategos (HA-BB8 Team)"
slug: "supervisor-first-deployment-plan"
type: "plan"
tags: ["process", "architecture", "feature", "governance", "home-assistant", "addon", "ble", "mqtt"]
date: "2025-10-26"
last_updated: "2025-10-26"
---

# Supervisor-First Corrective Plan for HA-BB8 Add-on Deployment and Diagnostics

![Status: In progress](https://img.shields.io/badge/status-In%20progress-yellow)

This plan corrects drift by mandating **Supervisor-only** deployment for the BB‑8 add-on, banning host-side operational scripts, and adding **MQTT-invoked diagnostics and actuation** to verify real device behavior (wake → roll → stop → LED) on hardware. All evidence is mirrored under `/config/ha-bb8` while execution occurs strictly via Home Assistant add-on surfaces.

## 1. Requirements & Constraints

- **REQ-001**: Perform all deployments via **HA Supervisor** (`ha addons reload|rebuild|restart`); no rsync/git on HA host.
- **REQ-002**: Confine host writes to `/config/ha-bb8/**` (evidence only); **no host utility scripts**.
- **REQ-003**: All testing via **MQTT topics** owned by the add-on (`bb8/cmd/*`, `bb8/ack/*`, `bb8/status/*`).
- **REQ-004**: Provide MQTT commands for **diag_scan**, **diag_gatt**, and **actuate_probe**.
- **REQ-005**: Keep services **foreground-supervised**; no background daemons.
- **SEC-001**: Validate/clamp inputs; fail-closed on violations; protect credentials; no privilege escalation beyond stated add-on settings.
- **CON-001**: **ADR‑0024** path hygiene enforced; runtime writes only under `/data` (container) and `/config/ha-bb8` (host evidence).
- **GUD-001**: Publish structured ACK/NACK for every command with `cid`.
- **PAT-001**: Facade pattern with `bridge_controller` + `mqtt_dispatcher` + `safety` modules; dispatcher drives subscriptions and telemetry.

## 2. Implementation Steps

### Implementation Phase 1

- **GOAL-001**: **Supervisor-only deployment and governance reset**; remove host scripts; wire add-on capabilities required for BLE (BlueZ/DBus) while keeping least privilege.

| Task         | Description                                                                                                                                                                                                           | Completed | Date |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ---- |
| **TASK-001** | **Update add-on manifest** `addon/config.json`: ensure keys `host_dbus: true`, `udev: true`, `host_network: true`; retain `startup: services`, `boot: auto`.                                                          |           |      |
| **TASK-002** | **Ban host operational scripts**: delete `/config/ha-bb8/tools/*` (if present) and add plan note forbidding re-creation; evidence removal receipt in `/config/ha-bb8/checkpoints/BB8-FUNC/<ts>/host_cleanup.txt`.     |           |      |
| **TASK-003** | **Supervisor deploy only**: modify CI task/ops scripts to call `ha addons reload`, `ha addons rebuild local_beep_boop_bb8`, `ha addons restart local_beep_boop_bb8`; remove any rsync of code.                        |           |      |
| **TASK-004** | **Dispatcher connectivity introspection**: expose `attach_connected_callable(cb)` in `addon/bb8_core/mqtt_dispatcher.py`; use to set telemetry `connected` from `facade.is_connected()`; default to `True` if `None`. |           |      |
| **TASK-005** | **Bridge controller attach**: in `addon/bb8_core/bridge_controller.py` call `disp.attach_connected_callable(facade.is_connected)` if available.                                                                       |           |      |
| **TASK-006** | **Supervisor rebuild & restart** via HA CLI only; capture stdout to `/config/ha-bb8/checkpoints/BB8-FUNC/<ts>/supervisor_restart.log`.                                                                                |           |      |

### Implementation Phase 2

- **GOAL-002**: **On-device diagnostics and actuation over MQTT**; evidence-first verification of locomotive/visual response.

| Task         | Description                                                                                                                                                                                                                                                   | Completed | Date |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ---- |
| **TASK-007** | **Register diagnostic commands** in `addon/bb8_core/bridge_controller.py`: `bb8/cmd/diag_scan`, `bb8/cmd/diag_gatt`, `bb8/cmd/actuate_probe`. Implement handlers that return ACK dicts and publish details on `bb8/status/telemetry`.                         |           |      |
| **TASK-008** | **Facade stubs/impl** in `addon/bb8_core/facade.py`: `async diag_scan(mac, adapter="hci0") -> {found:bool,rssi:int?,name:str?}` (5–8s scan via bleak); `async diag_gatt(mac)->bool` (≤5s quick connect).                 |           |      |
| **TASK-009** | **Actuation probe** in controller: `wake → drive(speed=80,heading=180,ms=500) → stop → led_preset("white")`; ACK on `bb8/ack/actuate_probe`; publish `{"probe":"actuate","done":true}` to telemetry.                                                          |           |      |
| **TASK-010** | **Acceptance evidence via MQTT only** (no host scripts): use `mosquitto_pub/sub` to invoke and capture `c1_scan_ack.json` and `c2_actuation_ack.json` into `/config/ha-bb8/checkpoints/BB8-FUNC/<ts>/`; mirror to `reports/checkpoints/BB8-FUNC/ssh_c_<ts>/`. |           |      |
| **TASK-011** | **Binary gate**: PASS when `c1_scan_ack.json` has `{ok:true}` for MAC `ED:ED:87:D7:27:50` and `c2_actuation_ack.json` has `{ok:true}`; otherwise capture last 300 add-on logs to `<ts>/addon_logs_tail.txt` for triage.                                       |           |      |

## 3. Alternatives

- **ALT-001**: Keep rsync/SSH deployment and host shell scripts. **Rejected**: violates Supervisor-first governance; not portable or reproducible.
- **ALT-002**: HTTP control surface. **Rejected**: out of scope; MQTT already defined and integrated with HA.

## 4. Dependencies

- **DEP-001**: `paho-mqtt>=2,<3`, `bleak==0.22.3`, `spherov2==0.12.1` (already pinned in add-on image).
- **DEP-002**: HA Mosquitto add-on reachable as `core-mosquitto` with valid credentials.
- **DEP-003**: BlueZ/DBus availability in HA OS (via `host_dbus: true`, `udev: true`).

## 5. Files

- **FILE-001**: `addon/config.json` — Supervisor capability flags (DBus/udev/host_network).
- **FILE-002**: `addon/bb8_core/mqtt_dispatcher.py` — `attach_connected_callable()` and telemetry heartbeat.
- **FILE-003**: `addon/bb8_core/bridge_controller.py` — register diag/actuation handlers; attach connected callback.
- **FILE-004**: `addon/bb8_core/facade.py` — `diag_scan()` and `diag_gatt()` async stubs/impl.
- **FILE-005**: `reports/checkpoints/BB8-FUNC/ssh_c_<ts>/` — mirrored evidence copies.

## 6. Testing

- **TEST-001**: Supervisor deploy log contains `addons rebuild ...` and `addons restart ...` with exit 0; artifact saved at `/config/ha-bb8/checkpoints/BB8-FUNC/<ts>/supervisor_restart.log`.
- **TEST-002**: `mosquitto_pub/sub` 1: publish `bb8/cmd/diag_scan` for MAC `ED:ED:87:D7:27:50` and adapter `hci0`; expect `bb8/ack/diag_scan` JSON with `{ok:true}` within 10s; save to `c1_scan_ack.json`.
- **TEST-003**: `mosquitto_pub/sub` 2: publish `bb8/cmd/actuate_probe`; expect `bb8/ack/actuate_probe` with `{ok:true}` within 18s; save to `c2_actuation_ack.json`.
- **TEST-004**: On failure of TEST-002 or TEST-003, capture `docker logs --tail 300` to `<ts>/addon_logs_tail.txt` and mark phase as REWORK.

## 7. Risks & Assumptions

- **RISK-001**: BLE adapter permissions or DBus access insufficient → mitigated by `host_dbus` + `udev` and logging.
- **RISK-002**: Broker auth mismatch → mitigated by explicit `MQTT_USER/PASSWORD` env; NACK reasons propagated.
- **ASSUMPTION-001**: Target BB‑8 MAC `ED:ED:87:D7:27:50` and adapter `hci0` are correct and reachable during testing window.

## 8. Related Specifications / Further Reading

- ADR‑0024 Canonical Paths (internal)
- BB‑8 Command Schema (B2, internal)
- Safety & Estop (B3, internal)
