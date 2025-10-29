# Project Folders Structure Blueprint

Generated: 2025-10-27 (auto-detected)

This blueprint documents the repository’s folder structure, organization principles, and practical conventions to keep code, docs, and operations consistent.

## Initial Auto‑detection

- Detected primary type: Python project with Home Assistant add-on (Supervisor runtime) and extensive operational tooling.
- Key indicators:
  - Python config: `pyproject.toml`, `requirements*.txt`, `pytest.ini`, `ruff.toml`, `mypy.ini`.
  - HA add-on: `addon/Dockerfile`, `addon/config.yaml`, `apparmor.txt`, `build.yaml`, `addon/run.sh`.
  - Documentation/ADRs: `docs/ADR/ADR-*.md`, governance instructions in `.github/instructions/`.
  - CI/QA/evidence: `Makefile`, `ops/**`, `reports/**`.
- Monorepo: No. Single add-on project with supporting ops/docs.
- Microservices: No. Single service (BB‑8 add-on) plus helper scripts.
- Frontend: None detected.

## 1. Structural Overview

- Organization model: layered + feature modules inside `addon/bb8_core` (BLE, MQTT, facade, controller), with repository-level ops/evidence under `ops/` and `reports/`.
- Governance and architecture captured via ADRs in `docs/ADR` with an index tool in `bin/`.
- Testing spans unit tests under `addon/tests` and repository evidence flows under `reports/checkpoints/**` with orchestrators in `ops/`.
- Home Assistant add-on packaging lives entirely under `addon/` and is rebuilt/restarted via Supervisor per ADR‑0031.

## 2. Directory Visualization (Markdown list, depth 3)

- `addon/`
  - `bb8_core/`
    - Core modules: `bridge_controller.py`, `mqtt_dispatcher.py`, `ble_bridge.py`, `ble_gateway.py`, `facade.py`, `logging_setup.py`
    - Utilities/logic: `common.py`, `core.py`, `types.py`, `safety.py`, `telemetry.py`, `lighting.py`
    - Runners/tests/tools: `main.py`, `echo_responder.py`, `mqtt_echo.py`, `tests/`
  - `app/`, `schemas/`, `scripts/`, `tools/`, `tests/`
  - Packaging: `Dockerfile`, `config.yaml`, `run.sh`, `requirements.txt`
- `docs/`
  - `ADR/` (architectural decisions)
  - `meta/`, `ops/`, `deployment-bundle/`, `delta_contracts/`
- `.github/`
  - `instructions/` (governance for agents/tools)
  - `prompts/` (reusable Copilot prompts)
- `ops/`
  - `acceptance/`, `deploy/`, `evidence/`, `qa/`, `env/`, `release/`, `diag/`
- `reports/`
  - `checkpoints/` (evidence), `governance/`, `qa/`, `analysis/`
- Root support
  - Build/tooling: `Makefile`, `pyproject.toml`, `pytest.ini`, `ruff.toml`, `mypy.ini`
  - Configs: `.env` (non‑secrets), `.evidence.env` (local secrets, ignored), `.dockerignore`

