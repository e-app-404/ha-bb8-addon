### Supervisor‑First Deployment (ADR‑0031, ADR‑0024)
> **Project override:** Supervisor‑only deployment. Do **not** use rsync/git on the HA host for operational deploys.
```bash
ha addons reload
ha addons rebuild local_beep_boop_bb8   # if Dockerfile/deps changed
ha addons restart local_beep_boop_bb8

# Verify
ha addons info local_beep_boop_bb8 | grep 'state: started'
```
### Configuration Management (ADR‑0041, ADR‑0024)

- **Centralized config**: Only **non‑secret** settings in `.env`; **secrets in `.evidence.env`** (never commit).
- **CONFIG_ROOT** is `/config`; derive all HA paths from it. BB‑8 evidence mirrors to `/config/ha-bb8/**`.
### Operational Guardrails (BB‑8)

- **No host utility scripts** outside `/config/hestia/tools`.
- **Runtime writes** inside the container go under `/data/**`; host evidence mirrors under `/config/ha-bb8/**`.
### Governance Overrides (BB‑8)

- **Supervisor‑only execution**: invoke and verify the sequence with the add‑on running under HA Supervisor; do not depend on host scripts.
```json
### Environment Variable Governance (ADR-0024 Companion)

**Status:** Draft
**Created:** 2025-10-07
**ADR Alignment:** [ADR-0024 Canonical Config Path](../docs/ADR/ADR-0024-canonical-config-path.md)
**Scope:** HA-BB8 Add-on Repository `.env` standardization
```
---
applyTo: '**'
---
# AI Coding Agent Instructions: HA-BB8 Add-on (Governed, PIE-Optimized)

## Project Overview

Home Assistant add-on for controlling Sphero BB-8 via BLE and MQTT. This codebase follows a layered architecture with comprehensive ADR governance, extensive testing, and operational evidence collection. Uses Alpine Linux v3.22 runtime with centralized configuration management and verified deployment pipeline.

## Architecture & Service Boundaries

### Core Components (addon/bb8_core/)

- **bridge_controller.py**: Main orchestrator - resolves BB-8 MAC, initializes BLE gateway, starts MQTT dispatcher
- **mqtt_dispatcher.py**: MQTT broker connection, topic subscription/publishing, HA discovery management
- **ble_bridge.py**: BLE device interface, Spherov2 SDK integration, command/response handling
- **ble_gateway.py**: Low-level BLE scanning and connection management
- **facade.py**: BB8Facade - unified interface between MQTT dispatcher and BLE bridge
- **addon_config.py**: Configuration loader with provenance (options.json → env → YAML fallback)

### Service Flow

```
run.sh → bridge_controller.py → start_bridge_controller() →
  resolve_bb8_mac() → BleGateway → BLEBridge → BB8Facade →
  mqtt_dispatcher.start_mqtt_dispatcher()
```

### Runtime Model Policy (PIE: P3 — Prevent)

**Do not mix supervision models.**
**Chosen model for production:** **Foreground single-proc**.
`run.sh` must **exec** the target (echo/bridge) and remain in the foreground. Keep any `services.d/*` entries **down** unless ADR-governed migration to s6 is explicitly approved.
Emit on startup:

- `RUNTIME_MODEL=foreground`
- `SERVICE_LIST=[]`
  ADR alignment: 0031.

### Data Flow Patterns

- **Config**: `/data/options.json` → environment vars → structured config with provenance logging
- **MQTT**: Commands (`bb8/*/set`) → facade → BLE bridge → device, Status (`bb8/*/state`) published on changes
- **Logging**: Centralized in `logging_setup.py`, structured JSON with auto-redaction of secrets

## Critical Development Practices

### Import & Module Structure (PIE: P4 — Prevent)

