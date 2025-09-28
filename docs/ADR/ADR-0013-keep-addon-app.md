---
id: ADR-0013
title: "Keep all app/ scripts and diagnostics in addon/app/"
date: 2025-09-06
status: Accepted
author:
  - Promachos Governance
related:
  - ADR-0001
  - ADR-0012
supersedes: []
last_updated: 2025-09-06
tags: ["app", "scripts", "diagnostics", "repo-structure", "governance"]
---

# ADR-0013 - Keep all app/ scripts and diagnostics in addon/app/

## Status
Accepted

## Context
Historically, scripts and diagnostics were split between `/app` and `/addon/app`. This caused import and test conflicts, especially with duplicate filenames (e.g., `test_ble_adapter.py`).

## Decision
- All scripts, diagnostics, and test utilities must reside in `addon/app/`.
- The root `/app` folder is eliminated.
- All future additions must be placed in `addon/app/` only.
- CI and repo hygiene checks will enforce this layout.


## Consequences
- No more import/test conflicts due to duplicate basenames.
- Simpler repo structure and governance.
- All documentation and onboarding should reference `addon/app/` as the canonical location.

## Token Blocks

```yaml
TOKEN_BLOCK:
  accepted:
    - APP_LAYOUT_OK
    - DIAGNOSTICS_OK
  drift:
    - DRIFT: app_layout_invalid
    - DRIFT: diagnostics_missing
```

