---
id: ADR-0010
title: Unified Supervision & DIAG Instrumentation
date: 2025-09-03
status: Accepted
decision: 1. Enforce single control-plane via run.sh for both bb8_core.main and bb8_core.echo_responder.
author:
- Promachos Governance
related:
- ADR-0001
- ADR-0008
supersedes: []
last_updated: 2025-09-03
---

# ADR-0010 — Unified Supervision & DIAG Instrumentation

## Context
The add-on experienced rapid restart loops and low observability due to non-blocking entrypoints, multi-control-plane supervision, and fragile path handling.

## Decision
1. Enforce single control-plane via `run.sh` for both `bb8_core.main` and `bb8_core.echo_responder`.  
2. Emit deterministic DIAG events for runloop attempts, process starts, and child exits; persist to `/data/reports/ha_bb8_addon.log`.  
3. Enable health heartbeats to `/tmp/bb8_heartbeat_main` and `/tmp/bb8_heartbeat_echo` gated by `enable_health_checks`.  
4. Normalize log paths, create parent dirs, and fallback to `/data` then `/tmp`.  
5. Set default restart backoff to 5s; unlimited restarts with manual kill switch `/tmp/bb8_restart_disabled`.

## Consequences
- Rapid restart loops are contained and observable; child death causes recorded respawn.
- Operators obtain clear acceptance signals for liveness and supervision.
- Path handling is consistent with HA volume semantics.


## Rollout
- Patch `run.sh`, service wiring, options schema; ship docs and runbooks.
- Validate via HA host diagnostics (process PIDs, DIAG lines, heartbeats, respawn drill).

## Token Blocks

```yaml
TOKEN_BLOCK:
  accepted:
    - DIAG_EVENT_OK
    - SUPERVISION_OK
    - HEALTH_HEARTBEAT_OK
    - CLEAN_RESTART_OK
  drift:
    - DRIFT: supervision_failed
    - DRIFT: diag_event_missing
    - DRIFT: health_heartbeat_missing
```