Excluded generated folders in visualization: `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `htmlcov/`.

## 3. Key Directory Analysis

### Python project structure (detected)

- Solution layout
  - Runtime code lives under `addon/bb8_core` and is executed inside the HA add-on container.
  - Repository-level automation lives under `ops/` (scripts) and `reports/` (artifacts/evidence).
- Layering
  - Controller/entry: `bridge_controller.py` (orchestrator), `main.py` (entry), `echo_responder.py` (aux runner).
  - MQTT layer: `mqtt_dispatcher.py`, `mqtt_helpers.py`, `mqtt_probe.py`.
  - BLE layer: `ble_gateway.py`, `ble_bridge.py`, `ble_link.py`, `ble_session.py`, `ble_utils.py`.
  - Facade: `facade.py` mediates MQTT ↔ BLE with safety/rate‑limits.
  - Safety/telemetry/logging: `safety.py`, `telemetry.py`, `logging_setup.py`.
- Configuration
  - Add-on config source: `/data/options.json` → `addon/bb8_core/addon_config.py`.
  - Environment governance documented in `docs/ENV_GOVERNANCE.md` and `.github/instructions/*`.
- Tests
  - Unit/integration under `addon/tests/`; fast local runs via `pytest -q addon/tests -k 'not slow'`.
  - Evidence and acceptance flows under `reports/checkpoints/**` orchestrated by `ops/`.

## 4. File Placement Patterns

- Configuration files
  - Add-on packaging: `addon/config.yaml`, `addon/Dockerfile`, `apparmor.txt`, `build.yaml`.
  - Python toolchain: `pyproject.toml`, `requirements*.txt`, `pytest.ini`, `ruff.toml`, `mypy.ini`.
- Domain models and types
  - Core types under `addon/bb8_core/types.py`, `core_types.py`.
- Business logic
  - Feature logic under `addon/bb8_core/*` grouped by responsibility (BLE, MQTT, facade, controller).
- Tests
  - `addon/tests/` for unit/integration; repo evidence scripts under `reports/checkpoints/**`.
- Documentation
  - ADRs in `docs/ADR`; governance and ops docs under `docs/meta/`, `docs/ops/`.

## 5. Naming and Organization Conventions

- Python modules: snake_case filenames; classes in PascalCase; functions in snake_case with type hints.
- ADRs: `docs/ADR/ADR-XXXX-slug.md` with YAML frontmatter including `status`, `date`, `title`, and `decision`.
- Ops scripts: grouped under `ops/<domain>/...` with clear verb‑noun names and environment governance.
- Reports: evidence under `reports/checkpoints/<GATE>/<ts>/`; governance indices under `reports/governance/`.

## 6. Navigation and Development Workflow

- Entry points
  - Runtime: `addon/bb8_core/main.py` (or module runners), add-on foreground exec via `addon/run.sh`.
  - Orchestrator: `addon/bb8_core/bridge_controller.py`.
- Common tasks
  - Add feature logic in `addon/bb8_core/` by layer (MQTT, BLE, facade, controller).
  - Add tests under `addon/tests/` and evidence scripts under `reports/checkpoints/**`.
  - Update ADRs in `docs/ADR`; regenerate governance index via `bin/adr_index.py`.
- Dependencies
  - Use `requirements.txt` in `addon/` for container; dev dependencies in repo `requirements-dev.txt`.
  - Respect Supervisor-only deployment per ADR‑0031.

## 7. Build and Output Organization

- Build/pipeline
  - Local QA via `make qa`; tests via `pytest`; evidence via `make evidence-stp4`.
  - Add-on build/restart through Home Assistant Supervisor (UI or `ha` CLI).
- Outputs
  - Test coverage: `coverage.json`, `htmlcov/`.
  - Evidence: `reports/checkpoints/**`, governance: `reports/governance/**`.

## 8. Technology‑Specific Organization (Python)

- Project config: `pyproject.toml` centralizes tooling; ruff/mypy/pytest configs at repo/addon levels.
- Packaging for runtime inside `addon/` with `Dockerfile` and `run.sh` enforcing foreground execution.
- Structured JSON logging centralized in `logging_setup.py` with secret redaction.

## 9. Extension and Evolution

- Extension points
  - New MQTT commands: extend `mqtt_dispatcher.py` and implement in `facade.py`/BLE layers.
  - New diagnostics/evidence: add scripts under `ops/evidence/` and outputs under `reports/checkpoints/`.
- Scalability
  - Keep module boundaries (BLE, MQTT, facade) and avoid mixing supervision models.
- Refactoring patterns
  - Prefer small, typed helpers; adhere to centralized logging and configuration loaders.

## 10. Structure Enforcement

- Validation
  - Governance: ADR index via `bin/adr_index.py`; CI gates for coverage (dynamic threshold), lint/type checks.
  - ENV governance checks under `ops/env/` and `.github/instructions/env-governance.instructions.md`.
- Documentation practices
  - ADR updates in `docs/ADR` with decisions auto-filled when missing.
  - Evidence mirrored as per workspace memory under `reports/checkpoints/**`.

---
Maintenance: Update this blueprint when adding major folders, changing add-on packaging, or modifying ADR/testing workflows. Include date and rationale for structural changes.
