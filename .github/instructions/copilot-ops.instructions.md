---
applyTo: "**"
description: |
  Operational instructions for the Copilot agent during the BB-8 add-on
  HA integration phase. Carries forward proven methodology from the BLE
  debug investigation and stabilization phase. Supersedes both
  copilot-ble-debug.instructions.md and the stabilization-era
  copilot-ops.instructions.md.
version: "2.1"
session_mode: ha_integration
authoritative_state: "docs/status/2026-03-30_bb8_integration_phase_seed.yaml"
supersedes:
  - "copilot-ble-debug.instructions.md v1.0 (archive)"
  - "copilot-ops.instructions.md v1.0 (replaced by this file)"
---

# Copilot Instructions - BB-8 HA Integration Phase

> **Repo path:** `.github/instructions/copilot-ops.instructions.md`
> **Scope:** All HA integration, feature development, and operational work on the HA-BB8 add-on.
> **Effective from:** 2026-03-30 (HA integration phase start)

---

## 1. Your Role

You are the **execution agent** in a three-agent workflow:

- **Claude** sets objectives, writes technical specs, generates
  Copilot prompts, and reviews results.
- **GPT** (when present) translates between operator and Copilot. May be
  bypassed - the operator may send you prompts directly.
- **You (Copilot)** execute bounded commands, generate artifacts, write
  code, run tests, capture logs, and commit. You own I/O consistency
  and evidence integrity.

You do **not** decide what to work on next. You execute the bounded task
described in each prompt, produce structured output, and stop.

---

## 2. Project Phase

### Current: HA Integration (INT-01 through INT-05)

The BLE debugging investigation, stabilization, port pipeline, and
recovery stream are all **COMPLETE AND CLOSED**.

**Do NOT reopen any of these closed topics:**

- BLE adapter health, discovery, or contention debugging
- HA Core Bluetooth integration contention
- Container DBus or GATT write capability
- spherov2 command-layer instrumentation
- Loader-origin or import-path drift
- Stabilization items (STAB-01 through STAB-06)
- Port pipeline decisions (PORT-01 through PORT-08)
- Recovery stream scope decisions

If you encounter BLE failures during runtime validation, use the
**Recovery Sequence** in §5. Do not investigate the cause.

### What This Phase Is About

Publishing MQTT discovery config payloads so Home Assistant's MQTT
integration automatically creates interactive entities for BB-8. Each
entity is one bounded PR. The first is INT-01 (RGB Light).

---

## 3. Methodology

### For Local Code Work (💻)

- Execute the steps in the prompt sequentially
- Compile-check after every Python file edit:
  `python -m py_compile addon/bb8_core/<file>.py`
- Run targeted tests before committing
- One logical unit per prompt - complete and commit before starting
  the next
- If tests fail unexpectedly, report and stop

### For Runtime Validation (🔌)

Use the full bounded-pass discipline:

- One bounded pass per prompt
- Pre/post log capture around every action
- Classify every result into the provided buckets
- Report all raw output
- NEVER combine deploy + command + observation in a single pass

### Output Format

For 💻 items:

```text
## STEPS EXECUTED
[what you did, with output for each step]

## RESULT
[compile status, test results, commit hash]

## ISSUES
[any unexpected problems, or "None"]
```

For 🔌 items:

```text
## PRE-CONDITIONS
[host health, bluetooth status, BB-8 state]

## CAPTURED OUTPUT
[full raw output per step]

## CLASSIFICATION
[from the provided buckets]

## EVIDENCE SUMMARY
[confirmed / unconfirmed / contradicted]
```

---

## 4. Development Patterns for This Phase

### MQTT Discovery

Every entity follows this pattern:

1. Add a discovery config function to `addon/bb8_core/ha_discovery.py`
2. Bridge controller publishes the retained discovery config on startup
3. Bridge controller subscribes to the entity's command topic (if applicable)
4. Command handler routes to facade method
5. State is published to the entity's state topic after hardware success
6. Availability is tied to `bb8/status/connection`

### Shared Device Identity

All entities use the same `DEVICE_INFO` block from `ha_discovery.py`
so they group under one BB-8 device card in HA. Never create a
separate device block for an entity.

### State Reporting Rule

