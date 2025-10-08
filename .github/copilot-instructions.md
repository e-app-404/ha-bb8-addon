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
* **Foreground single-proc (Gate A/B):** `run.sh` must `exec` the target (echo/bridge). Keep conflicting `services.d/*` entries **down**.
* **s6-managed (multi-service):** `run.sh` starts `s6-svscan`; only services **without** `down` run.
* Emit on startup:
  - `RUNTIME_MODEL=foreground|s6`
  - `SERVICE_LIST=[...]` (when s6)
ADR alignment: 0031.

### Data Flow Patterns
- **Config**: `/data/options.json` → environment vars → structured config with provenance logging
- **MQTT**: Commands (`bb8/*/set`) → facade → BLE bridge → device, Status (`bb8/*/state`) published on changes
- **Logging**: Centralized in `logging_setup.py`, structured JSON with auto-redaction of secrets

## Critical Development Practices

### Import & Module Structure (PIE: P4 — Prevent)
* **Runtime imports:** Use `bb8_core.*` when the working dir is `addon/` and entrypoint is `python -m bb8_core.<module>`.
* **Tests (workspace root):** Use `addon.bb8_core.*`. Ensure pytest adds repo root to `PYTHONPATH` (via `pytest.ini`).
* **Do not mix** import styles in the same run.
* **Guardrail:** Do not mutate `sys.path` inside production modules.
* Use `from __future__ import annotations` where helpful; export `__all__` explicitly.

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
* Always mask: `MQTT_PASSWORD`, `HA_TOKEN`, `API_KEY`, any `*_SECRET`.
* Use exact placeholder: `[MASKED]` for diff-friendly evidence.
* Emit a single masked preview on startup:
```json
{"event":"startup_env_preview","MQTT_HOST":"...","MQTT_PORT":1883,"MQTT_USER":"[MASKED]","MQTT_PASSWORD":"[MASKED]"}
```
ADR alignment: 0041.

**Standardized MQTT Lifecycle Events (PIE: I5 — Improve)**
* `mqtt_connect_success`: `{"host":"...","port":1883}`
* `mqtt_subscribed`: `{"topic":"..."}`
* `mqtt_publish`: `{"topic":"...","len":123}`
* `mqtt_disconnect`: `{"reason":"..."}`
Rationale: Faster grepping and evidence parsing.

## Testing & Quality

### Test Organization (addon/tests/)
- **Unit tests**: Mock external dependencies, focus on logic
- **Integration tests**: FakeMQTT via `tools/bleep_run.py` for MQTT seam validation
- **Evidence tests**: Operational validation using `ops/evidence/STP4/collect_stp4.py`

### Quality Gates
```bash
make qa          # Full QA suite: format, lint, types, testcov, security
make testcov     # Pytest with coverage (≥80% threshold)
make evidence-stp4  # End-to-end MQTT roundtrip attestation
```

### Coverage Requirements
- Minimum 80% test coverage enforced
- Use `# pragma: no cover` for unreachable/external integration code
- 200+ tests target for comprehensive validation

### Test Runtime Policy (PIE: I3 — Improve)
* Mark hardware/long BLE tests with `@pytest.mark.slow`.
* Default local runs deselect slow tests: `pytest -q -k 'not slow'`.
* CI gates run full suite; local dev uses fast set for iteration.
* `pytest-xdist` can be used locally for parallel-safe modules.

## Home Assistant Integration

### MQTT Topics & Discovery
- Commands: `{base_topic}/{entity}/set` (e.g., `bb8/power/set`)
- States: `{base_topic}/{entity}/state` (e.g., `bb8/power/state`)  
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

#### Evidence Contract (Governed) (PIE: P2 — Prevent)
* Only **governed harness/tests** may write under `reports/checkpoints/**`.
* Exploratory/ad-hoc scripts must write to `sandbox/` or `tmp/`, **never** to `reports/checkpoints/**`.
* Any startup/config mutation must emit a timestamped backup under `/config/hestia/workspace/archive/**`.
* Include `manifest.sha256` for every checkpoint directory.
ADR alignment: 0008, 0031, 0041.

