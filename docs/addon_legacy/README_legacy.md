# ha-sphero-bb8: Home Assistant BLE/MQTT Bridge for Sphero BB-8

## Project Purpose & Current State

- Hardware-only BLE/MQTT bridge for Sphero BB-8, designed for robust, production-grade Home Assistant integration.
- Simulation, mock, and fallback logic have been removed; only real hardware is supported.
- Operates in “peripheral/bridge mode”: Home Assistant is the sole orchestrator, BB-8 acts as a peripheral, receiving commands via MQTT and reporting status back.

## MVP and Acceptance Criteria

- MVP: Fully empirical, hardware-in-the-loop demonstration—Home Assistant sends an MQTT command, BB-8 acts, and feedback is observed/logged.
- No simulation or theoretical “green checks”; only real device feedback counts.
- Protocol/adapter gaps and handler mismatches are logged as future work, not blockers for MVP closure.

## Architecture & Flow

- Home Assistant (HA) → Mosquitto (MQTT broker) → BB-8 Bridge (MacBook/Pi) → BB-8 (via BLE).
- All orchestration and automation logic lives in HA; the bridge is a stateless relay.
- Typical flow: HA automation triggers → MQTT command → bridge relays to BB-8 → BB-8 acts → status/diagnostics sent back via MQTT.

## Key Features & Best Practices

- Native MQTT integration for command and status.
- Extensible via MQTT topics for new automations or BB-8 actions.
- Only one controller (the bridge) should own the BLE connection to BB-8 at any time.
- All smart logic is in HA; the bridge is kept simple and focused.

## Development & Testing

- Focus is on end-to-end, hardware-backed tests.
- Diagnostics and logs are prioritized for troubleshooting and validation.
- After MVP, further features and diagnostics may be added based on real use-cases.

## Strategic Decisions & Rationale

- Moved from dual-orchestration (standalone tool or HA) to single-mode, HA-mastered architecture for simplicity, maintainability, and scalability.
- Reduces code complexity, accelerates development, and makes future extension easier.

## Risks & Mitigations

- Single point of orchestration: If HA or MQTT is down, BB-8 cannot be controlled. Mitigated by robust reconnect logic and clear error reporting.
- BLE/MQTT reliability and latency are monitored.
- All platform dependencies are documented.

## Roadmap & Next Steps

- Finalize and document the single-mode bridge architecture.
- Remove all legacy simulation/dual-mode code.
- Harden bridge robustness and diagnostics.
- Prepare QA artifacts for final MVP acceptance.
- Future: Add more features, support for additional Sphero devices, and deeper HA integration as justified by real-world use.

## Project Directory Layout & Orientation

The workspace is organized for clarity, legacy reference, and active Home Assistant add-on development. Key directories:

- `addons/ha-bb8-addon/` — Official Home Assistant add-on source, synchronized for deployment and production use.
- `local.ha-bb8-addon/` — Local development and staging area for the add-on, including meta documentation and onboarding material.
- `ha-sphero-bb8/` — Legacy/archival project folder, containing the original Python BLE/MQTT bridge, historical artifacts, and reference code. Not used for current add-on builds.
  - `docs/` — Consolidated project documentation, including historical meta/ and design notes.
  - `legacy/` — Archived tools, tests, and scripts from earlier development phases.
  - `tools/setup/` — Obsolete setup scripts, retained for reference.
  - `vendor/` — Legacy vendor code, preserved for future lookbacks.
  - `src/` — Original source code for the Python bridge (now legacy).
  - `logs/` — Historical logs, diffs, and patch records.

**Best Practices:**

- All new development and production deployments should occur in `addons/ha-bb8-addon/` and `local.ha-bb8-addon/`.
- Use `ha-sphero-bb8/` only for reference, not for active code changes.
- Documentation and onboarding material are centralized in `local.ha-bb8-addon/meta/` and `ha-sphero-bb8/docs/`.

This structure ensures a clean separation between legacy material and the current, production-focused Home Assistant add-on.
