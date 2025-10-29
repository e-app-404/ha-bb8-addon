---
id: ADR-0019
title: Workspace folder taxonomy and assignation rules
date: 2025-09-14
status: Accepted
decision: "### Canonical roots - addon/: **Runtime code for the Home Assistant add-on**\
  \ - addon/bb8_core/ \u2014 Python package for runtime code only. - addon/services.d/\
  \ \u2014 s6-overlay services shipped in the container (<service>/run, optional <service>/log/run)."
author:
- Evert Appels
- Github Copilot GPT 5 mini
related:
- ADR-0001
- ADR-0004
- ADR-0008
- ADR-0009
- ADR-0017
- ADR-0018
last_updated: 2025-10-07
tags:
- workspace
- organization
- taxonomy
- folder structure
- ADR
- layout
- archive
- logs
- reports
supersedes: []
---

# ADR-0019: Workspace folder taxonomy and assignation rules

## Table of Contents
1. [Context](#1-context)
2. [Decision](#2-decision)
3. [Assignation Rules (programmatic)](#3-assignation-rules-programmatic)
4. [Enforcement](#4-enforcement)
5. [Consequences](#5-consequences)
6. [Addendum A: Time-Based Log Organization Pattern (2025-10-07)](#addendum-a-time-based-log-organization-pattern-2025-10-07)
7. [Token Block](#6-token-block)

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
- `reports/`: **Important documentation for long-term retention** (checkpoints, governance docs, development plans). Git-tracked selective content.
- `logs/`: **Temporary outputs and automated artifacts** (diagnostic dumps, receipts, evidence collection). Git-ignored completely.
- `docs/`: **Documentation** (ADR, guides, prompts, patches, legacy).
- `services.d/` at repo root: **FORBIDDEN**. All services must live under `addon/services.d/`.
- `tools/` at repo root: **Discouraged**. Code tools must be rehomed:
  - add-on utilities → `addon/tools/`
  - ops tooling → `ops/tools/`
  - otherwise → `scripts/`

## 3. Assignation Rules (programmatic)
- **ADR documents (canonical)** → **`docs/ADR/`** ONLY (final, approved architectural decisions).
  - Format: `docs/ADR/ADR-XXXX-<slug>.md`
  - All ADRs must comply with ADR-0009 formatting and governance standards
  - These are the "source of truth" architectural decisions
- **Architecture supporting documents** → **`docs/ADR/architecture/`** (general architecture, structure, plans).
  - Research that informs ADR development
  - Non-ADR architectural documentation
  - Design materials and architectural analysis
- **Research archive and evidence** → **`docs/ADR/architecture/historical/`** (preserved for validation/reference).
  - Raw research findings and operational evidence
  - Historical data that informed ADR write-ups
  - Reconnaissance responses, session transcripts, operational logs
  - Source materials for future validation and ADR updates
- Python files importing `addon.bb8_core` → **`addon/`** (runtime or add-on bundled tools).
- Python files importing docker, paho, git, HA CLI, cloud SDKs, or performing audits/releases → **`ops/`**.
- Python files with CLI `if __name__ == "__main__"` but no runtime imports:
  - operational CLIs → `ops/tools/`
  - developer convenience → `scripts/`
- s6 services (`<name>/run` [+ `log/run`]) → **`addon/services.d/`** (executable).
- Important documentation for retention (checkpoints, governance) → **`reports/`** (git-tracked).
- Temporary outputs (diagnostic dumps, receipts, evidence, logs) → **`logs/`** (git-ignored).
- Coverage files and addon-specific test config → **`addon/`** (`.coverage*`, `pytest.ini`, `pyproject.toml`).

## 4. Enforcement
- Pre-commit hook rejects:
  - root `services.d/`
  - bare `bb8_core` imports (must be `addon.bb8_core`)
  - Python under `tools/` at repo root (must be rehomed)
  - **ADR documents outside canonical location** (canonical ADRs must be directly in `docs/ADR/`)
  - **ADRs without proper ADR-0009 formatting** (YAML front-matter, TOKEN_BLOCK required)
- CI job runs repo-shape audit and fails on violations.
- Three-tier ADR structure enforced: canonical (`docs/ADR/`), supporting docs (`docs/ADR/architecture/`), historical archive (`docs/ADR/architecture/historical/`).

## 5. Consequences
- No duplicate code trees.
- Clear separation of runtime vs ops/dev artifacts.
- Automated guardrails prevent regression.

## Addendum A: Time-Based Log Organization Pattern (2025-10-07)

### Context
During Gate A INT-HA-CONTROL operations, the workspace accumulated significant operational artifacts in checkpoint directories and root locations. The original taxonomy provided general guidance for logs/ vs reports/ separation but lacked specific organizational patterns for temporal log management and topic-based archival.

### Enhanced Organization Pattern

**Implemented Structure:**
```
logs/{ISOWEEK}/{topic}/{$TS-logtitle}
reports/{topic}/{meaningful-report-title}
```

**ISO Week-Based Log Archival (`logs/`):**
```
logs/2025-W41/                    # ISO week format for temporal organization
├── int-ha-control/               # Topic: INT-HA-CONTROL operational logs
│   ├── 20241007_030000-addon_restart.log
│   ├── 20241007_030000-mqtt_roundtrip.log
│   ├── Gate-A-Echo-Unblock-Harness.sh
│   └── discovery_ownership_audit.py
├── coverage/                     # Topic: Test coverage measurement
│   ├── coverage.json
│   └── coverage_final_80.json
├── deployment/                   # Topic: Deployment operations
│   ├── 20241007_030000-deploy_receipt.txt
│   └── 20241007_030000-publish_receipt.txt
├── diagnostics/                  # Topic: System diagnostics
│   └── ha_bb8_diagnostics_*.tar.gz
├── general/                      # Topic: General operational logs
│   └── (timestamped operational files)
└── stp4/                        # Topic: STP4 attestation
    └── stp4_* directories
```

**Topic-Based Report Organization (`reports/`):**
```
reports/
├── int-ha-control/               # Permanent INT-HA-CONTROL insights
│   ├── GATE_A_COMPLETION_SUMMARY.md
│   ├── ESCALATION_REPORT.md
│   └── REMEDIATION_STATUS.md
├── infrastructure/               # Infrastructure analysis & decisions
│   ├── INFRASTRUCTURE_BLOCKER_REPORT.md
│   ├── reconnaissance_analysis_20250928.md
│   └── WORKSPACE_ORGANIZATION_COMPLETED.md
├── coverage-analysis/            # Coverage measurement insights
├── deployment-status/            # Deployment status & provenance
│   └── version_provenance_2025-10-03.md
└── (existing report categories)
```

### Implementation Benefits

**Temporal Organization:**
- **ISO Week Structure**: `logs/YYYY-WWW/` provides natural weekly archival boundaries
- **Timestamp Prefixing**: `YYYYMMDD_HHMMSS-` ensures chronological ordering within topics
- **Automatic Cleanup**: Weekly boundaries enable systematic log rotation

**Topic-Based Categorization:**  
- **Operational Separation**: Logs by operational domain (int-ha-control, deployment, coverage)
- **Context Preservation**: Related artifacts grouped together for investigation
- **Scalable Structure**: New topics can be added without restructuring

**Clear Retention Policy:**
- **Logs**: Temporary artifacts with weekly archival, subject to rotation
- **Reports**: Permanent insights, findings, and decisions tracked in git

### Migration Pattern
When checkpoint directories or operational artifacts accumulate:

1. **Classify by Purpose**:
   - Operational logs, scripts, data files → `logs/YYYY-WWW/topic/`
   - Insights, reports, decisions, summaries → `reports/topic/`

2. **Apply Temporal Structure**:
   - Use current ISO week for log organization
   - Add timestamp prefixes for chronological ordering
   - Group by operational topic/domain

3. **Preserve Evidence**:
   - Maintain operational audit trails in logs
   - Keep permanent insights in reports
   - Document organizational decisions (like this addendum)

### Enforcement Updates
- **Weekly Cleanup**: Systematic log organization using ISO week boundaries
- **Topic Validation**: Operational artifacts must be categorized by topic
- **Retention Policy**: Logs subject to rotation, reports permanently tracked
- **Migration Protocol**: Standard pattern for cleanup operations

This addendum formalizes the workspace organization pattern implemented during 2025-W41 INT-HA-CONTROL operations, establishing a scalable model for future operational artifact management.

## 6. Token Block
```yaml
TOKEN_BLOCK:
  accepted:
    - WORKSPACE_TAXONOMY_OK
    - FOLDER_ASSIGNATION_OK
    - ADR_THREE_TIER_STRUCTURE
    - ADR_CANONICAL_SEGREGATION
    - TIME_BASED_LOG_ORGANIZATION
    - ISO_WEEK_ARCHIVAL_PATTERN
    - TOPIC_BASED_CATEGORIZATION
    - TOKEN_BLOCK_OK
  requires:
    - ADR_SCHEMA_V1
    - ADR_FORMAT_OK
    - ADR_GENERATION_OK
    - ADR_REDACTION_OK
    - THREE_TIER_ADR_FOLDER_DISCIPLINE
    - WORKSPACE_ORGANIZATION_PATTERN
  drift:
    - DRIFT: root_services_d_present
    - DRIFT: adr_canonical_supporting_confusion
    - DRIFT: bare_bb8_core_import
    - DRIFT: python_tools_root
    - DRIFT: folder_taxonomy_violation
    - DRIFT: adr_subfolder_violation
    - DRIFT: adr_formatting_noncompliant
    - DRIFT: temporal_log_organization_missing
    - DRIFT: topic_categorization_absent
```
