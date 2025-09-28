---
id: ADR-0027
title: "Hygiene gate CI and required status checks"
date: 2025-09-27
status: accepted
author:
  - Evert Appels
related:
  - ADR-0018
  - ADR-0023
  - ADR-0026
supersedes: []
last_updated: 2025-09-27
tags: ["ci", "hygiene", "branch-protection", "status-checks", "automation", "governance", "tokens"]
---

# ADR-0027: Hygiene gate CI and required status checks

## Context

We added a minimal CI gate to keep the workspace "quiet" and prevent
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

```
hygiene-gate / gate
```

Also enable "Require branches to be up to date before merging" if desired.

## Consequences

- PRs to `main` must pass the hygiene gate before merge.
- The check creates a predictable status context used in repository settings.

## Implementation notes

- We seeded runs on `main` so the context is discoverable.
- The `gate` job name is stable; do not rename without updating protection.

## Token Block

```yaml
TOKEN_BLOCK:
  accepted:
    - HYGIENE_GATE_OK
    - WORKSPACE_QUIET_OK
    - BRANCH_PROTECTION_OK
  drift:
    - DRIFT: hygiene_gate_failed
    - DRIFT: workspace_not_quiet
    - DRIFT: tracked_artifacts
```