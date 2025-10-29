---
id: ADR-0024
title: "Workspace Hygiene (BB-8 add-on) \u2014 Adoption of ADR-0024 with repo-specific\
  \ overrides"
date: 2025-09-27
status: Accepted
decision: "**Adopt the main repo\u2019s ADR-0024 as the normative policy** and apply\
  \ the following **BB-8\u2013specific overrides**:."
author:
- Evert Appels
related:
- ADR-0015
- ADR-0023
- ADR-0026
- ADR-0027
external_related:
- repo: ha-config
  adr: ADR-0024
  url: https://github.com/e-app-404/ha-config/blob/main/docs/ADR/ADR-0024-workspace-hygiene.md
  relationship: adopts
  last_checked: '2025-09-28'
alignment_dependencies:
- ha-config:ADR-0024
supersedes: []
last_updated: 2025-09-30
tags:
- adr
- cross-repository
- linking
- alignment
- governance
- tokens
- workspace-hygiene
- backups
- ci
- enforcement
---

## Context

The BB-8 add-on repo accumulated editor backup files (`*.bak`, `*.perlbak`, temp/swap), ad-hoc tarballs/bundles, and restore artifacts at the repo root. This obscured important sources and risked large, noisy commits. The main HA config repo's **ADR-0024: Workspace Hygiene** already defines a strong policy for ignoring, retaining and gating such artifacts.

## Cross-Repository References

