---
id: ADR-0026
title: Backups, inventory, and retention policy for BB-8 add-on
date: 2025-09-27
status: accepted
decision: '### 1) Paths & tracking - **Backups live under** _backups/ and **are ignored
  by Git**. - **Inventory is the exception** and is tracked:.'
author:
- Evert Appels
related:
- ADR-0015
- ADR-0023
supersedes: []
last_updated: 2025-09-27
tags:
- backup
- inventory
- retention
- policy
- governance
- tokens
- hygiene
- ci
- enforcement
- adr
---

# ADR-0026: Backups, inventory, and retention policy for BB-8 add-on

## Context

The workspace accumulated `*.bak`, `.perlbak`, `_backup*` and tarballs,
obscuring source. We need consistent placement, retention, and tracking rules.

## Decision

### 1) Paths & tracking
- **Backups live under** `_backups/` and **are ignored by Git**.
- **Inventory is the exception** and is tracked:

```
_backups/inventory/**          # manifests, trees, staged manifests
_backups/.snapshot_state.json  # small state marker
```

- Tarballs/archives (`*.tar.gz`, `*.tgz`, `*.zip`, `*.bundle`) remain ignored.

### 2) Canonical local backup filename
- Small/editor backups normalize to: `name.bk.<UTC>`  
e.g., `Dockerfile.bk.20250927T123456Z`.
- Legacy suffixes (`*.bak`, `*.perlbak`, `_backup`, `_restore`) are corralled
or renamed during hygiene passes; content is preserved.

### 3) Retention (defaults)
- `*.bk.<UTC>` and small manifests: keep as long as useful (text is tiny).
- Binary archives/tarballs: keep up to **365 days** in `_backups/`; older → move
to cold storage (outside Git).
- Logs/reports: keep **90 days** (or receipts only).

## Consequences

- Git history contains small, reproducible **manifests & receipts** only.
- Large, binary or editor detritus stays out of reviews and diffs.

## Implementation notes

- `.gitignore` rules (see ADR-0027 and hygiene gate) must include:

```
_backups/**
!_backups/
!_backups/inventory/
!_backups/inventory/**
!_backups/.snapshot_state.json
*.tar.gz *.tgz *.zip *.bundle
.bk. .bak .perlbak *~ .swp .tmp .temp
.pytest_cache/ __pycache__/ .ruff_cache/ .mypy_cache/ .idea/ .venv/
.trash/ .quarantine/
```

- Dedup tool removes root duplicate manifests if identical ones already exist
under `_backups/inventory/`.

## Token Block

```yaml
TOKEN_BLOCK:
  accepted:
    - BACKUP_POLICY_OK
    - RETENTION_OK
    - INVENTORY_TRACKED_OK
  drift:
    - DRIFT: legacy_backup_suffix
    - DRIFT: tracked_archive
    - DRIFT: stray_manifest_root
```