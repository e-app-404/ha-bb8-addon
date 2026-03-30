# BB-8 Home Assistant Add-on

This directory contains the Home Assistant add-on subtree for the BB-8 integration.

- Canonical topics: `bb8/cmd/*`, `bb8/ack/*` with `{ok,cid,echo}`, `bb8/status/telemetry`
- Governance, evidence, and acceptance receipts live in the workspace repository
- Runtime writes: `/data/**` (container); evidence on host under `/config/ha-bb8/**`

See the workspace repo PR comments for the latest acceptance receipt and SHA.

## Operator One-Shot Recovery Trigger

The host bluetooth restart primitive is intentionally manual-only.
It is not wired into recurring watchdog loops.

### Preconditions

- Add-on option `enable_host_bluetooth_restart_recovery` must be `true`
- Add-on option `bluetooth_restart_cooldown_s` should remain at a safe value
- Operator has a clear reason for exactly one recovery attempt

### Exact invocation

Run inside the add-on container:

```bash
python3 -m bb8_core.host_bluetooth_recovery --reason "operator_manual_trigger"
```

The command emits a single JSON payload containing:

- `config_source`
- `effective_enabled`
- `cooldown_s`
- `result` (status/path/classification)
- `emitted_events`

### Stop conditions

- Execute once per operator decision
- Do not loop/retry automatically
- If result is `skipped_cooldown` or `skipped_disabled`, stop and resolve config/operations state first

### Post-invocation checks

- Capture the returned JSON payload
- Capture bounded add-on logs around the invocation timestamp
- Record whether path was `dbus` fallback or another classification
