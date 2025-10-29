# BB‑8 Workspace Instructions: How to Read and Operate This Repo

> Practical guide to navigate the code, run tests/QA, collect evidence, and deploy under the Home Assistant Supervisor-first model.

## What this repository is

Home Assistant add-on to control a Sphero BB‑8 via BLE, integrated with MQTT and governed by ADRs. It uses a foreground, single-process runtime model and centralized configuration. Evidence-driven acceptance (INT‑HA‑CONTROL) verifies operational behaviors.

## Start here (reading order)

1) `llms.txt` — High-level entrypoint with links to key docs, modules, and evidence harnesses.
2) `README.md` — Features, architecture outline, release workflow, and usage.
3) `docs/ADR/INDEX.md` — Canonical ADR index; skim ADR‑0031, ADR‑0032, ADR‑0037, ADR‑0041 first.
4) `.github/instructions/copilot-instructions.md` — Repo-governed agent/dev rules and guardrails.
5) `addon/bb8_core/` — Core runtime modules (see quick map below).

## Repository map (minimal)

- `addon/bb8_core/` — Core runtime
  - `bridge_controller.py` — orchestrator (BLE gateway/bridge + MQTT dispatcher)
  - `mqtt_dispatcher.py` — broker connect, subscribe/publish, HA discovery
  - `ble_gateway.py`, `ble_bridge.py` — BLE scan/connect and device interface
  - `addon_config.py` — structured config loader with provenance
  - `logging_setup.py` — centralized JSON logger with redaction
- `addon/` — Add-on image: `config.yaml`, `Dockerfile`, `run.sh`, `requirements.txt`
- `docs/ADR/` — Architectural Decision Records (policy, architecture, ops)
- `reports/checkpoints/` — Evidence outputs (governed harness only)
- `ops/` — Release, deploy, evidence, diagnostics, and QA helpers
- `.github/instructions/` — This file + repo governance docs

## Daily operations: commands and tasks

Preferred entry is via VS Code tasks (mapped below) or Makefile targets. Commands run from repo root unless noted.

- Tests (fast): `pytest -q addon/tests -k 'not slow'`
- QA: `make qa`
- Evidence (STP4): `make evidence-stp4`
- Env governance: `make env-validate`
- Release (patch): `make release-patch`

### VS Code tasks (wired)

- HA: Deploy over SSH — runs `ops/release/deploy_ha_over_ssh.sh`
- STP5 Supervisor BLE Attestation — runs `scripts/stp5_supervisor_ble_attest.sh` (requires HOST/PORT/USER/PASS/BASE)
- Env: validate — `make env-validate`
- HA: Restart add-on — `make ha-restart`
- Tests: fast — `pytest -q addon/tests -k 'not slow'`
- Evidence: STP4 — `make evidence-stp4`
- QA: make qa — `make qa`

## Acceptance vs dev-only flows

- Supervisor/HA OS (acceptance): Rebuild and restart strictly via Supervisor. All testing is MQTT‑only. Evidence stored under `/config/ha-bb8/**` on HA Host and mirrored to `reports/checkpoints/**` here.
- Standalone dev (local only): Use Python runner or container locally for quick iteration. Not valid for acceptance.

Key acceptance references:
- INT‑HA‑CONTROL harness in `reports/checkpoints/INT-HA-CONTROL/`
- STP4 MQTT roundtrip: `make evidence-stp4`
- STP5 BLE+MQTT attestation: VS Code task “STP5 Supervisor BLE Attestation”

## Environment governance (ADR‑0041)

- `CONFIG_ROOT=/config` is the only HA root. Derive all HA paths from it.
- Keep secrets in `.evidence.env` (never commit). `.env` contains only non‑secret config.
- Inside the add-on container, use MQTT host `core-mosquitto`.
- Validate with `make env-validate`; artifacts land under `reports/checkpoints/ENV-GOV/`.

## Runtime model and imports

- Foreground single process: `run.sh` must exec the target; avoid mixing supervision models.
- Imports: runtime uses `bb8_core.*` (when running from addon/); tests from repo root use `addon.bb8_core.*`.
- Do not mutate `sys.path` in production modules.

## Evidence contract (where to write)

- Only governed harnesses may write under `reports/checkpoints/**`.
- On HA Host, all artifacts must live under `/config/ha-bb8/**` and be mirrored back.
- Include `manifest.sha256` for every checkpoint directory.

## MQTT/Discovery essentials

- Use Paho v2 with correct callback signatures (MQTTv5 preferred, v311 supported).
- Discovery payloads MUST include proper device blocks with both `identifiers` and `connections` (ADR‑0037).
- Standardized command surface: `bb8/cmd/*` (drive, stop, led, power, estop/clear_estop).

## Common pitfalls (quick)

- Forgetting Supervisor rebuild after changing `run.sh` or dependencies.
- Omitting device block fields in discovery (causes HA entity failures).
- Mixing `addon.bb8_core` and `bb8_core` imports in the same run.
- Writing exploratory artifacts under `reports/checkpoints/**` (use `scratch/` instead).

## Useful pointers

- LLM entrypoint: `llms.txt`
- ADR index: `docs/ADR/INDEX.md`
- Acceptance artifacts: `reports/checkpoints/INT-HA-CONTROL/`
- Ops overview: `ops/README.md`
- Evidence helpers: `ops/evidence/README.md`

---

This document complements `.github/instructions/copilot-instructions.md` and should be kept in sync with ADRs and `llms.txt` when files move.