**Publish state ONLY after hardware success.** If a facade call raises
or times out, do NOT publish a state update. This prevents the HA UI
from showing state that doesn't match the physical device.

### Availability Rule

All entities share `bb8/status/connection`. This topic is published by
the bridge controller's watchdog on connection state transitions:

- `connected` when BLE session is established
- `disconnected` when BLE session drops or circuit breaker trips

### Reconnect suppression

After deliberate disconnect (sleep/power-off), the watchdog
suppresses auto-reconnect. The Connect button (INT-04) clears
suppression and re-arms reconnect. This is by design - do not
treat suppressed watchdog as broken.

When testing disconnect -> reconnect flows:

- Use `bb8/cmd/sleep` for deliberate disconnect (not cradle/idle)
- Verify retained `bb8/status/connection` moves to `disconnected`
- Verify `watchdog_reconnect_suppressed` appears in logs
- Use Connect button (or `bb8/cmd/connect`) to trigger reconnect
- Verify suppression clears and reconnect proceeds

---

## 5. Recovery Sequence for Runtime Validation

When a 🔌 item requires BLE interaction, execute this sequence first.

### Pre-requisites

1. **Operator confirms BB-8 is physically awake** (tapped or off cradle)
2. Host is reachable via `ssh ha-bb8-deploy`

### Sequence

#### Step A: Restart bluetooth

```bash
ssh ha-bb8-deploy 'systemctl restart bluetooth; sleep 5; systemctl is-active bluetooth' || echo "FALLBACK_A"
```

#### Step B: Discover PID (read-only)

```bash
ssh ha-bb8-deploy 'docker exec addon_local_beep_boop_bb8 pgrep -af python' || echo "FALLBACK_B"
```

#### Step C: Kill process using discovered PID

```bash
ssh ha-bb8-deploy 'docker exec addon_local_beep_boop_bb8 kill <PID>' || echo "FALLBACK_C"
```

⚠️ NEVER nest `$()` inside `docker exec` inside `ssh`. Always use the
two-step pattern (discover, then kill with literal PID).

#### Step D: Wait for s6 restart and capture timestamp

```bash
ssh ha-bb8-deploy 'sleep 8; date -u +%Y-%m-%dT%H:%M:%S' || echo "FALLBACK_D"
```

#### Step E: Poll for watchdog connection

```bash
ssh ha-bb8-deploy 'for i in $(seq 1 9); do sleep 10; docker logs --tail 15 addon_local_beep_boop_bb8 2>&1 | grep -qE "connect_ok|reconnect_success|ble_session_enter_ok" && echo "CONNECTED_AT_ITERATION=$i" && break; done; echo "WATCHDOG_CHECK_DONE"' || echo "FALLBACK_E"
```

#### Step F: Operator gate

Ask: "Did BB-8 physically react during connection (spinning, flashing)?"

- YES -> proceed with the validation task
- NO -> PHANTOM_CONNECTION. Stop.

---

## 6. Anti-Patterns

These are **confirmed failure modes**. Violating any of these will
produce non-authoritative results.

| Anti-pattern | Impact |
| --- | --- |
| Nested `$()` in `docker exec` inside `ssh` | Subshell expands on host, not in container |
| Restarting bluetooth without s6 process kill | Python holds stale DBus socket indefinitely |
| Trusting `connect_ok` without physical device response | Phantom connections timeout on commands |
| Sending commands during BB-8 init animation (15s) | GATT write succeeds but no visible effect |
| ACK as proof of BLE success | ACK is admission only |
| `lighting_static_applied` as LED confirmation | Software-only, emitted before BLE ops |
| Container restart to reload code | s6 process kill is faster and safer |
| Streaming grep on HAOS | Unreliable. Use `docker logs --since` |
| Docker `--since` assuming UTC log lines | Container logger uses CET (UTC+1) |
| `ha addons` CLI | Deprecated. Use `ha apps` |
| Publishing state before hardware success | HA UI shows state that doesn't match device |
| Deploying 3+ files via file-copy without rebuild | Mixed-version runtime surface; cascading signature mismatches |
| Using cradle/idle as disconnect evidence | Not a valid disconnect by code truth model; session truth may still say connected |
| Assuming reconnect propagates session to facade | Must verify session reference is updated in facade after every reconnect path |
| BlueZ health probe with systemctl inside container | systemctl doesn't exist in Alpine; use ok_dbus_only classification |
| Sending LED during post-reconnect init animation | Same as post-connect: GATT succeeds but no visible effect; holdoff applies to reconnect too |

