# Stabilization Port Roadmap - HA-BB8

## Status: Runtime ports complete

All runtime-critical features have been ported from the legacy HA-BB8
repo into the canonical ha-bb8-addon repo. The remaining deferred items
(PORT-05 through PORT-08) are development-quality improvements, not
runtime features.

## Completed ports

| Port | Description | PR | Status |
| ------ | ------------- | ----- | -------- |
| PORT-01 | Post-connect stabilization delay + LED holdoff | #21 | Merged |
| PORT-02 | BlueZ health monitoring and circuit breaker | #22 | Merged |
| PORT-03 | Estop ACK correctness | #23 | Merged |
| PORT-04 | Battery production-path fallback | #23 | Merged |

## Beyond-roadmap: Recovery stream

| Item | Description | PR | Status |
| ------ | ------------- | ----- | -------- |
| RECOVERY auth/capability | Supervisor + D-Bus capability validation | #24-#28 | Merged |
| RECOVERY primitive | Bounded host bluetooth restart via D-Bus | #29 | Merged |
| RECOVERY operator surface | One-shot trigger + README runbook | #30 | Merged |

## Deferred items

| Port | Description | Status | Notes |
| ------ | ------------- | -------- | ------- |
| PORT-05 | CI test enforcement | CI_HARDENED (PR #31, commit f659bb2) | Implemented in canonical repo. Collection errors are repaired; fast suite still has async-plugin/runtime test failures. |
| PORT-06 | Telemetry shape hardening | Deferred | Incremental; estop ACK fix covered critical path. |
| PORT-07 | ble_session test alignment | Deferred | Focused unit tests cover critical paths. |
| PORT-08 | Documentation alignment | Partially addressed | README runbook landed in PR #30. |

## Runtime validation note

A bounded runtime validation pass was attempted on canonical main after
the merged recovery stream. Evidence showed:
- deployed/runtime SHA parity matched canonical main
- connection-phase physical reaction was observed on retry
- logs contained:
  - mqtt_cmd_received
  - lighting_static_applied
  - facade_led_async_success

However:
- no facade_led_hw_result ok=true marker was captured
- no ble_session_led_write_timeout marker was captured
- operator did not reliably observe whether BB-8 turned green

Therefore this runtime validation should be treated as inconclusive /
operator-unconfirmed, not as a timeout classification.

## Legacy repo

- Path: /Users/evertappels/actions-runner/Projects/HA-BB8
- Status: Read-only reference. Do not PR from this repo.