- **Runtime imports:** Use `bb8_core.*` when the working dir is `addon/` and entrypoint is `python -m bb8_core.<module>`.
- **Tests (workspace root):** Use `addon.bb8_core.*`. Ensure pytest adds repo root to `PYTHONPATH` (via `pytest.ini`).
- **Do not mix** import styles in the same run.
- **Guardrail:** Do not mutate `sys.path` inside production modules.
- Use `from __future__ import annotations` where helpful; export `__all__` explicitly.

### MQTT Client Initialization (PAHO v2) (PIE: P1 — Prevent)

Use the correct API rather than suppressing warnings.

```python
import paho.mqtt.client as mqtt
# Prefer MQTTv5 if broker supports it; otherwise use MQTTv311.
client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    protocol=mqtt.MQTTv5  # or mqtt.MQTTv311
)
def on_connect(client, userdata, flags, reasonCode, properties=None):
    client.subscribe(f"{base}/echo/cmd")
client.on_connect = on_connect
```

If using MQTTv311, adapt the signature:

```python
def on_connect(client, userdata, flags, rc):
    client.subscribe(f"{base}/echo/cmd")
```

ADR alignment: 0032, 0035.

### Configuration System

```python
from .addon_config import load_config
cfg, src = load_config()  # Returns (config_dict, source_path)
```

- Config provenance tracked and logged
- Environment variables auto-exported by run.sh
- No hardcoded MQTT topics/clients - always derive from config
- MQTT host inside container must use the Supervisor internal hostname **`core-mosquitto`**.

### Logging Standards

```python
from .logging_setup import logger
logger.info({"event": "structured_event", "key": "value"})
```

- **Only** use the centralized logger from `logging_setup.py`
- Structured JSON logging throughout
- Auto-redaction of secrets (password, token, apikey patterns)
- NO print statements or `logging.basicConfig()` elsewhere

**Masked Keys (PIE: P5 — Prevent)**

- Always mask: `MQTT_PASSWORD`, `HA_TOKEN`, `API_KEY`, any `*_SECRET`.
- Use exact placeholder: `[MASKED]` for diff-friendly evidence.
- Emit a single masked preview on startup:

```json
{
  "event": "startup_env_preview",
  "MQTT_HOST": "...",
  "MQTT_PORT": 1883,
  "MQTT_USER": "[MASKED]",
  "MQTT_PASSWORD": "[MASKED]"
}
```

ADR alignment: 0041.

**Standardized MQTT Lifecycle Events (PIE: I5 — Improve)**

- `mqtt_connect_success`: `{"host":"...","port":1883}`
- `mqtt_subscribed`: `{"topic":"..."}`
- `mqtt_publish`: `{"topic":"...","len":123}`
- `mqtt_disconnect`: `{"reason":"..."}`
  Rationale: Faster grepping and evidence parsing.

### Motion Safety & Emergency Stop (PIE: P6 — Prevent)

- Implement and honor **rate limits**, **max drive duration**, and **speed caps** in the motion path.
- Provide **emergency stop** topic (`bb8/cmd/estop`) that latches until cleared via (`bb8/cmd/clear_estop`).
- Telemetry must publish `estop` state under `bb8/status/telemetry`.

## Testing & Quality

### Test Organization (addon/tests/)

- **Unit tests**: Mock external dependencies, focus on logic
- **Integration tests**: FakeMQTT via `tools/bleep_run.py` for MQTT seam validation
- **Evidence tests**: Operational validation using `ops/evidence/STP4/collect_stp4.py`

### Quality Gates

```bash
make qa             # Full QA suite: format, lint, types, tests, security
make testcov        # Pytest with coverage (threshold comes from .coveragerc)
make evidence-stp4  # End-to-end MQTT roundtrip attestation (governed)
make env-validate   # ENV governance conformance check and artifact write
```

### Coverage Policy (Honest, Dynamic)

- **Feature branches**: threshold **50%** (current `.coveragerc`)
- **Main branch / PR to main**: CI **auto-applies 60%** by copying `.coveragerc.pr60` → `.coveragerc`
- Keep omissions minimal (justify inline); prefer integration-meaningful tests over synthetic inflation.

