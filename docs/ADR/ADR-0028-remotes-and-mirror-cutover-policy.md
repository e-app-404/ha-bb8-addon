---
id: ADR-0028
title: "Remote triad, backups, and mirror cutover policy"
date: 2025-09-27
status: accepted
author:
  - Evert Appels
related:
  - ADR-0017
  - ADR-0026
supersedes: []
last_updated: 2025-09-27
tags: ["remote", "mirror", "cutover", "policy", "governance", "tokens", "backup", "synchronization", "git"]
---

# ADR-0028: Remote triad, backups, and mirror cutover policy

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
    ```bash
    git -C /path/to/bare fetch --prune https://github.com/e-app-404/ha-bb8-addon.git \
      +refs/heads/main:refs/heads/main
    ```
    If refs are corrupted/locked, repair permissions then:
    ```bash
    git -C /path/to/bare update-ref refs/heads/main <github-main-sha>
    ```
- Verify triad:
  ```bash
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

## Token Block

```yaml
TOKEN_BLOCK:
  accepted:
    - REMOTE_TRIAD_OK
    - MIRROR_SYNC_OK
    - CUTOVER_POLICY_OK
  drift:
    - DRIFT: remote_triad_mismatch
    - DRIFT: mirror_sync_failed
    - DRIFT: cutover_rollback_needed
```