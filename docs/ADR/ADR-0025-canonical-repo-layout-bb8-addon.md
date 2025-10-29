---
id: ADR-0025
title: Canonical repo layout for HA BB-8 add-on (package lives under addon/)
date: 2025-09-27
status: accepted
decision: 1. **Single, canonical location** for the runtime package:.
author:
- Evert Appels
related:
- ADR-0001
- ADR-0012
- ADR-0019
supersedes: []
last_updated: 2025-09-27
tags:
- repo-structure
- imports
- governance
- coverage
- pythonpath
- tokens
- addon
- bb8_core
- canonical
---

# ADR-0025: Canonical repo layout for HA BB-8 add-on (package lives under addon/)

## Context

Historically, a `bb8_core/` package sometimes appeared at the repo root.
That caused:
- import ambiguity (`import bb8_core` resolving to unintended paths),
- IDE/symlink workarounds,
- container/runtime divergence (local vs add-on root).

## Decision

1. **Single, canonical location** for the runtime package:

```
addon/bb8_core/   # package root
```

Root-level `./bb8_core/` is **legacy** and must not exist.

2. **Runtime invocation**
- Set `PYTHONPATH=/work/addon` in the container.
- Launch as `python -m bb8_core` (or the add-on's entry module).

3. **No symlinks** from root → addon. If compatibility is temporarily needed,
use a *shim module* (pure Python re-export) and remove it in the next minor.

## Consequences

- Imports are stable and match container execution.
- Tooling (linters, typecheckers, packagers) sees one source of truth.
- Moves are single-commit `git mv` changes; easier review/blame.

## Implementation notes

- If a root `./bb8_core/` exists, run:

```bash
git mv bb8_core addon/bb8_core
```

- Update Dockerfile/cmd to export `PYTHONPATH=/work/addon` and start with
`python -m bb8_core`.

## Token Block

```yaml
TOKEN_BLOCK:
  accepted:
    - CANONICAL_LAYOUT_OK
    - ADDON_PACKAGE_OK
    - PYTHONPATH_OK
  drift:
    - DRIFT: root_bb8_core_present
    - DRIFT: import_ambiguity
    - DRIFT: pythonpath_incorrect
```