### Test Runtime Policy (PIE: I3 — Improve)

- Mark hardware/long BLE tests with `@pytest.mark.slow`.
- Default local runs deselect slow tests: `pytest -q -k 'not slow'`.
- CI gates run full suite; local dev uses fast set for iteration.
- `pytest-xdist` can be used locally for parallel-safe modules.

## Home Assistant Integration

### MQTT Topics & Discovery

- **Command surface (standardized):** `bb8/cmd/*`
  - `bb8/cmd/drive` → `{"speed":0..255,"heading":0..359,"ms":0..5000}`
  - `bb8/cmd/stop` → `{}`
  - `bb8/cmd/led` → `{"r":0..255,"g":0..255,"b":0..255}` (presets allowed)
  - `bb8/cmd/power` → `{"action":"wake|sleep"}`
  - `bb8/cmd/estop` / `bb8/cmd/clear_estop`
- **Acknowledgements & errors:** `bb8/ack/*` with correlation ids.
- **States/telemetry:** `{base_topic}/status`, `{base_topic}/status/telemetry`
- Discovery: Auto-published to `homeassistant/{component}/{device_id}/{entity}/config`
- Status: `{base_topic}/status` (online/offline with LWT)

### Discovery Entities

- `power` (switch): ON/OFF control
- `presence` (binary_sensor): BLE presence detection
- `rssi` (sensor): Signal strength
- `led` (light): RGB color control
- `drive`, `heading`, `speed`, `stop`, `sleep` (various types)

### MQTT Discovery Device Block Compliance (ADR-0037)

**CRITICAL**: All discovery messages MUST include proper device blocks:

```json
{
  "device": {
    "identifiers": ["bb8_S33_BB84_LE"],
    "connections": [["mac", "ED:ED:87:D7:27:50"]],
    "name": "BB-8 (S33 BB84 LE)",
    "manufacturer": "Sphero",
    "model": "BB-8"
  }
}
```

- **Never use empty device blocks**: `{"device": {}}` causes entity registration failure
- **Always include identifiers AND connections**: Both required for proper device registry
- **Derive from config**: Use `bb8_mac` and `bb8_name` from addon configuration

## Operational Patterns

### Environment Detection

- **HA OS**: Alpine Linux v3.22, Docker at `/usr/local/bin/docker`
- **BLE Tools**: Use `bluez-deprecated` package, dual adapters (hci0/hci1)
- **Paths**: Logs to `/data/reports/`, config from `/data/options.json`

### Evidence Collection

- Runtime telemetry via `EvidenceRecorder` (150 lines max)
- Diagnostics via `ops/diag/collect_ha_bb8_diagnostics.sh`
- Attestation via STP4 protocol for MQTT roundtrip validation

> Extended: STP5 Supervisor BLE Attestation

- Use the STP5 runbook to exercise BLE + MQTT under Supervisor control.
- Workspace task: “STP5 Supervisor BLE Attestation” (see VS Code tasks above) invokes `scripts/stp5_supervisor_ble_attest.sh` against your HA host.
- Artifacts should be mirrored under `reports/checkpoints/**` per the Evidence Contract.

#### HA Host validation & path confinement (B5+)

- All artifacts written on the HA Host must be confined under the base directory: `/config/ha-bb8`.
- Standard B5 validation run via SSH helper: `ops/ha-host/run_b5_via_ssh.sh [<host-alias>]`.
  - Behavior: SSH into HA Host, locate the BB‑8 add‑on container, execute the E2E sequence (wake → preset → drive → stop → sleep) and echo probe inside the container, write evidence to `/config/ha-bb8/checkpoints/BB8-FUNC/<UTC_TS>/`, and generate a `manifest.sha256` in that folder.
  - After completion, artifacts are copied back to the local repo under `reports/checkpoints/BB8-FUNC/ssh_b5_<UTC_TS>/` for commit.
- Never write outside `/config/ha-bb8` on HA Host. If additional subfolders are needed, place them beneath this base directory.

