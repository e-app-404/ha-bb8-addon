---
title: "ADR-0022: Protocol Enforcement (Topics, Imports, Shape)"
date: 2025-09-15
status: Accepted
author:
  - Evert Appels
  - Strategos GPT
related: []
supersedes: []
last_updated: 2025-09-15
---

# ADR-0022: Protocol Enforcement (Topics, Imports, Shape)

## Context

## Enforced Rules
1. **Imports:** Only `addon.bb8_core` is allowed. Bare `bb8_core` imports are forbidden.
2. **Topics:** No MQTT wildcards (`#` or `+`) in cmd/state/discovery topics.
3. **Repo Shape:** No prod packages at repo root: `bb8_core/`, `services.d/`, `tools/`.
4. **Coverage:** Ratcheted gate ≥ 70%; cannot regress in mainline.
5. **Snapshots:** `_backups` tarball policy only on change thresholds.

## Enforcement
- Pre-commit hook (fast grep-based) blocks violations.
- CI workflow (`protocol.yml`) runs `ops/guardrails/protocol_enforcer.sh` with fail-fast.


## Token Blocks

Note: validators and guard scripts live under `ops/guardrails/`. Run `ops/guardrails/protocol_enforcer.sh` to execute the working-area validators. Tests live under `ops/guardrails/tests/`.

## Decision (addendum)

```yaml
TOKEN_BLOCK:
  accepted:
    - PROTOCOL_GUARD_ENABLED
    - COVERAGE_FLOOR_70
    - ADR0009_VALIDATION_ON
    - LEGACY_RUNTIME_GATED
  requires:
    - ADR_SCHEMA_V1
  drift:
    - DRIFT: legacy_runtime_subscription_detected
```
## Decision (addendum)

- No MQTT wildcards in configured topics; sanitize to safe literals.
- HA discovery JSON **must not** include broker-publish options (e.g., `retain`).
- MQTT Button `payload_press` is static; no templating in discovery JSON.
- Three `mqtt.number` entities (`speed`, `heading`, `duration_ms`) publish to simple numeric topics; controller composes JSON on `cmd/drive`.
- Discovery publishes are sent with `retain=True` at publish time.
- Coverage gate floor remains **70%** (ratchet later).
