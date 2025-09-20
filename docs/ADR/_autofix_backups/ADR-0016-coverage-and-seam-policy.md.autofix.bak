---
title: "ADR-0016: Coverage & seam policy"
date: 2025-09-12
status: Accepted
author:
  - Promachos Governance
related:
  - ADR-0012
supersedes: []
last_updated: 2025-09-12
---

# ADR-0016: Coverage & seam policy

## Context
We require reliable coverage without real IO/threads/network. Seams were missing in some modules.

## Decision
- **Coverage**: single driver (`pytest-cov`); repo fail-under ≥70%; high-priority per-file gates ≥90%.
- **Seams**: Do not change production solely for tests. Use local shims via `monkeypatch`/fakes in tests.
- **Network**: No real network in CI. Net tests are conditionally xfailed behind `ALLOW_NETWORK_TESTS=1`.

## Consequences
Deterministic tests; PRs that break gates are rejected.


## Enforcement
- `.coveragerc` at repo root, coverage gate script (`tools/coverage_gate.py`).
- GitHub Actions workflow runs tests + gate on every PR.

## Token Blocks

```yaml
TOKEN_BLOCK:
  accepted:
    - COVERAGE_POLICY_OK
    - SEAMS_OK
    - NETWORK_TESTS_OK
  drift:
    - DRIFT: coverage_policy_failed
    - DRIFT: seams_missing
    - DRIFT: network_tests_failed
```