This ADR adopts [@ha-config:ADR-0024](https://github.com/e-app-404/ha-config/blob/main/docs/ADR/ADR-0024-workspace-hygiene.md) as the baseline workspace hygiene policy.

### Alignment Status
- **Last Verified**: 2025-09-28
- **Upstream Version**: ADR-0024 (last_updated: 2025-09-15) 
- **Local Adaptations**: See "BB-8-specific overrides" section below

### Change Monitoring
Monitor [@ha-config:ADR-0024](https://github.com/e-app-404/ha-config/blob/main/docs/ADR/ADR-0024-workspace-hygiene.md) for changes that may require updates to this ADR.

## Decision

**Adopt the main repo’s ADR-0024 as the normative policy** and apply the following **BB-8–specific overrides**:

### A. Canonical backup & retention
- **Canonical local backup name**: `*.bk.<UTC>` (e.g., `file.bk.20250927T123456Z`) — **never tracked**.
- **Retention**:
  - Backups/snapshots (tarballs): **keep 365d** in `_backups/` (archive off-repo after 1y).
  - Editor/temp/swap (`~`, `.swp`, `.perlbak`, `*.autofix.bak`): **keep 0d in Git** (ignored or deleted).
  - Logs/reports: **keep ≤90d**; prefer small text receipts if needed.

### B. Allowed vs forbidden tracked content
- **Allowed to track**: ADR docs, source, small inventories:
  - `_backups/inventory/**` and `_backups/.snapshot_state.json` (whitelisted).
- **Forbidden to track** (CI gate fails PRs if present):
  - `*.tar.gz`, `*.tgz`, `*.zip`, `*.bundle`, any `*.bk.*`, legacy `*.bak`/`*.perlbak`, and restore staging blobs.

### C. Ignore rules (authoritative snippet)
```gitignore
# ADR-0024 (BB-8) — Backups: ignore all, re-include inventory + snapshot marker
_backups/**
!_backups/
!_backups/inventory/
!_backups/inventory/**
!_backups/.snapshot_state.json

# Generated/report & caches (scope as needed)
reports/**
.trash/**
.quarantine/**
.venv*/
__pycache__/
.pytest_cache/
.ruff_cache/
.mypy_cache/
node_modules/
.idea/

# Backups / temp / logs
*.bk.*
*.bak
*.perlbak
*~
*.swp
*.tmp
*.temp
*.log
*.jsonl

# Archives
*.bundle
*.tar.gz
*.tgz
*.zip

# rsync overwrite receipts
*.from_backup_*

### D. CI enforcement (hygiene gate)
- Workflow: `.github/workflows/hygiene-gate.yml`
- Required check name (for branch protection): `hygiene-gate / gate`
- Gate script: `ops/check_workspace_quiet.sh` (read-only). Prints OK when clean; emits VIOLATION … lines and exits non-zero otherwise.

### E. Workspace structure touchpoints (ties to ADR-0012/0019)
- Canonical layout under addon/: `addon/{bb8_core,services.d,tests,tools,app}`.
- Imports must use `addon.bb8_core` (no bare `bb8_core`).

## Consequences
- PRs that introduce forbidden shapes (tracked archives, legacy `*.bak`, stray manifests at root) fail the hygiene gate.
- Restore artifacts remain available under `_backups/` but do not pollute history; small inventories/receipts can be tracked for auditability.
- Editors/tools should be configured to write backup/auto-fix files into ignored locations (or disabled).

## Enforcement & rollout
- Status: Enabled (Accepted).
- CI: Hygiene gate required on main (branch protection).
- Receipts: Restoration receipts live under `_backups/inventory/restore_receipts/`.
- Rollback: use `stable/*` tags and backup branches when performing cutovers.

## Amendment A: Workspace Organization and Canonical File Placement (2025-09-30)

Building on the base hygiene policy, we establish **clear separation of tracked documentation vs temporary outputs** and **canonical locations for operational artifacts**.

### A1. logs/ vs reports/ Separation

#### A1.1 logs/ Directory (Git-ignored temporary outputs)
- **Purpose**: Automated tool outputs, temporary artifacts, diagnostic dumps
- **Git tracking**: Completely ignored (`logs/` and `logs/**` in .gitignore)
- **Content types**:
  - Diagnostic tarballs (`ha_bb8_diagnostics_*.tar.gz`)
  - Timestamped evidence collection (`stp4_*` directories)  
  - Receipt files (`*_receipt.txt`)
  - Log files (`*.log`)
  - Verification outputs (`*_verification_*.txt`)
  - Temporary JSON/XML artifacts from automated tools
- **Retention**: Auto-cleanup after 90 days, no git pollution

#### A1.2 reports/ Directory (Git-tracked important documentation)  
- **Purpose**: Important documentation meant for long-term retention
- **Git tracking**: Selective tracking with explicit includes
- **Content types**:
  - `checkpoints/` — Milestone validation frameworks (e.g., INT-HA-CONTROL)
  - `governance/` — Compliance and audit documentation
  - `*.md` files — Development plans, assessments, documentation
- **Forbidden**: Timestamped outputs, temporary tool dumps, logs

#### A1.3 Updated .gitignore Configuration
```gitignore
# Workspace organization: logs/ (untracked) vs reports/ (tracked important docs)
logs/
logs/**
# Keep reports/ tracked for important documentation  
reports/**
!reports/
!reports/checkpoints/
!reports/checkpoints/**
!reports/*.md
# Coverage files (generated, location: addon/)
addon/.coverage
addon/.coverage.*
.coverage
.coverage.*
```

### A2. Canonical File Placements

#### A2.1 Operational Scripts
- **Diagnostics collection**: `ops/diag/collect_ha_bb8_diagnostics.sh`
- **Diagnostic output**: `logs/ha_bb8_diagnostics_*` (auto-created by script)
- **Status reporting**: `reports/checkpoints/INT-HA-CONTROL/` (framework artifacts)

#### A2.2 Testing and Coverage
- **Coverage configuration**: `addon/.coveragerc` (addon-specific test config)
- **Coverage database**: `addon/.coverage` (generated, git-ignored)
- **Test configuration**: `addon/pytest.ini` (addon-specific)
- **Project configuration**: `addon/pyproject.toml` (addon-specific)

#### A2.3 Evidence and Validation  
- **Evidence configuration**: `.evidence.env` (root-level MQTT config)
- **Evidence collection output**: `logs/stp4_*` (timestamped artifacts)
- **Validation frameworks**: `reports/checkpoints/` (tracked milestones)

### A3. Script Output Path Requirements

All operational scripts **MUST** output to appropriate canonical locations:
- Diagnostic tools → `logs/` directory (create if needed: `mkdir -p logs`)
- Status/framework artifacts → `reports/checkpoints/` (for tracking)
- Temporary receipts/logs → `logs/` (not repo root)

### A4. Enforcement Extensions

Beyond base ADR-0024 hygiene gates:
- **Misplaced outputs**: Scripts outputting to repo root instead of `logs/`
- **Coverage file pollution**: `.coverage*` files at repo root (should be in `addon/`)
- **Reports contamination**: Temporary files in `reports/` (should be in `logs/`)

### A5. Migration Compliance

This amendment formalizes workspace reorganization completed 2025-09-30:
- ✅ Moved 19 restored test files to proper locations
- ✅ Relocated coverage files to `addon/` directory  
- ✅ Established `logs/` vs `reports/` separation
- ✅ Updated script output paths to canonical locations
- ✅ Cleaned repo root of misplaced artifacts

## Notes
This ADR adopts the main HA config repo's ADR-0024 verbatim as the baseline. If the upstream ADR-0024 changes, this repo follows it unless an explicit override is added here in a new "Amendment" section.

**Amendment A Status**: Implemented 2025-09-30, enforced via updated .gitignore and canonical file placement guidelines.

## Token Block

```yaml
TOKEN_BLOCK:
  accepted:
    - WORKSPACE_HYGIENE_OK
    - BACKUP_RETENTION_OK
    - HYGIENE_GATE_ENFORCED_OK
    - WORKSPACE_ORGANIZATION_OK
    - CANONICAL_PLACEMENT_OK
    - LOGS_REPORTS_SEPARATION_OK
    - SCRIPT_OUTPUT_PATHS_OK
  drift:
    - DRIFT: tracked_archives
    - DRIFT: legacy_backup_suffix
    - DRIFT: hygiene_gate_failed
    - DRIFT: misplaced_outputs
    - DRIFT: coverage_file_pollution
    - DRIFT: reports_contamination
    - DRIFT: canonical_violation
```

