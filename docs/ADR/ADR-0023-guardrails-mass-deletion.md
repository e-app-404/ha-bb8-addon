---
id: ADR-0023
title: "Guardrails to prevent mass-deletion and accidental backup commits"
authors:
  - "Evert Appels"
  - "Strategos"
status: accepted
related: 
  - ADR-0018
supersedes: []
date: 2025-09-25
last_updated: 2025-09-25
---

## Context

Recent incidents in this repository demonstrated that automated autofix and helper scripts can create many local backup files and that bulk automated moves (or mistaken commits) can make files appear to "disappear" from their original locations. We need a small, pragmatic set of guardrails to protect against accidental mass-deletion/moves and accidental commits of backup files, while keeping developer workflow reasonably unobstructed.

## Decision

We will adopt a layered set of guardrails across local developer tooling, CI, and repository operational processes:

1) CI mass-deletion detector
   - Fail PRs that delete/rename/move more than N files (default N=10).
   - Fail PRs that add tracked backup-like patterns (e.g., `*.autofix.*`, `*.perlbak`, `*.autofix.bak`).
   - Implement script: `ops/guardrails/check_pr_mass_deletes.sh` and call it from the `shape` job or a dedicated `repo-shape` CI job.

   Example (safe, idempotent):

```sh
#!/usr/bin/env bash
set -euo pipefail

# threshold (tune)
THRESHOLD=${THRESHOLD:-10}

# Get diff stats in the PR (works in CI where $GITHUB_BASE_REF and $GITHUB_HEAD_REF exist)
# Fallback: compare HEAD with origin/main if not available.
BASE=${GITHUB_BASE_REF:-origin/main}
HEAD=${GITHUB_HEAD_REF:-HEAD}

# compute file-level changes
added=$(git diff --name-only --diff-filter=A "$BASE"..."$HEAD" | wc -l)
deleted=$(git diff --name-only --diff-filter=D "$BASE"..."$HEAD" | wc -l)
renamed=$(git diff --name-only --diff-filter=R "$BASE"..."$HEAD" | wc -l)

total_changes=$((added + deleted + renamed))

if [ "$total_changes" -gt "$THRESHOLD" ]; then
  echo "ERROR: PR changes $total_changes files (added $added, deleted $deleted, renamed $renamed) — exceeds threshold $THRESHOLD."
  echo "If this is intentional, adjust THRESHOLD or open a maintenance PR with approval from repository admins."
  exit 1
fi

# also fail on tracked backup patterns being introduced
if git diff --name-only --cached --diff-filter=A "$BASE"..."$HEAD" | grep -E '\.autofix\.|\.perlbak$|\.autofix\.bak' -q; then
  echo "ERROR: PR adds tracked backup-like files; please remove or move them to _backups"
  git diff --name-only --cached --diff-filter=A "$BASE"..."$HEAD" | grep -E '\.autofix\.|\.perlbak$|\.autofix\.bak' || true
  exit 1
fi

echo "OK: PR passes mass-deletion and tracked-backup checks."
exit 0
```

2) Pre-merge snapshot artifact
   - If a PR modifies more than M files or deletes more than K files (these thresholds can be the same as the detector), CI will create a pre-merge snapshot tarball and upload it as a GitHub Actions artifact. This artifact can be used to restore the pre-merge tree quickly.

   Example:

```sh
snapshot_name="premerge-${GITHUB_RUN_ID:-manual}-$(date +%Y%m%d%H%M%S).tgz"
git archive --format=tar HEAD | gzip > "$snapshot_name"
# upload as artifact in GitHub Actions using actions/upload-artifact
```

3) Make helper scripts safe: preflight snapshot + manifest
   - Any helper that bulk-moves or removes many files (including `helper_move_backup.sh`) must:
     - Take a tar.gz snapshot of all matched files before moving.
     - Write a manifest JSON with original path, destination, timestamp, user, and commit id.
     - Require an explicit `--force` flag to run non-interactively.

   Example snippet (apply before moving files):

```sh
matches=$(find . -type f \( -name '*.autofix.*' -o -name '*.perlbak' -o -name '*.autofix.bak' \) -print)
if [ -n "$matches" ]; then
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  snapshot="_backups/snapshot_${ts}.tgz"
  tar -czf "$snapshot" $matches
  echo "{\"snapshot\":\"$snapshot\",\"ts\":\"$ts\",\"files\":[$(printf '%s\n' $matches | jq -R -s -c 'split("\n")[:-1]')] }" > "_backups/manifest_${ts}.json"
  # continue moving files into _backups as before
fi
```

4) Local pre-commit safeguards
   - Distribute a `pre-commit` configuration (or a plain `./.git/hooks/pre-commit` script) that prevents staging backup-like files and warns/fails on too many deletions.

   Example pre-commit snippet:

```sh
#!/usr/bin/env bash
staged=$(git diff --cached --name-only)
if echo "$staged" | grep -E '\.autofix\.|\.perlbak$|\.autofix\.bak' -q; then
  echo "Refusing commit: staged backup/autofix files detected."
  echo "$staged" | grep -E '\.autofix\.|\.perlbak$|\.autofix\.bak'
  exit 1
fi

# warn/stop on many deletions
deletes=$(git diff --cached --name-only --diff-filter=D | wc -l)
if [ "$deletes" -gt 8 ]; then
  echo "Refusing commit: more than 8 deletions staged ($deletes). Please review."
  exit 1
fi
```

5) Protect critical paths & require reviews
   - Use GitHub protected-branch rules to require PRs, passing status checks, and at least one code owner approval for changes touching sensitive areas (`docs/`, `ops/`, `.vscode`, etc.).

6) Server-side pre-receive hooks (optional)
   - If you run your own git server, a pre-receive hook can be added to reject pushes performing mass deletes or adding tracked backup patterns.

7) Logging & audit trail
   - Helper scripts must write `_backups/manifest_<ts>.json` and CI snapshot artifacts must be retained for a configurable period.

8) Local-machine safety
   - Encourage Time Machine / local filesystem snapshots and store templates for critical workspace files under `docs/` so they are tracked and recoverable.

9) Alerting on unexpected repo shape changes
   - CI should open an issue or create a thread when the mass-deletion detector triggers. Include the diff and a link to the pre-merge snapshot artifact.

## Rationale

Layered protections (local hooks, CI checks, server-side rules, and snapshots) make the cost of a human or tool mistake low: the mistake will be caught or easily restorable instead of silently deleting files and losing them.

## Consequences

- Small operational overhead: CI will run a few extra checks and take occasional snapshots; helper scripts will run a snapshot step before moving files.
- Developers must install `pre-commit` tooling to get local checks (or run a manual script provided), or rely on CI as a backstop.
- Some large refactors will require an exemption workflow or higher thresholds.

## Minimal set for initial rollout
1. Add `.gitignore` entries for backup suffixes (non-destructive).
2. Add `ops/guardrails/check_pr_mass_deletes.sh` and run it in `shape.yml`/PR CI with default threshold 10.
3. Update `helper_move_backup.sh` so it snapshots matched files and writes a manifest before moving — require `--force` for non-interactive runs.
4. Add a `pre-commit` local hook/template in `.pre-commit-config.yaml` to block accidental staging of backup files.

---
References:
- This ADR references repository guardrail work and the repository's `ops/guardrails` scripts. Implementations should be placed under `ops/guardrails/` and referenced from CI workflows.
