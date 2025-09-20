---
title: "ADR-0011: Supervisor-only Operations"
date: 2025-08-27
status: Accepted
author:
  - Promachos Governance
related:
  - ADR-0001
  - ADR-0010
supersedes: []
last_updated: 2025-09-03
---

# ADR-0011: Supervisor-only Operations

## Table of Contents
1. Context
2. Decision
3. Enforcement
4. Tokens
5. Last updated

## Context
On some hosts, docker CLI is unavailable or the add-on container isn’t visible by name. Diagnostics must not rely on `docker exec/ps`. This ADR establishes a Supervisor-only operational mode for the HA-BB8 add-on, ensuring all diagnostics and health checks are accessible via Supervisor logs and the `ha` CLI.

## Decision
All operational visibility is emitted to Supervisor logs (`ha addons logs`). `run.sh` prints DIAG and 15s health summaries to stdout; Python emits heartbeats; an optional file-to-stdout forwarder mirrors key Python lines. All runbooks and operational workflows use the `ha` CLI, avoiding container-internal flags and direct docker access.

## Enforcement
- All diagnostics, health checks, and respawn drills must be verifiable solely from Supervisor logs and the `ha` CLI.
- No operational dependency on `docker exec`, `docker ps`, or direct container shell access.
- Documentation and runbooks must reflect Supervisor-only workflows.
- Automated tests and attestation scripts must parse Supervisor logs for health and DIAG tokens.

## Tokens
- `HEALTH_SUMMARY` — emitted every 15s by run.sh, includes heartbeat ages.
- `RUNLOOP attempt #N` — run.sh emits for each supervised restart.
- `Started bb8_core.main PID=…` — confirms main process start.
- `Started bb8_core.echo_responder PID=…` — confirms echo responder start.
- `Connected to MQTT` / `Subscribed to bb8/echo/cmd` — confirms MQTT event handling.
- All tokens are visible in Supervisor logs via `ha addons logs`.

## Token Blocks

```yaml
TOKEN_BLOCK:
  accepted:
    - HEALTH_SUMMARY_OK
    - RUNLOOP_OK
    - MAIN_PROCESS_STARTED_OK
    - ECHO_RESPONDER_STARTED_OK
    - MQTT_CONNECTED_OK
  drift:
    - DRIFT: health_summary_missing
    - DRIFT: runloop_failed
    - DRIFT: main_process_failed
    - DRIFT: echo_responder_failed
    - DRIFT: mqtt_connection_failed
```