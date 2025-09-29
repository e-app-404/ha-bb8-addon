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

---

## Machine-Readable Policy Block

```yaml
REMOTE_TRIAD_POLICY:
  remotes:
    github: "https://github.com/e-app-404/ha-bb8-addon.git"
    origin: "ssh://gituser@ds220plus.reverse-beta.ts.net/volume1/git-mirrors/ha-config.git"
  source_of_truth: "github/main"
  shells:
    zsh_refspec_note: "Use ${VAR}:refs/heads/… (braces) to avoid zsh parameter modifiers."
  constraints:
    nas_shell: "Synology git service runs restricted git-shell; do not run arbitrary 'ssh … git' commands."
    update_method: "Mirror must be updated by pushing from the local workstation."
    force_policy: "–force-with-lease=main for cutovers and non-fast-forward mirror updates."
  acceptance_tokens:
    - BACKUPS_OK
    - CUTOVER_POLICY_OK
    - MIRROR_SYNC_OK
    - REMOTE_TRIAD_OK
  error_signatures:
    non_fast_forward: "denying non-fast-forward refs/heads/main (you should pull first)"
    synology_git_shell: "fatal: git package does not support customized git-shell-commands"
    zsh_refspec_mangled: "src refspec efs/heads/main does not match any"
```

## Operational Procedure (Copilot-ready)

> Run from your Mac at the workspace root (HA-BB8/). Assumes remotes named github and origin.

```bash
# 0) Preflight & backups
git fetch --all --prune
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
git push github refs/heads/main:refs/heads/backup/main-github-$STAMP
git push github refs/heads/main:refs/tags/backup/main-github-$STAMP
git push origin refs/heads/main:refs/heads/backup/main-nas-$STAMP
git push origin refs/heads/main:refs/tags/backup/main-nas-$STAMP
echo "BACKUPS_OK:$STAMP"

# 1) Capture GitHub main SHA (source of truth) — zsh safe
git fetch github main --prune
GITHUB_SHA=$(git rev-parse refs/remotes/github/main)
echo "GITHUB_SHA=$GITHUB_SHA"

# 2) Cutover (optional): replace GitHub main with curated branch
# git push github --force-with-lease=main my-curated-branch:refs/heads/main && echo CUTOVER_POLICY_OK

# 3) Mirror sync (push from Mac; do NOT ssh into NAS to run git)
git push origin --force-with-lease=main ${GITHUB_SHA}:refs/heads/main && echo MIRROR_SYNC_OK

# 4) Triad verification
LOCAL=$(git rev-parse HEAD)
GH=$(git ls-remote --heads github main | awk '{print $1}')
NAS=$(git ls-remote --heads origin main | awk '{print $1}')
echo "LOCAL=$LOCAL"; echo "GITHUB=$GH"; echo "NAS=$NAS"
[ "$GH" = "$NAS" ] && echo REMOTE_TRIAD_OK || { echo "DRIFT: remote_triad_mismatch"; exit 2; }
```

## Troubleshooting (Deterministic)

| Symptom (verbatim) | Cause | Action |
|---|---|---|
| denying non-fast-forward refs/heads/main (you should pull first) | Mirror rejects non-FF | Push with --force-with-lease=main using the GitHub SHA refspec. |
| fatal: git package does not support customized git-shell-commands | Synology restricted git-shell | Do not ssh to run git; always update mirror by pushing from local. |
| src refspec <sha>efs/heads/main does not match any | zsh mangled refspec | Use ${GITHUB_SHA}:refs/heads/main (braces) or quote the entire refspec. |

## Make Targets (Reference)

```make
.PHONY: backups triad-sync triad-verify
backups:
	git fetch --all --prune
	STAMP=$$(date -u +%Y%m%dT%H%M%SZ); \
	git push github refs/heads/main:refs/heads/backup/main-github-$$STAMP; \
	git push github refs/heads/main:refs/tags/backup/main-github-$$STAMP; \
	git push origin refs/heads/main:refs/heads/backup/main-nas-$$STAMP; \
	git push origin refs/heads/main:refs/tags/backup/main-nas-$$STAMP; \
	echo BACKUPS_OK:$$STAMP

triad-sync:
	git fetch github main --prune
	GITHUB_SHA=$$(git rev-parse refs/remotes/github/main); \
	git push origin --force-with-lease=main $$GITHUB_SHA:refs/heads/main && echo MIRROR_SYNC_OK

triad-verify:
	@LOCAL=$$(git rev-parse HEAD); \
	GH=$$(git ls-remote --heads github main | awk '{print $$1}'); \
	NAS=$$(git ls-remote --heads origin main | awk '{print $$1}'); \
	echo LOCAL=$$LOCAL; echo GITHUB=$$GH; echo NAS=$$NAS; \
	[ "$$GH" = "$$NAS" ] && echo REMOTE_TRIAD_OK || (echo "DRIFT: remote_triad_mismatch"; exit 2)
```