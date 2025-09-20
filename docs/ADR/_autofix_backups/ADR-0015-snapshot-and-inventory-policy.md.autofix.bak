---
title: "ADR-0015: Snapshot & Inventory Policy"
date: 2025-09-12
status: Accepted
author:
   - Promachos Governance
related:
   - ADR-0001
   - ADR-0009
supersedes: []
last_updated: 2025-09-12
---

# ADR-0015: Snapshot & Inventory Policy

## Context
We experienced accidental mass deletions and loss of untracked workspace assets. We need a canonical, low-friction policy to:
- Periodically snapshot the tracked tree (tarball) when material change occurs.
- Record an inventory of **untracked** files for recovery visibility.
- Enforce this behavior locally (git hooks) and verify via CI without moving large files into Git.

## Decision
1. **Trigger Metric (Thresholds)**
   - Create a tracked-tree tarball snapshot when **either**:
     - `LOC_CHANGED >= 2000` (sum of lines added + deleted since last snapshot mark), **or**
     - `FILES_CHANGED >= 80` (files touched since last snapshot mark), **or**
     - No previous snapshot mark is found.
   - Thresholds are configurable via environment:
     - `LOC_THRESHOLD` (default `2000`)
     - `FILES_THRESHOLD` (default `80`)

2. **What we Snapshot**
   - Tarball contains **tracked files only** (from `git ls-files`), stored under `_backups/` and/or `docs/tarballs/`.
   - A concurrent **untracked inventory** is emitted to `_backups/inventory/untracked_<TS>.txt`.

3. **Markers**
   - The last snapshot commit and counters are recorded in `_backups/.snapshot_state.json`.

4. **Where Artifacts Live**
   - `_backups/` and `docs/tarballs/` are **ignored** by Git (see .gitignore). No large files pushed.

5. **Enforcement & Automation**
   - Local **post-commit** hook: runs a **dry-run** check; if thresholds are exceeded and `SNAPSHOT_AUTO=1`, emits tarball + inventory.
   - **Makefile** (standalone `scripts/snapshot.mk`) provides `snapshot-auto`, `snapshot-tarball`, and `snapshot-untracked` targets.
   - CI (PR workflow) verifies ADR presence and `--dry-run` behavior; CI does **not** create tarballs.

## Consequences
- Safer local workflows; easy recovery points when change is substantial.
- No large artifacts enter the repo.
- Developers remain in control; auto snapshot only when `SNAPSHOT_AUTO=1`.

## Alternatives Considered
- Size-based (MB) thresholds: noisy due to caches; rejected.
- Tooling under `tools/`: disallowed by pre-push guard; use `scripts/` instead.

## Rollout
- This ADR, `scripts/snapshot_policy.sh`, `scripts/snapshot.mk`, `.githooks/post-commit`, and a PR workflow are added.
- Thresholds can be tuned in future ADRs if needed.

## Token Blocks

```yaml
TOKEN_BLOCK:
   accepted:
      - SNAPSHOT_POLICY_OK
      - INVENTORY_OK
      - THRESHOLDS_OK
   drift:
      - DRIFT: snapshot_policy_failed
      - DRIFT: inventory_missing
      - DRIFT: thresholds_invalid
```