Quick runbook (operator):

1) Ensure the BB‑8 add‑on container is running on HA Host (name/image contains `bb8`).
2) From the repo root, run:
  - `chmod +x ops/ha-host/run_b5_via_ssh.sh`
  - `bash ops/ha-host/run_b5_via_ssh.sh homeassistant`
3) Confirm local capture under `reports/checkpoints/BB8-FUNC/ssh_b5_<UTC_TS>/` contains:
  - `b5_e2e_demo.log`, `b5_summary.md`, and `manifest.sha256`.
4) Commit evidence and include in PR if required by the gate.

#### Evidence Contract (Governed) (PIE: P2 — Prevent)

- Only **governed harness/tests** may write under `reports/checkpoints/**`.
- Exploratory/ad-hoc scripts must write to `sandbox/` or `tmp/`, **never** to `reports/checkpoints/**`.
- Any startup/config mutation must emit a timestamped backup under `/config/hestia/workspace/archive/**`.
- Include `manifest.sha256` for every checkpoint directory.
  ADR alignment: 0008, 0031, 0041.

### Supervisor‑First Deployment (ADR‑0031, ADR‑0024) +
> **Project override:** Supervisor‑only deployment. Do **not** use rsync/git on the HA host for operational deploys. +
```bash
# From HA host shell (or Studio Code Server terminal)
# Rebuild + restart the local BB‑8 add‑on strictly via Supervisor
ha addons reload
ha addons rebuild local_beep_boop_bb8   # if Dockerfile/deps changed
ha addons restart local_beep_boop_bb8

# Verify
ha addons info local_beep_boop_bb8 | grep 'state: started'
```

### Configuration Management (ADR‑0041, ADR‑0024)

- **Centralized config**: Only **non‑secret** settings in `.env`; **secrets in `.evidence.env`** (never commit).
- **CONFIG_ROOT** is `/config`; derive all HA paths from it. BB‑8 evidence mirrors to `/config/ha-bb8/**`.
- **Broker in‑container**: `core-mosquitto`. Do not hardcode external IPs.
- **No hardcoded values**: Keep hosts/paths in env; avoid script‑embedded literals.

### Operational Guardrails (BB‑8)

- **No host utility scripts** outside `/config/hestia/tools`.
- **Runtime writes** inside the container go under `/data/**`; host evidence mirrors under `/config/ha-bb8/**`.
- **Testing surface** is **MQTT only** (`bb8/cmd/*`, `bb8/ack/*`, `bb8/status/*`).

## ADR Governance

### Three-Tier Documentation

- `docs/ADR/`: Canonical architectural decisions (ADR-XXXX-slug.md)
- `docs/ADR/architecture/`: Supporting docs and general architecture
- `docs/ADR/architecture/historical/`: Raw evidence and research archive

### Key ADRs

