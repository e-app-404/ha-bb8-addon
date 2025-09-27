# ADR bundle for HA BB-8 Add-on (session formalization)

Paste this whole block into your shell as a here-doc to create the ADRs,
or copy each `FILE:` section into place.

---

FILE: docs/ADR/ADR-0025-canonical-repo-layout-bb8-addon.md
---
id: ADR-0025
title: Canonical repo layout for HA BB-8 add-on (package lives under addon/)
status: accepted
deciders: ["maintainers"]
date: 2025-09-27
author: "Evert Appels"
tags: ["layout","imports","python","docker","addon"]
---

## Context

Historically, a `bb8_core/` package sometimes appeared at the repo root.
That caused:
- import ambiguity (`import bb8_core` resolving to unintended paths),
- IDE/symlink workarounds,
- container/runtime divergence (local vs add-on root).

## Decision

1. **Single, canonical location** for the runtime package:

addon/bb8_core/   # package root

Root-level `./bb8_core/` is **legacy** and must not exist.

2. **Runtime invocation**
- Set `PYTHONPATH=/work/addon` in the container.
- Launch as `python -m bb8_core` (or the add-on’s entry module).

3. **No symlinks** from root → addon. If compatibility is temporarily needed,
use a *shim module* (pure Python re-export) and remove it in the next minor.

## Consequences

- Imports are stable and match container execution.
- Tooling (linters, typecheckers, packagers) sees one source of truth.
- Moves are single-commit `git mv` changes; easier review/blame.

## Implementation notes

- If a root `./bb8_core/` exists, run:

git mv bb8_core addon/bb8_core

- Update Dockerfile/cmd to export `PYTHONPATH=/work/addon` and start with
`python -m bb8_core`.

---

FILE: docs/ADR/ADR-0026-backups-inventory-and-retention.md
---
id: ADR-0026
title: Backups, inventory, and retention policy for BB-8 add-on
status: accepted
deciders: ["maintainers"]
date: 2025-09-27
author: "Evert Appels"
tags: ["backups","retention","inventory","hygiene"]
---

## Context

The workspace accumulated `*.bak`, `.perlbak`, `_backup*` and tarballs,
obscuring source. We need consistent placement, retention, and tracking rules.

## Decision

### 1) Paths & tracking
- **Backups live under** `_backups/` and **are ignored by Git**.
- **Inventory is the exception** and is tracked:

