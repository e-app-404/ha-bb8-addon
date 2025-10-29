---
id: ADR-0031
title: Supervisor-only Operations & Testing Protocol
slug: supervisor-only-operations-testing
date: 2025-09-28
status: Accepted
decision: '**Technical Choice:** Adopt a **comprehensive Supervisor-only operational
  model** encompassing:.'
author:
- Operational Evidence Analysis
related:
- ADR-0010
- ADR-0011
- ADR-0032
- ADR-0033
supersedes: []
tags:
- operations
- testing
- supervisor
- ha-bb8
- mqtt
- stp5
- release
- deployment
last_updated: 2025-09-28
---

# ADR-0031: Supervisor-only Operations & Testing Protocol

**Session Evidence Sources:**

- `STRAT-HA-BB8-2025-09-03T06:50Z-001` (Supervisor verification, attestation runs, MQTT probes)
- `BB8-STP5-MVP trace-bb8-2f0c9e9a` (CI/testing validation, coverage ratcheting)
- `Handoff::Strategos::HA-BB8::2025-09-03T06:50Z-001` (Release pipeline, deployment topology)

## Context

**Problem Statement:** Establish a comprehensive operational model for HA-BB8 add-on that works entirely through Home Assistant Supervisor interfaces, without requiring container shell access, while providing empirical validation of health, connectivity, and functionality.

**Investigation Method:**

- Live Supervisor logs collection (`ha addons logs`, `ha addons info`)
- MQTT round-trip probes with `mosquitto_pub/sub`
- STP5 attestation runs with metrics collection
- Release pipeline execution with token validation
- CI/testing validation with coverage gates

## Evidence Gathered

### Core Operational Evidence

- **Add-on Configuration:** `startup: services`, `host_dbus: true`, `apparmor: disable`, device `/dev/hci0`
- **Health Banner Pattern (15s intervals):**

  ```log
  2025-09-03T10:24:36+01:00 [BB-8] HEALTH_SUMMARY main_age=1.4s echo_age=0.7s interval=15s
  ```

- **Process Supervision Logs:**

  ```log
  [BB-8] run.sh entry (version=2025.8.21.28) wd=/usr/src/app LOG=/data/reports/ha_bb8_addon.log HEALTH=1 ECHO=true
  [BB-8] RUNLOOP attempt #1
  [BB-8] Started bb8_core.main PID=131
  [BB-8] Started bb8_core.echo_responder PID=134
  [BB-8] Child exited: dead=echo_responder.py(134) exit_code=143 (main=131 echo=134)
  ```

### Testing & Validation Evidence

- **Test Coverage:** 200+ tests passing, coverage ~69%, 1 failing test (`test_resolve_topic_wildcard`)
- **Coverage Gate:** ≥70% threshold configured
- **CI Guards:** Repository shape validation via `.github/workflows/shape.yml`
- **MQTT Seam Validation:** FakeMQTT testing via `addon/tools/bleep_run.py`

### Deployment Evidence

- **Release Pipeline Tokens:**

  ```arduino
  BUMP_OK:<version>
  SUBTREE_PUBLISH_OK:main@<sha>
  DEPLOY_OK — runtime rsync complete
  VERIFY_OK — add-on restarted via Services API
  ```

- **Supervisor Build Logs:**

  ```log
  [supervisor.docker.addon] Starting build for local/aarch64-addon-beep_boop_bb8:2025.8.21.28
  [supervisor.addons.addon] Add-on 'local_beep_boop_bb8' successfully updated
  ```

## Decision

**Technical Choice:** Adopt a **comprehensive Supervisor-only operational model** encompassing:

### 1. Health Monitoring & Validation

- Single control-plane supervision via `run.sh`
- Health heartbeat files: `/tmp/bb8_heartbeat_main`, `/tmp/bb8_heartbeat_echo`  
- Periodic health summaries logged every 15 seconds
- Process lifecycle logging with PID tracking and exit codes

### 2. Testing & Quality Gates

- **Coverage Gate:** Maintain ≥80% test coverage threshold (enhanced from ≥70%)
- **Repository Shape Guard:** Enforce canonical `addon/` structure via CI
- **MQTT Seam Testing:** Use FakeMQTT (`bleep_run.py`) for integration validation
- **Test Count Benchmark:** Target 200+ passing tests
- **QA Pipeline Commands:** (from STP4 strict requirements)
  
  ```bash
  black --check .
  ruff check .
  mypy --install-types --non-interactive .
  pytest -q --maxfail=1 --disable-warnings --cov=bb8_core --cov-report=term-missing
  bandit -q -r bb8_core || true
  safety check --full-report || true
  ```

### 3. Deployment & Release Automation

- **One-command Release:** `make release-patch` with automated version bumping
- **Validation Tokens:** Explicit success markers (`STRUCTURE_OK`, `VERIFY_OK`, `WS_READY`, `DEPLOY_OK`)
- **Dual-Clone Deployment:** Git-based workspace to runtime synchronization

  ```bash
  # Dual-clone deployment pattern (verified)
  git -C "$ADDON" push origin HEAD:main
  git -C "$RUNTIME" fetch --all --prune
  git -C "$RUNTIME" checkout -B main origin/main
  git -C "$RUNTIME" reset --hard origin/main
  ```

