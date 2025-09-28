---
id: ADR-0012
title: "Canonical module layout & imports"
date: 2025-09-05
status: Accepted
author:
  - Promachos Governance
related:
  - ADR-0001
  - ADR-0003
  - ADR-0009
supersedes: []
last_updated: 2025-09-05
tags: ["repo-structure", "imports", "governance", "coverage"]
---

# ADR-0012 - Canonical module layout & imports

## Context
The codebase historically used multiple trees (e.g., `bb8_core/*`, `addon/bb8_core/*`, `tools/*`). This caused duplicate modules and broken imports.

## Decision
- **Canonical path** for production Python is `addon/bb8_core/*`.
- **Tests** live in `addon/tests/*`.
- Legacy paths (e.g., `bb8_core/*`, `tools/*.py`) must not contain production modules duplicated under `addon/bb8_core/*`.
- Imports must use `import addon.bb8_core.<module>` or `from addon.bb8_core import <symbol>`.

## Consequences
- Git hooks enforce: no conflict markers, no duplicate `verify_discovery.py` (or any module) outside the canonical path, no legacy `tests/*`.
- CI and local commands use a **single** coverage driver (`pytest-cov`) and a single coverage gate script path.

## Enforcement
- Git hooks: pre-commit and pre-push (see repo hooks).
- “Layout guard” test ensures no strays in non-canonical paths.

## Token Blocks

```yaml
TOKEN_BLOCK:
  accepted:
    - CANONICAL_LAYOUT_OK
    - IMPORTS_OK
    - COVERAGE_OK
  drift:
    - DRIFT: layout_invalid
    - DRIFT: imports_invalid
    - DRIFT: coverage_failed
```

> Canonical package root is **addon/bb8_core/**. Any root-level `bb8_core/` is forbidden and will be rejected by hooks.
