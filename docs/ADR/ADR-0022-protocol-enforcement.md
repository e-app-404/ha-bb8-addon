---
id: ADR-0022
title: "Protocol Enforcement (Topics, Imports, Shape)"
date: 2025-09-15
status: Accepted
author:
  - "Evert Appels"
  - "Strategos GPT"
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