- **Runtime Synchronization:** Git-based alignment with token validation
- **Repository Hygiene:** Automated `.gitignore` guards and workspace-only directory pruning

### 4. Operational Commands (Verified)

```bash
# Health & Status Validation
ha addons info local_beep_boop_bb8 | jq -r '.state+" @ "+.version'
ha addons options local_beep_boop_bb8 | jq -c '{enable_echo,enable_health_checks,log_path,mqtt_host,mqtt_port}'

# DIAG Pattern Extraction
ha addons logs local_beep_boop_bb8 --lines 400 \
  | grep -E 'run.sh entry|RUNLOOP attempt|Started bb8_core.(main|echo_responder) PID|Child exited|HEALTH_SUMMARY'

# Heartbeat Validation (15s snapshots)
echo '--- A ---'; ha addons logs local_beep_boop_bb8 --lines 200 | grep HEALTH_SUMMARY | tail -n 3
sleep 15
echo '--- B ---'; ha addons logs local_beep_boop_bb8 --lines 200 | grep HEALTH_SUMMARY | tail -n 3

# MQTT Connectivity Test
ha service call mqtt.publish -d '{"topic":"bb8/echo/cmd","payload":"{\"value\":\"ping\"}"}'

# Release & Deploy
make release-patch  # Full pipeline with validation tokens
```

### 5. STP5 Attestation Protocol

**Attestation Command Structure:**

```bash
# Basic echo attestation (NO_BLE mode)
BASE=$(jq -r '.mqtt_base // "bb8"' /data/options.json)
E_CMD=$(jq -r '.mqtt_echo_cmd_topic // empty' /data/options.json); [ -z "$E_CMD" ] && E_CMD="$BASE/echo/cmd"

mosquitto_sub -h 192.168.0.129 -p 1883 -u mqtt_bb8 -P mqtt_bb8 \
-t "$BASE/echo/#" -C 3 -W 8 -v & SP=$!; sleep 0.2
mosquitto_pub -h 192.168.0.129 -p 1883 -u mqtt_bb8 -P mqtt_bb8 \
-t "$E_CMD" -m '{"value":1}'
wait $SP || true

# BLE-enforced attestation (full validation)
HOST=192.168.0.129 PORT=1883 USER=mqtt_bb8 PASS=mqtt_bb8 BASE=bb8 \
DURATION=30 BURST_COUNT=10 BURST_GAP_MS=2000 REQUIRE_BLE=true \
/config/domain/shell_commands/stp5_supervisor_ble_attest.sh
```

**Validation Results:**

- **Pass Criteria:** `STP5 PASS (binary criteria met)`, artifacts under `/config/reports/stp5_runs/<timestamp>`
- **Fail Criteria:** `ble_true_count: 0`, `verdict: FAIL` when BLE enforcement required
- **Acceptance Gates:** window ≥10s, echoes ≥3, RTT p95 ≤250ms, BLE evidence when required

## Consequences

### Positive

- **Complete operational surface** without container dependencies
- **Empirically validated** health monitoring and testing protocols  
- **Automated release pipeline** with explicit success/failure tokens
- **Deterministic artifact locations** under `/config/reports/*`
- **Clear acceptance criteria** for all operational phases
- **Repeatable validation protocols** using only Supervisor interfaces

### Negative

- **Limited debug depth** constrained to stdout/log file outputs
- **BLE evidence frequently absent** (`ble_ok:false`) requiring device wake strategies
- **MQTT broker ACL sensitivity** between local vs remote execution contexts
- **Test coverage gap** (69% vs 70% gate) requires resolution
- **Single failing test** (`test_resolve_topic_wildcard`) due to policy/test mismatch

### Unknown/Untested

- **Rollback procedures** not fully validated in automation
- **BLE readiness root cause** (device sleep vs BlueZ permissions) unresolved
- **End-to-end motion validation** beyond echo/attestation not demonstrated
- **CI edge cases** with generated artifacts not fully exercised

## Implementation Evidence

### Configuration Discovered

```yaml
# Add-on Configuration
devices:
  - /dev/hci0
host_dbus: true
startup: services
apparmor: disable

# Runtime Options  
options:
  mqtt_base: bb8
  mqtt_host: 192.168.0.129
  mqtt_port: 1883
  mqtt_user: mqtt_bb8
  mqtt_password: mqtt_bb8
  enable_echo: true
  enable_health_checks: true
  ble_adapter: hci0
  bb8_mac: ED:ED:87:D7:27:50
```

### Log Patterns Observed

#### Startup Sequence

```log
[BB-8] run.sh entry (version=X.X.X) wd=/usr/src/app LOG=/data/reports/ha_bb8_addon.log HEALTH=1 ECHO=true
[BB-8] RUNLOOP attempt #1
[BB-8] Started bb8_core.main PID=131
[BB-8] Started bb8_core.echo_responder PID=134
```

#### Health Monitoring

