---
title: "ADR-0019: Workspace folder taxonomy and assignation rules"
date: 2025-09-14
status: Accepted
author:
  - Evert Appels
  - Github Copilot
related:
  - ADR-0001
  - ADR-0004
  - ADR-0008
  - ADR-0009
  - ADR-0017
  - ADR-0018
supersedes: []
last_updated: 2025-09-14
references:
  - check_root_tools.sh
  - check_root_services_d.sh
  - check_bare_bb8_core_imports.sh
  - run_guardrails.sh
---

# ADR-0019: Workspace folder taxonomy and assignation rules

## Table of Contents
1. Context
2. Decision
3. Canonical roots
4. Assignation Rules (programmatic)
5. Enforcement
6. Consequences
7. Token Block

## 1. Context
This project maintains a canonical add-on code root at `addon/`. Prior drift produced duplicate or misplaced content at the repository root (e.g., `bb8_core/`, `services.d/`, and `tools/`). This ADR defines categorical purposes and programmatic assignation rules per folder to prevent drift.

## 2. Decision

### Canonical roots
- `addon/`: **Runtime code for the Home Assistant add-on**
  - `addon/bb8_core/` — Python package for runtime code only.
  - `addon/services.d/` — s6-overlay services shipped in the container (`<service>/run`, optional `<service>/log/run`).
  - `addon/tests/` — tests for the runtime package.
  - `addon/tools/` — runtime utilities bundled into the container (may be invoked by services or operators).
- `ops/`: **Operations, QA, audits, release tooling**
  - Subfolders: `ops/audit`, `ops/diagnostics`, `ops/qa`, `ops/release`, `ops/evidence`, `ops/guardrails`, etc.
  - `ops/tools/` — operator-facing tools (docker, git, CI helpers, data audits); **never imported at runtime**.
- `scripts/`: **Repo developer scripts** (small glue, bootstrap, repo maintenance; no runtime semantics).
- `reports/`: **Generated artifacts only** (logs, coverage, audits, evidence). No source files.
- `docs/`: **Documentation** (ADR, guides, prompts, patches, legacy).
- `services.d/` at repo root: **FORBIDDEN**. All services must live under `addon/services.d/`.
- `tools/` at repo root: **Discouraged**. Code tools must be rehomed:
  - add-on utilities → `addon/tools/`
  - ops tooling → `ops/tools/`
  - otherwise → `scripts/`

## 3. Assignation Rules (programmatic)
- Python files importing `addon.bb8_core` → **`addon/`** (runtime or add-on bundled tools).
- Python files importing docker, paho, git, HA CLI, cloud SDKs, or performing audits/releases → **`ops/`**.
- Python files with CLI `if __name__ == "__main__"` but no runtime imports:
  - operational CLIs → `ops/tools/`
  - developer convenience → `scripts/`
- s6 services (`<name>/run` [+ `log/run`]) → **`addon/services.d/`** (executable).
- Generated outputs, logs, coverage, dumps → **`reports/`** only.

## 4. Enforcement
- Pre-commit hook rejects:
  - root `services.d/`
  - bare `bb8_core` imports (must be `addon.bb8_core`)
  - Python under `tools/` at repo root (must be rehomed)
- CI job runs repo-shape audit and fails on violations.

## 5. Consequences
- No duplicate code trees.
- Clear separation of runtime vs ops/dev artifacts.
- Automated guardrails prevent regression.

## 6. Token Block
```yaml
TOKEN_BLOCK:
  accepted:
    - WORKSPACE_TAXONOMY_OK
    - FOLDER_ASSIGNATION_OK
    - TOKEN_BLOCK_OK
  requires:
    - ADR_SCHEMA_V1
    - ADR_FORMAT_OK
    - ADR_GENERATION_OK
    - ADR_REDACTION_OK
  drift:
    - DRIFT: root_services_d_present
    - DRIFT: bare_bb8_core_import
    - DRIFT: python_tools_root
    - DRIFT: folder_taxonomy_violation
```
