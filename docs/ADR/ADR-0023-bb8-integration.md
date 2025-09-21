---
title: "ADR-0023: BB-8 Integration — Purpose, Constraints, and Runner Governance"
date: 2025-09-20
status: Proposed
author:
  - Evert Appels
related: 
   - ADR-0001
   - ADR-0004
   - ADR-0009
   - ADR-0012
   - ADR-0020
   - ADR-0014
supersedes: []
last_updated: 2025-09-20
tags: ["bb8", "integration", "runner", "governance", "pol", "proof-of-life", "safety", "mqtt", "home-assistant"]
---

# ADR-0023: BB-8 Integration — Purpose, Constraints, and Runner Governance

## Context

>This repository contains the Home Assistant add-on and supporting code for integrating a Sphero BB-8 device. Connecting to physical hardware has historically been unreliable due to intermittent BLE access, differing development platforms (macOS vs Raspberry Pi Supervisor), and unclear runner ordering semantics. This ADR defines a conservative, auditable approach to make integration predictable and safe.

## Decision

We adopt a canonical, project-level approach for BB-8 hardware integration and add-on lifecycle. This document records constraints, safety rules, runner behavior, and update steps required to support a stable "bleep" proof-of-life (POL) and a Supervisor-managed add-on lifecycle.

## Goals (inferred)

- Primary: reliably connect to a physical BB-8 and confirm an observable output (LED, tone, or motion) from the add-on via Home Assistant.
- Secondary: keep operations safe, auditable, and reproducible so contributors and automation can test and deploy changes deterministically.
- Make the add-on updateable via Home Assistant Supervisor with deterministic startup ordering and health checks.

## Constraints and non-goals

- Safety first: avoid unintended motion (rolling) unless explicitly requested and authorized in a live run.
- The add-on and tools must support a dry/simulated mode (default) for CI and local development when BLE hardware is absent.
- This ADR documents operational patterns and minimal runner changes; it does not mandate a large refactor.

## Architecture & key decisions

1) Dual-mode operation (dry vs live)
   - Default: dry mode (CI/local) that simulates hardware responses and publishes expected MQTT messages without BLE access.
   - Live mode: opt-in via environment variable or CLI flag (e.g., ENABLE_BB8_LIVE=1 or `--live`) and requires human confirmation when used interactively.

2) BLE access and platform assumptions
   - Production runtime target: Home Assistant Supervisor on a Raspberry Pi 5 with a supported Bluetooth adapter.
   - Development machines (macOS, Linux) should run in dry mode by default. Live BLE on macOS is supported only when the developer allows permission.

3) Add-on update and deployment
   - Typical steps:
     a. Bump add-on version and update `VERSION`.
     b. Update Dockerfile/build artifacts when dependencies change.
     c. Publish the updated build to the repository/index used by Supervisor.
     d. In Supervisor UI: update and restart the add-on (or use scripted deploy).
   - The runner must log deterministic startup sequencing and fail fast with clear MQTT diagnostics if preconditions fail (e.g., BLE adapter offline).

4) Runner ordering and health checks (strict sequence)
   1. Load configuration (`init_config()`)
   2. Initialize logging and reports directories
   3. Start MQTT client and verify connectivity
   4. Attach controller and BLE bridge (deferred until MQTT client is connected)
   5. Run discovery and publish Home Assistant discovery entities
   6. In live mode: run a one-time, safe POL (LED blink by default)
   7. Report POL outcome to a well-known MQTT topic and a local report file
   8. Enter the normal service loop (responders, presence scanner, etc.)

Each step should emit a structured (redacted) lifecycle event to the `reports/` directory and to MQTT under `bb8/addon/status` for Supervisor visibility.

5) Proof-of-life (POL) behavior
   - POL is explicit and opt-in. In live mode the default action is a short LED blink/pulse (1s) to minimize risk.
   - Optional escalation (tone or small motion) requires a separate human-set environment variable and explicit consent (for example, a supervisor/dev confirmation and physical cradle placement).
   - POL must be bounded by a short timeout (e.g., 10s) and must not change device configuration or pairing state.

6) Home Assistant integration surface
   - The add-on publishes discovery entities for presence, RSSI, and a control entity (switch or script) to trigger POL. It also publishes a POL status binary_sensor indicating success/failure.
   - HA automations should use the published discovery entities to trigger POL when desired.

7) Testing & simulation
   - Provide a local CLI driver `addon/tools/bleep_run.py` that supports `--dry` (default) and `--live` modes. `--dry` simulates BLE calls and publishes the same MQTT messages; `--live` attempts a single connect and executes the POL step (LED blink by default).

## Compliance with existing ADRs

This ADR is scoped to runner behavior and POL governance and must be read alongside the governance ADRs listed in the front-matter. Notable interactions and compliance requirements:

- ADR-0001 (workspace topology): the project uses a canonical reports sink. This ADR pins POL/run reports to `reports/bleep_run/` (a subfolder of the canonical sink) so POL artifacts are discoverable and machine-greppable.
- ADR-0004 (CRTP): assets under `addon/tools/` are only allowed if they are referenced by the image/runtime or explicitly whitelisted. `addon/tools/bleep_run.py` is permitted when invoked by the runtime container or when `addon/.allow_runtime_scripts` exists. Otherwise the runner should live in `ops/` or `scripts/`.
- ADR-0009 (ADR governance): front-matter ordering, `last_updated` update on edits, and inclusion of a `TOKEN_BLOCK` are required. A TOKEN_BLOCK is included below.
- ADR-0012 (layout & imports): runtime code must live under `addon/bb8_core/` and imports must use the canonical `addon.` package paths. Any runtime-invoked POL helpers must follow this import layout.
- ADR-0020 (motion safety & MQTT contract): POL defaults and MQTT topic structure follow the motion-safety policy: `ALLOW_MOTION=0` by default and POL should prefer a non-motion observable (LED blink). MQTT publishes must avoid wildcards and follow the established topic conventions.

## Reports and MQTT topics (recommended)

Recommended paths and topics to make POL outcomes discoverable by automation and operators:

- Local report files: `reports/bleep_run/bleep_run_<ISO_TS>.log` (keep local; not part of the add-on image publishing step).
- Lifecycle & status topic: `bb8/addon/status` — structured JSON lifecycle events (startup, discovery_ok, pol_result, error).
- Device POL status (retained): `bb8/<device>/pol/status` — JSON { status: "success"|"failure", reason: str, timestamp: ISO8601 } (retain=true).

All MQTT publishes must avoid wildcards and must set retention intentionally per ADR-0020.

## Runner placement & CRTP guidance

Because `bleep_run.py` is both an operational helper and a local CLI, maintainers may:

1. Keep `addon/tools/bleep_run.py` in the add-on subtree and add `addon/.allow_runtime_scripts` to explicitly whitelist it (preferred when the runner is referenced by the image or runtime entrypoint).
2. Move the runner to `ops/` or `scripts/` if it is purely an operator tool and not invoked by the container image.

Decision: default to keeping the runner in `addon/tools/` and add `addon/.allow_runtime_scripts` if it will be invoked by the container. If no runtime invocation exists, move to `ops/`.

## Proof-of-life defaults (aligned with ADR-0020)

- Default: `ALLOW_MOTION=0` (motion disabled unless explicitly opt-in).
- Default POL observable: LED blink/pulse for 1s.
- POL timeout: 10s. POL must not change pairing or persistent device config.

## Consequences

- Developers can run a safe dry-run locally that follows the same runner path as production.
- Supervisor-managed add-on updates follow a documented process; POL outcomes are auditable via MQTT and local reports.
- Live POL is opt-in, which minimizes accidental device movement.

## Implementation plan (high level)

1. Update the runner to emit deterministic lifecycle events and implement the POL step.
2. Ensure `addon/tools/bleep_run.py` supports dual-mode behavior and writes reports to `reports/` (or a subfolder like `reports/bleep_run/`).
3. Add/update Home Assistant discovery publication (dispatcher) to ensure required entities exist.
4. Record this ADR in `docs/ADR` (this document).
5. Validate on a local HA Supervisor (Raspberry Pi 5) and iterate on deployment steps.

## Open questions

- Which Supervisor add-on publish workflow do we prefer (git-based, registry-based, or local dev add-on install)?
- What additional POL behaviors beyond LED blink are acceptable (tone, roll)? Rolling requires explicit consent.

## Status and next steps

- This ADR is the canonical decision record and will be referenced for subsequent changes.
- Next: verify environment and BLE permissions, inspect `addon/tools/bleep_run.py`, and attempt a safe BLE scan (dry first). Any live connect or POL will require an explicit `--live` flag and your confirmation.

## Appendix: canonical message (optimized request)

Purpose

We will prioritize making a stable BB-8 integration the core deliverable: the add-on must reliably connect to physical BB-8 hardware via Home Assistant Supervisor and perform a simple, observable POL (LED blink, tone, or movement) that is confirmable from the Supervisor UI and via published MQTT events.

Constraints

- Default operation is dry/simulated for CI and local development. Live BLE actions are opt-in and bounded.
- POL must be low-risk by default (LED blink) and only escalate to motion with explicit authorization.
- The runner must be deterministic, auditable, and publish lifecycle and POL events.

Actionable next steps

- Verify local environment and availability of `spherov2` and BLE access.
- Implement a guarded POL helper and CLI runner that writes a report under `reports/`.
- Update add-on artifacts and publish to Supervisor; validate startup ordering and POL execution through Supervisor.

If you confirm, I will run environment checks and perform a dry BLE scan followed by a live scan/connect only after you reconfirm the live action. The live POL will default to an LED blink unless you explicitly request motion.

## Token Blocks

```yaml
TOKEN_BLOCK:
   accepted:
      - ADR_FORMAT_OK
      - ADR_REDACTION_OK
      - ADR_GENERATION_OK
      - TOKEN_BLOCK_OK
      - BB8_POL_GOVERNANCE_OK
      - BB8_RUNNER_PLACEMENT_OK
   requires:
      - ADR_SCHEMA_V1
   drift:
      - DRIFT: adr_format_invalid
      - DRIFT: missing_token_block
      - DRIFT: adr_redaction_untracked
      - DRIFT: pol_reports_missing
```
