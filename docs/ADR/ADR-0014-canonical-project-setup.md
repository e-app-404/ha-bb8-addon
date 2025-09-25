---
title: "ADR-0014: Canonical Project Setup for HA-BB8 Addon"
date: 2025-09-11
status: Proposed
author:
  - Promachos Governance
related:
  - ADR-0001
  - ADR-0012
  - ADR-0013
supersedes: []
last_updated: 2025-09-11
references:
  - Makefile (root)
  - Makefile (addon shim)
  - coverage_gate.py
  - bleep_run.py
---

# ADR-0014: Canonical Project Setup for HA-BB8 Addon

## Context

The HA-BB8 repository previously contained multiple Makefiles and developer/CI targets, leading to duplication, override warnings, and inconsistent build/test flows. Supporting files (e.g., coverage gate, bleep runner) were scattered or referenced inconsistently. This ADR establishes a single, canonical Makefile at the repository root, with a forwarding shim in `addon/Makefile`, and anchors the supporting file structure and format.

## Decision

- The root `Makefile` is the authoritative build, test, and CI entrypoint for the repository.
- All developer, CI, and QA targets are defined in the root Makefile.
- The `addon/Makefile` is a forwarding shim, delegating all targets to the root Makefile.
- Supporting files and directories are anchored as follows:
  - `addon/tools/coverage_gate.py`: Coverage enforcement script
  - `addon/tools/__init__.py`: Ensures `addon.tools` is a package
  - `addon/tools/bleep_run.py`: FakeMQTT LED bleep runner
  - `reports/`: All test, coverage, and audit logs
  - `requirements.txt`, `requirements-dev.txt`: Dependency management
- All Makefile variables, file/folder references, and target definitions are up-to-date and consistent.
- Redundant comments, unused variables, and duplicate targets are removed.
- Future addenda may anchor other supporting files (e.g., `pyproject.toml`, `ruff.toml`, `mypy.ini`).

## Consequences

- Eliminates override warnings and build/test confusion.
- Ensures maintainable, future-proof build and test flows.
- Anchors supporting file structure for governance and onboarding.
- Enables future extension for additional configuration files.

## References
- [ADR-0001: Repository Structure and Governance](ADR-0001.md)
- [Makefile (root)](../../Makefile)
- [Makefile (addon shim)](../../addon/Makefile)
- [coverage_gate.py](../../addon/tools/coverage_gate.py)
- [bleep_run.py](../../addon/tools/bleep_run.py)

## Token Blocks

```yaml
TOKEN_BLOCK:
  accepted:
    - CANONICAL_MAKEFILE_OK
    - SUPPORTING_FILES_OK
    - PROJECT_SETUP_OK
  drift:
    - DRIFT: makefile_invalid
    - DRIFT: supporting_files_missing
    - DRIFT: project_setup_failed
```
