# Recovery Stream Closeout

## Status: Complete (manual/operator-triggered scope)

Date: 2026-03-30

## What was implemented

The HA-BB8 add-on can now detect dead bluetoothd (BlueZ circuit
breaker) and provides a manual recovery primitive that restarts
bluetooth on the host via D-Bus from inside the container.

### Components

- bb8_core/bluez_health.py - BlueZ health probing, circuit breaker
- bb8_core/recovery_capability_probe.py - Supervisor/D-Bus capability detection
- bb8_core/host_bluetooth_recovery.py - bounded restart primitive + operator CLI

### Execution path

- Supervisor Host API: read/capability only (control endpoints return 404)
- D-Bus via busctl (elogind): working execution path for bluetooth restart

### Operator surface

- CLI: python -m bb8_core.host_bluetooth_recovery
- README runbook documents preconditions, invocation, expected output

## What was explicitly NOT implemented

- Autonomous/watchdog-triggered recovery: Rejected as too risky in
  current architecture. Host service restart without operator awareness
  could mask real problems or cause cascading failures.
- Supervisor-based host service control: Not available on current
  HAOS build. If future HAOS versions expose this, the capability probe
  will detect it automatically.

## Future work (separate project, not started)

If autonomous recovery is desired, it requires a separate bounded
design phase covering:

- Failure-mode analysis (restart loops, interference with other BLE devices)
- Cooldown and rate-limiting guarantees
- Operator notification before and after autonomous action
- Rollback/safe-state behavior if restart fails

This is a new project, not a continuation of the current recovery stream.