- **ADR-0008**: End-to-end deployment flow (reference only) — **override by ADR‑0031 Supervisor‑first**
- **ADR-0019**: Workspace folder taxonomy
- **ADR-0024**: Canonical config path management ( + expansion doc `ENV_GOVERNANCE`)
- **ADR-0031**: Supervisor-only operations & testing protocol
- **ADR-0032**: MQTT/BLE integration architecture
- **ADR-0034**: HA OS infrastructure knowledge (Alpine v3.22, Docker paths)
- **ADR-0035**: OOM prevention and echo load management
- **ADR-0036**: AI model selection governance (this document's source)
- **ADR-0037**: MQTT discovery device block compliance (critical entity registration fix)
- **ADR-0041**: Centralized environment configuration & accessible secrets management

## Common Pitfalls

**Deployment & Infrastructure**

- **Rebuilds**: Changes to `run.sh` or Python dependencies **require a full container rebuild** (use the release pipeline).
- **File synchronization**: Plain rsync without rebuild will not update the running image.
- **Alpine packages**: Use `apk add python3 py3-pip python3-dev` (note: `py3-venv` is not a separate package on Alpine 3.22; `python3 -m venv` is available).
- **Docker paths**: Use `/usr/local/bin/docker` not `/usr/bin/docker` on HA OS
- **Package manager**: Alpine uses `apk`, not `apt-get` - HA Supervisor overrides Dockerfile BUILD_FROM
- **Environment config**: Use centralized `.env` file, ensure `HA_URL` is set for HTTP restart
- **Version sync**: Always use `make release-patch` for consistent versioning across files

**MQTT & Discovery**

- **Device blocks**: MQTT discovery MUST have proper `device` blocks with `identifiers` and `connections`
- **Empty device blocks**: `{"device": {}}` causes entity registration failures in Home Assistant
- **MQTT wildcards**: Avoid in production; sanitize all user inputs.
- **Topic derivation**: Never hardcode topics; always derive from config.
- **Broker address in-container**: use **`core-mosquitto`**.

### Development & Testing

- **BLE tools**: Install `bluez-deprecated`, standard `bluez-utils` insufficient
- **Logging**: Never use multiple file handlers, centralize in `logging_setup.py`
- **Motion tests**: Skip unless `ALLOW_MOTION_TESTS=1` environment variable set
- **Import structure**: Use `addon.bb8_core` in tests that run from workspace root level, `bb8_core` for runtime from addon directory

## AI Model Selection & Guardrails

### Model-Specific Capabilities

**GPT-4o mini: Optimal for**

- **Rapid iteration**: Quick code reviews, small patches, documentation updates
- **Pattern recognition**: Identifying code violations, import issues, formatting problems
- **Parallel processing**: Multiple file edits, batch operations, qa pipeline fixes
- **Structured output**: JSON logging patterns, configuration generation, test data
- **Tool orchestration**: Complex multi-step operations with tool chaining

**Claude Sonnet 3.5: Optimal for**

- **Deep analysis**: Architectural decision making, ADR authoring, system design
- **Code quality**: Complex refactoring, type safety improvements, test architecture
- **Long-context reasoning**: Cross-file dependencies, integration patterns, workflow design
- **Documentation**: Technical writing, comprehensive explanations, user guides
- **Problem solving**: Debugging complex issues, root cause analysis, solution design

### Dynamic Model Switching Guidelines

**Use GPT-4o mini when:**

```bash
# Quick fixes and maintenance
make qa                    # QA pipeline failures
make testcov              # Coverage improvements
make evidence-stp4        # Evidence collection issues
```

**Use Claude Sonnet 3.5 when:**

- Creating/updating ADRs in `docs/ADR/`
- Architectural changes affecting multiple components
- Complex debugging across BLE/MQTT/HA integration
- Comprehensive codebase analysis and refactoring
- Documentation requiring deep technical understanding

### Model-Specific Guardrails (aligned to current governance)

**GPT-4o mini Constraints:**

- **Scope limitation**: Max 3-file changes per session.
- **ADR prohibition**: Cannot create/modify canonical ADRs without explicit override.
- **Architecture freeze**: No changes to core service boundaries (bridge_controller, mqtt_dispatcher, facade).
- **Evidence verification**: Run `make evidence-stp4` for MQTT changes; store artifacts under `reports/checkpoints/**` per Evidence Contract.

**Claude Sonnet 3.5 Constraints:**

- **ADR governance**: Must follow ADR-0009 formatting requirements strictly
- **Token validation**: All ADRs must include proper TOKEN_BLOCK sections
- **Cross-reference validation**: Must verify ADR relationships and supersession chains
- **Evidence integration**: Must incorporate operational evidence from STP4/diagnostics

### Context Switching Protocol

**When switching between models:**

1. **State preservation**: Document current progress in structured format
2. **Context handoff**: Provide architectural context and current milestone status
3. **Tool state**: Preserve evidence collection state and test results
4. **ADR continuity**: Reference relevant ADRs and maintain governance compliance

**Handoff template:**

```
CONTEXT_HANDOFF:
  current_milestone: <Phase 1/2/3>
  model_from: <previous model>
  model_to: <target model>
  progress_state: <current work status>
  key_files: [<list of modified files>]
  test_status: <qa/coverage results>
  adr_context: [<relevant ADR references>]
  next_actions: [<prioritized tasks>]
```

**Workspace Map Refresh (PIE: E2 — Extend)**

- On new branches or file moves, refresh `tools/index.jsonl` (workspace map) and commit it.
- Agents should read this index first to target changes precisely.
  ADR alignment: 0019.

**LLM Entrypoint (llms.txt)**

- The repository root contains `llms.txt` (llmstxt.org format) to guide LLM navigation.
- Prefer consulting `llms.txt` first for key docs (README, ADRs), core runtime modules, config/build files, and evidence harness locations.
- Keep links in `llms.txt` current when moving files that affect onboarding or governance.

## Editing Protocol for the AI Agent (PIE: I4 — Improve)

1. **PLAN**: List files to touch, risks, expected artifacts.
2. **DIFF**: Produce unified diffs; do not modify ADRs without explicit approval.
3. **RUN**: Use governed commands (`make qa`, harness tests). No ad-hoc writes to `reports/checkpoints/**`.
4. **EVIDENCE**: Attach logs and updated `manifest.sha256`. Stop on failure and record it.
   ADR alignment: 0009, 0031.

## VSCode Profile (recommended) (PIE: I2 — Improve)

Create `.vscode/settings.json`, `.vscode/tasks.json`, and `.vscode/extensions.json` (see repo files).
Rationale: Fewer editor-induced errors; faster QA/deploy loops.

## Workspace Hygiene (PIE: I1 — Improve)

Add a `.dockerignore` to speed builds and avoid shipping dev artifacts (see repo file).
ADR alignment: 0008.

## Optional: Devcontainer (local dev only) (PIE: E1 — Extend)

Provide a devcontainer for local lint/type/test only. **Do not** use it for Supervisor-governed operational tests (ADR-0031).

## Command Palette Cheatsheet (PIE: E3 — Extend)

- **Tests: fast** — `pytest -q addon/tests -k 'not slow'`
- **QA** — `make qa`
- **Evidence (STP4)** — `make evidence-stp4`
- **Release patch** — `make release-patch`

### VS Code tasks (wired in this workspace)

- HA: Deploy over SSH — runs `ops/release/deploy_ha_over_ssh.sh`
- STP5 Supervisor BLE Attestation — executes `scripts/stp5_supervisor_ble_attest.sh` with env (HOST/PORT/USER/PASS/BASE/REQUIRE_BLE)
- Env: validate — `make env-validate` (ENV governance check and artifact write)
- HA: Restart add-on — `make ha-restart` via HA Core API/Supervisor proxy
- Tests: fast — `pytest -q addon/tests -k 'not slow'`
- Evidence: STP4 — `make evidence-stp4`
- QA: make qa — `make qa`

### Common Anti-Patterns by Model

**GPT-4o mini Anti-Patterns:**

- Creating ADRs without proper YAML front-matter and TOKEN_BLOCK
- Making architectural decisions without evidence collection
- Batch changes that break test coverage thresholds
- Import violations (`bb8_core` instead of `addon.bb8_core`)

**Claude Sonnet 3.5 Anti-Patterns:**

- Over-engineering simple fixes that GPT-4o mini could handle
- Creating verbose documentation when concise patterns exist
- Analysis paralysis on well-established patterns in the codebase
- Ignoring existing guardrails in favor of "ideal" solutions

## Quick Development Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r addon/requirements.txt -r addon/requirements-dev.txt
pytest -q addon/tests -k 'not slow'      # Fast local cycle
make qa                                  # Full quality suite
```

> CI enforces the active threshold from `.coveragerc`; PRs to `main` auto-apply `.coveragerc.pr60` to restore the 60% gate.