_backups/inventory/**          # manifests, trees, staged manifests
_backups/.snapshot_state.json  # small state marker

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

- `.gitignore` rules (see ADR-0024 and hygiene gate) must include:

_backups/**
!_backups/
!_backups/inventory/
!_backups/inventory/**
!_backups/.snapshot_state.json
*.tar.gz *.tgz *.zip *.bundle
.bk. .bak .perlbak *~ .swp .tmp .temp
.pytest_cache/ pycache/ .ruff_cache/ .mypy_cache/ .idea/ .venv/
.trash/ .quarantine/

- Dedup tool removes root duplicate manifests if identical ones already exist
under `_backups/inventory/`.

---

FILE: docs/ADR/ADR-0027-hygiene-gate-and-status-checks.md
---
id: ADR-0027
title: Hygiene gate CI and required status checks
status: accepted
deciders: ["maintainers"]
date: 2025-09-27
author: "Evert Appels"
tags: ["ci","github-actions","branch-protection","hygiene"]
---

## Context

We added a minimal CI gate to keep the workspace “quiet” and prevent
accidental commits of artifacts.

## Decision

1. **Workflow file**: `.github/workflows/hygiene-gate.yml`
 - Triggers: `pull_request` to `main`, `push` to `main`,
   `workflow_dispatch`, nightly `schedule`.
 - Job **`gate`** runs:
   - `ops/check_workspace_quiet.sh .` (prints `OK` or violations).
   - Fails if any tracked path ends with
     `.tar.gz|.tgz|.zip|.bundle|.bk.<UTC>|.bak|.perlbak`.
   - Emits `git status -s` on failure.

2. **Branch protection**: mark **Required status check** as:

hygiene-gate / gate

Also enable “Require branches to be up to date before merging” if desired.

## Consequences

- PRs to `main` must pass the hygiene gate before merge.
- The check creates a predictable status context used in repository settings.

## Implementation notes

- We seeded runs on `main` so the context is discoverable.
- The `gate` job name is stable; do not rename without updating protection.

---

FILE: docs/ADR/ADR-0028-remotes-and-mirror-cutover-policy.md
---
id: ADR-0028
title: Remote triad, backups, and mirror cutover policy
status: accepted
deciders: ["maintainers"]
date: 2025-09-27
author: "Evert Appels"
tags: ["git","cutover","mirror","backup","operations"]
---

## Context

The repository is hosted on GitHub (`github`) and mirrored to a NAS (`origin`).
We executed a controlled cutover to replace `main` with a curated branch and
synchronize the mirror.

## Decision

**GitHub is the source of truth.** Before any forced update:

1. **Preflight**
- `git status --porcelain` must be clean (or stash with message).
- `git fetch github main` and record SHA.

2. **Backup current GitHub main**
- Create branch + tag backups `backup/main-<UTC>` pointing to the old SHA.

3. **Publish curated branch** and **force-replace** GitHub main
- `git push --force-with-lease=main github <branch>:main`
- Verify: local HEAD == `github/main` SHA.

4. **Mirror sync**
- Back up `origin/main` (branch + tag) to `backup/main-<UTC>` on origin.
- If origin rejects non-fast-forward:
  - SSH as admin; ensure repo is a bare directory owned by mirror user.
  - Run low-level update (after fetching from GitHub):
    ```
    git -C /path/to/bare fetch --prune https://github.com/<org>/<repo>.git \
      +refs/heads/main:refs/heads/main
    ```
    If refs are corrupted/locked, repair permissions then:
    ```
    git -C /path/to/bare update-ref refs/heads/main <github-main-sha>
    ```
- Verify triad:
  ```
  git rev-parse HEAD
  git ls-remote --heads github main | awk '{print $1}'
  git ls-remote --heads origin main  | awk '{print $1}'
  # All three SHAs must match
  ```

5. **Unstash** (or commit curated local changes) and push normally.

## Consequences

- We always have rollback points (`backup/main-<UTC>` on both remotes).
- Mirror permissions/ownership must be correct on the NAS to accept updates.

## Notes

- Keep a stable **`stable/<YYYY-MM-DD>`** annotated tag after quiet passes.

---

FILE: docs/ADR/ADR-0029-restore-staging-and-receipts.md
---
id: ADR-0029
title: Restore staging protocol and receipts
status: accepted
deciders: ["maintainers"]
date: 2025-09-27
author: "Evert Appels"
tags: ["restore","staging","receipts","rsync","safety"]
---

## Context

We formalized a safe restore flow using a staging directory and explicit
receipts, to avoid destructive merges and to maintain auditability.

## Decision

### Staging layout

- Staging dir:  
`_backups/restore_report/restore_staging/<UTC>/`
- Inventory/receipts:  
`_backups/inventory/{manifest_*.txt,tree_*.txt,staged_manifest_*.json}`  
`_backups/inventory/restore_receipts/receipt_<UTC>.txt`

### Apply protocol

1. **Preview** (dry-run; list planned copies).
2. **Apply** with rsync, **always** backing up overwritten targets using:
- `--backup --suffix=".from_backup_<UTC>"`
3. **Write a receipt** containing:
- `receipt_ts`, `stage_dir`, action (`apply` or `noop`), branch, notes.
4. **Commit receipts (text only)** — never commit tarballs.

### Normalization

- Root stray manifests are deduped into inventory.
- Legacy suffixes (`*.bak`, `.perlbak`, `_backup`, `_restore`) are renamed to
`.bk.<UTC>` or corralled; content is retained.

## Consequences

- Restores are reproducible and reviewable.
- Every apply/no-op has a durable, textual receipt.

## Implementation notes

- The helper script uses BusyBox-compatible shell; no background writes.
- To revert, use the generated `.from_backup_<UTC>` files.

---

FILE: docs/ADR/INDEX.md (append these lines near the top list)
---
- [ADR-0025] Canonical repo layout for HA BB-8 add-on (package lives under addon/)
- [ADR-0026] Backups, inventory, and retention policy for BB-8 add-on
- [ADR-0027] Hygiene gate CI and required status checks
- [ADR-0028] Remote triad, backups, and mirror cutover policy
- [ADR-0029] Restore staging protocol and receipts

---

FILE: docs/ADR/_snippets/hygiene-gate.yml (reference copy for convenience)
---
name: hygiene-gate
on:
pull_request:
 branches: [ main ]
push:
 branches: [ main ]
workflow_dispatch:
schedule:
 - cron: "13 2 * * *"  # daily
jobs:
gate:
 runs-on: ubuntu-latest
 steps:
   - uses: actions/checkout@v4
   - name: workspace quiet
     run: sh ops/check_workspace_quiet.sh .
   - name: ban tracked archives & editor backups
     run: |
       set -euo pipefail
       git status --porcelain=1 | awk '{print $2}' \
       | egrep -i '\.(tar\.gz|tgz|zip|bundle)$|\.bk\.[0-9TZ]+$|\.bak$|\.perlbak$' \
       | { ! read || { echo "ERROR: tracked artifacts detected"; exit 1; } }
   - name: status (diagnostics on failure)
     if: ${{ failure() }}
     run: git status -s

---

FILE: ops/check_workspace_quiet.sh (reference copy, unchanged)
---
#!/usr/bin/env sh
# Read-only workspace gate: prints "OK" when no forbidden shapes are present.
set -eu
root="${1:-.}"
viol=0
say() { printf '%s\t%s\t%s\n' "VIOLATION" "$1" "$2"; viol=1; }
# 1) legacy backups & editor junk
find "$root" -type f -regex '.*\.\(bak\|perlbak\)\(.*\)?' -print \
| while read -r f; do say "legacy_backup_or_perlbak" "$f  # normalize to *.bk.<UTC> or corral"; done
# 2) stray manifests at repo root (expected in _backups/inventory)
for pat in 'manifest_*.txt' 'tree_*.txt'; do
find "$root" -maxdepth 1 -type f -name "$pat" -print \
 | while read -r f; do say "stray_manifest_root" "$f  # move to _backups/inventory/ or staging dir"; done
done
# 3) tracked archives (should be ignored)
git status --porcelain=1 | awk '{print $2}' \
| egrep -i '\.(tar\.gz|tgz|zip|bundle)$' >/dev/null 2>&1 && say "tracked_archive" "# add ignore or untrack"
# Exit
if [ "$viol" -eq 0 ]; then echo "OK"; exit 0; else echo "TOTAL_VIOLATIONS $viol"; exit 1; fi
---