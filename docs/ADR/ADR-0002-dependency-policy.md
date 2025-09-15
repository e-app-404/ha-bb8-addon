---
title: "ADR-0002: Dependency & Runtime Compatibility Policy"
date: 2025-08-22
status: Accepted
author:
  - Promachos Governance
related:
  - ADR-0001
  - ADR-0003
supersedes: []
last_updated: 2025-09-13
---

# ADR-0002: Dependency & Runtime Compatibility Policy

## Decision
- Pin **paho-mqtt** to **>= 2.0, < 3.0**. Code MUST pass `callback_api_version=CallbackAPIVersion.VERSION1`
  to `mqtt.Client(...)` until a planned migration to v2 callbacks occurs.
- Pin **PyYAML** to **>= 6.0.1** to guarantee `yaml` availability across dev/test/runtime.
- Development environment uses a project-local virtual environment (`.venv`) and installs
  both `addon/requirements.txt` (runtime) and `addon/requirements-dev.txt` (dev/test).

## Rationale
- `paho.mqtt.enums` is required by current code; it exists only in paho-mqtt v2+.
- Explicit callback API selection preserves backward-compatible handler signatures.

## Consequences
- Tests and runtime are aligned; import errors for `paho.mqtt.enums` are eliminated.
- Future migration to v2 callbacks is tracked as a deliberate change.

## Acceptance
- `addon/requirements.txt` contains `paho-mqtt>=2.0,<3.0` and `PyYAML>=6.0.1`.
- Grep of code shows `callback_api_version=CallbackAPIVersion.VERSION1` wherever `mqtt.Client(...)` is constructed.

## Token Blocks
```yaml
TOKEN_BLOCK:
  accepted:
    - DEPENDENCY_POLICY_OK
    - CALLBACK_API_VERSION_OK
  drift:
    - DRIFT: dependency_invalid
    - DRIFT: callback_api_version_missing
```