### Deployment Pipeline (ADR-0008)
```bash
# Verified end-to-end deployment (PREFERRED)
make release-patch    # Version bump + GitHub publish + rsync deploy + HA API restart
make release-minor    # Minor version increment with full pipeline
make release VERSION=1.4.2  # Explicit version with full pipeline

# Manual deployment (current state)  
REMOTE_HOST_ALIAS=home-assistant ops/release/deploy_ha_over_ssh.sh

# Deployment verification
ssh home-assistant 'grep version: /addons/local/beep_boop_bb8/config.yaml'
```

### Configuration Management (ADR-0041)
- **Centralized config**: All settings in `.env` file (auto-sourced by deployment scripts)
- **Required settings**: `HA_URL="http://192.168.0.129:8123"` for HTTP restart functionality
- **Secrets management**: Use `addon/secrets.yaml` (synced to HA system, accessible to SSH user)
- **No hardcoded values**: SSH hosts, paths, API endpoints all configurable via `.env`

## ADR Governance

### Three-Tier Documentation
- `docs/ADR/`: Canonical architectural decisions (ADR-XXXX-slug.md)
- `docs/ADR/architecture/`: Supporting docs and general architecture
- `docs/ADR/architecture/historical/`: Raw evidence and research archive

### Key ADRs
- **ADR-0008**: End-to-end deployment flow with verified pipeline (rsync, Alpine compatibility)
- **ADR-0019**: Workspace folder taxonomy
- **ADR-0031**: Supervisor-only operations & testing protocol  
- **ADR-0032**: MQTT/BLE integration architecture
- **ADR-0034**: HA OS infrastructure knowledge (Alpine v3.22, Docker paths)
- **ADR-0035**: OOM prevention and echo load management
- **ADR-0036**: AI model selection governance (this document's source)
- **ADR-0037**: MQTT discovery device block compliance (critical entity registration fix)
- **ADR-0041**: Centralized environment configuration & accessible secrets management

## Common Pitfalls

### Deployment & Infrastructure
- **File synchronization**: Deployment requires actual file copying (rsync), not just addon restart
- **Alpine packages**: Use `apk add python3 py3-pip python3-dev` NOT `py3-venv` (doesn't exist in Alpine 3.22)
- **Docker paths**: Use `/usr/local/bin/docker` not `/usr/bin/docker` on HA OS
- **Package manager**: Alpine uses `apk`, not `apt-get` - HA Supervisor overrides Dockerfile BUILD_FROM
- **Environment config**: Use centralized `.env` file, ensure `HA_URL` is set for HTTP restart
- **Version sync**: Always use `make release-patch` for consistent versioning across files

### MQTT & Discovery
- **Device blocks**: MQTT discovery MUST have proper `device` blocks with `identifiers` and `connections`
- **Empty device blocks**: `{"device": {}}` causes entity registration failures in Home Assistant
- **MQTT wildcards**: Avoid in production, sanitize all user inputs
- **Topic derivation**: Never hardcode MQTT topics, always derive from config

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

### Model-Specific Guardrails

**GPT-4o mini Constraints:**
- **Scope limitation**: Max 3-file changes per session
- **ADR prohibition**: Cannot create/modify canonical ADRs without explicit override
- **Architecture freeze**: No changes to core service boundaries (bridge_controller, mqtt_dispatcher, facade)
- **Evidence verification**: Must run `make evidence-stp4` for MQTT changes

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
* On new branches or file moves, refresh `tools/index.jsonl` (workspace map) and commit it.
* Agents should read this index first to target changes precisely.
ADR alignment: 0019.

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
* **Tests: fast** — `pytest -q addon/tests -k 'not slow'`
* **QA** — `make qa`
* **Evidence (STP4)** — `make evidence-stp4`
* **Release patch** — `make release-patch`

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
pytest -q addon/tests                    # Run tests
make qa                                   # Full quality suite
```

> Note: local fast cycle is `pytest -q -k 'not slow'`. CI uses full suite for coverage gates.