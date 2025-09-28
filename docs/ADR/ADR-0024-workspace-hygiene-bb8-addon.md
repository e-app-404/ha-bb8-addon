---
id: ADR-0024
title: "Workspace Hygiene (BB-8 add-on) — Adoption of ADR-0024 with repo-specific overrides"
date: 2025-09-27
status: Accepted
author:
  - Evert Appels
related:
  - ADR-0015
  - ADR-0023
  - ADR-0026
  - ADR-0027
external_related:
  - repo: "ha-config"
    adr: "ADR-0024"
    url: "https://github.com/e-app-404/ha-config/blob/main/docs/ADR/ADR-0024-workspace-hygiene.md"
    relationship: "adopts"
    last_checked: "2025-09-28"
alignment_dependencies:
  - "ha-config:ADR-0024"
supersedes: []
last_updated: 2025-09-28
tags: ["adr", "cross-repository", "linking", "alignment", "governance", "tokens", "workspace-hygiene", "backups", "ci", "enforcement"]
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

## Notes
This ADR adopts the main HA config repo's ADR-0024 verbatim as the baseline. If the upstream ADR-0024 changes, this repo follows it unless an explicit override is added here in a new "Amendment" section.

## Token Block

```yaml
TOKEN_BLOCK:
  accepted:
    - WORKSPACE_HYGIENE_OK
    - BACKUP_RETENTION_OK
    - HYGIENE_GATE_ENFORCED_OK
  drift:
    - DRIFT: tracked_archives
    - DRIFT: legacy_backup_suffix
    - DRIFT: hygiene_gate_failed
```