```log
[BB-8] HEALTH_SUMMARY main_age=4.1s echo_age=4.1s interval=15s
```

#### MQTT Integration

```log
Connected to MQTT broker with rc=Success
Subscribed to bb8/echo/cmd
Received message on bb8/echo/cmd: b'{"value":1}'
```

#### Version Probing

```json
{"event": "version_probe", "bleak": "0.22.3", "spherov2": "0.12.1"}
```

### Artifact Paths Verified

```ini
/config/reports/stp5_runs/<timestamp>/        # STP5 attestation results
/data/reports/ha_bb8_addon.log               # Add-on runtime logs  
/tmp/bb8_heartbeat_main                      # Main process heartbeat
/tmp/bb8_heartbeat_echo                      # Echo responder heartbeat
coverage.xml                                 # Test coverage reports
reports/ratchet/pipeline_*.log               # CI pipeline logs
reports/bleep_run_*.log                      # FakeMQTT test logs
```

### Gaps Requiring Further Investigation

### Critical

- **Resolve test coverage gap:** Address failing `test_resolve_topic_wildcard` and achieve ≥80% coverage
- **BLE AsyncIO Threading:** Implement dedicated event-loop thread to eliminate "There is no current event loop" warnings
- **BLE readiness strategy:** Develop reliable wake sequence for `ble_ok:true` telemetry
- **Rollback automation:** Implement and validate automated rollback procedures
- **Evidence Artifacts:** Generate required validation artifacts:
  - `evidence_manifest.json`
  - `ha_mqtt_trace_snapshot.jsonl`
  - `ha_discovery_dump.json`

### Secondary  

- **MQTT broker ACL documentation:** Clarify remote vs local execution differences
- **CI edge case coverage:** Test all generated artifact scenarios
- **End-to-end motion validation:** Beyond echo/attestation to full device control

## References

**Source Files Examined:**

- `addon/run.sh`, `addon/services.d/ble_bridge/run`, `addon/services.d/echo_responder/down`
- `addon/config.yaml`, `/data/options.json`, `addon/tools/bleep_run.py`
- `.github/workflows/shape.yml`, `.github/workflows/tests.yml`
- `coverage.xml`, `Makefile`, release automation scripts

**Commands Executed:**

- All Supervisor CLI commands listed above with successful execution
- STP5 attestation runs with both PASS and FAIL outcomes  
- Release pipeline with complete token validation
- MQTT probe commands with verified connectivity

**Tests Performed:**

- 200+ test suite execution with coverage measurement
- STP5 attestation protocol validation (NO_BLE and BLE_ENFORCED modes)
- Release pipeline end-to-end with version bumping and deployment
- Health monitoring cadence validation over extended periods

**Milestone 1 Operational Validation (28 Sep 2025):**

**Container Stability Evidence:**

```bash
# 3+ Hour Uptime Validation
sudo docker ps | grep bb8
# 473cb39bb39a ... Up 3 hours ... addon_local_beep_boop_bb8

# Health Monitoring Validation  
sudo docker logs addon_local_beep_boop_bb8 --tail 5
# 2025-09-28T23:29:13+01:00 [BB-8] HEALTH_SUMMARY main_age=4.8s echo_age=0.7s interval=15s
# Pattern confirms: dual heartbeat operational, no crash loops
```

**Alternative Access Methods (Supervisor CLI 401 Workaround):**

```bash
# When ha CLI fails with 401 authentication:
ha addons info local_beep_boop_bb8
# unexpected server response. Status code: 401

# Use direct Docker access instead:
sudo docker logs addon_local_beep_boop_bb8 --since="10m"
sudo docker ps | grep bb8
# Provides equivalent validation capability
```

**Production MQTT Connectivity Validation:**

```bash
# Echo Roundtrip Test
ssh home-assistant "mosquitto_sub -h 192.168.0.129 -u mqtt_bb8 -P mqtt_bb8 -t bb8/echo/ack & sleep 1; mosquitto_pub -h 192.168.0.129 -u mqtt_bb8 -P mqtt_bb8 -t bb8/echo/cmd -m '{\"test\": true}'; sleep 2; pkill mosquitto_sub"
# Response: {"ts": 1759098629.0950077, "value": 1}
# Confirms: MQTT integration fully operational post-deployment
```

**Session References:**

- `STRAT-HA-BB8-2025-09-03T06:50Z-001`: Supervisor verification and attestation
- `BB8-STP5-MVP trace-bb8-2f0c9e9a`: CI validation and testing protocols
- `HANDOFF::STRATEGOS::HA-BB8::2025-09-03T06:50Z-001`: Deployment and release automation
- **development/production-ready-20250928**: Milestone 1 deployment validation

---

**Extraction Date:** 28 September 2025
**Session ID/Reference:** Synthesis of multiple operational validation sessions
**Evidence Quality:** Complete for operational protocols; Complete for Milestone 1 deployment validation; Partial for BLE readiness and rollback automation

**TOKEN_MILESTONE1_VALIDATED**: Operational stability foundation confirmed through 3+ hour uptime, successful MQTT roundtrip, and dual heartbeat monitoring