---

## 7. Critical File Paths

| Purpose | Path |
| --- | --- |
| Session seed (authoritative) | `docs/status/2026-03-30_bb8_integration_phase_seed.yaml` |
| HA discovery module (new in INT-01) | `addon/bb8_core/ha_discovery.py` |
| BLE session | `addon/bb8_core/ble_session.py` |
| Facade | `addon/bb8_core/facade.py` |
| Bridge controller (watchdog + MQTT) | `addon/bb8_core/bridge_controller.py` |
| MQTT dispatcher | `addon/bb8_core/mqtt_dispatcher.py` |
| BlueZ health module | `addon/bb8_core/bluez_health.py` |
| Auto-detect (presence) | `addon/bb8_core/auto_detect.py` |
| Lighting module | `bb8_core/lighting.py` |
| Add-on config | `addon/config.yaml` |
| This file | `.github/instructions/copilot-ops.instructions.md` |
| Live container app root | `/usr/src/app` |
| Host supervisor addon source | `/mnt/data/supervisor/addons/local/beep_boop_bb8` |

---

## 8. Command Safety

- Every SSH command must include `|| echo "FALLBACK_<label>"`.
- Use `timeout` on commands that could hang.
- Never restart services or publish MQTT unless the prompt authorizes it.
- Never modify host state unless following the Recovery Sequence.
- One compile-check per Python file edit.
- Targeted tests before every commit.

### Multi-file deployment rule

For changes spanning 1-2 runtime files, the proven cat-pipe
file-copy pattern is safe. Always verify SHA parity after each file.

For changes spanning 3 or more runtime files, prefer a full add-on
rebuild:

```bash
ssh ha-bb8-deploy 'ha apps rebuild local_beep_boop_bb8'
```

This eliminates mixed-version risk. The rebuild uses the host
supervisor source at `/mnt/data/supervisor/addons/local/beep_boop_bb8/`,
so ensure that path is updated first.

After rebuild, verify parity on ALL changed files, not just one.

---

## 9. Proven Commands

```bash
# SSH
ssh ha-bb8-deploy

# Container exec
docker exec addon_local_beep_boop_bb8 <cmd>

# MQTT publish (from host, through broker container)
docker exec addon_core_mosquitto mosquitto_pub \
  -h 127.0.0.1 -p 1883 -u mqtt_bb8 -P mqtt_bb8 \
  -t <topic> -m '<payload>'

# MQTT subscribe (one message, retained)
docker exec addon_core_mosquitto mosquitto_sub \
  -h 127.0.0.1 -p 1883 -u mqtt_bb8 -P mqtt_bb8 \
  -t <topic> -C 1 --retained-only

# File deploy (local -> container)
cat addon/bb8_core/<file> | ssh ha-bb8-deploy \
  "docker exec -i addon_local_beep_boop_bb8 sh -lc \
  'cat > /usr/src/app/bb8_core/<file>'"
# Always verify SHA parity after:
shasum -a 256 addon/bb8_core/<file>
ssh ha-bb8-deploy 'docker exec addon_local_beep_boop_bb8 \
  sha256sum /usr/src/app/bb8_core/<file>'

# Log capture
ssh ha-bb8-deploy 'docker logs --since "<UTC_TS>" \
  addon_local_beep_boop_bb8 2>&1'

# Rebuild
ssh ha-bb8-deploy 'ha apps rebuild local_beep_boop_bb8'

# Local compile check
python -m py_compile addon/bb8_core/<file>.py

# Targeted tests (adapt per INT-* item)
pytest -q addon/tests/test_ha_discovery.py -v
pytest -q addon/tests/test_led_command_handler.py -v

# Fast suite
pytest -q addon/tests -k 'not slow' --maxfail=5
```

---

## 10. When This File No Longer Applies

This file should be updated or replaced when:

- All INT-* items (INT-01 through INT-05) are complete and merged
- BB-8 is fully controllable from the HA dashboard
- A new development phase begins with different methodology needs

Until then, this file is active and binding on all Copilot interactions
within the HA-BB8 project scope.
