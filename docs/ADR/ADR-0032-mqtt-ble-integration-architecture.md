---
id: ADR-0032
title: "MQTT/BLE Integration Architecture"
date: 2025-09-28
status: Accepted
author:
  - Operational Evidence Analysis
related: ["ADR-0020", "ADR-0031", "ADR-0033"]
supersedes: []
last_updated: 2025-09-28
tags: ["mqtt", "ble", "integration", "architecture", "topics", "evidence", "validation", "governance", "tokens"]
---

# ADR-0032: MQTT/BLE Integration Architecture

**Session Evidence Sources:**
- STRAT-HA-BB8-2025-09-03T06:50Z-001 (MQTT probes, BLE readiness validation, topic configuration)
- BB8-STP5-MVP trace-bb8-2f0c9e9a (FakeMQTT seam validation, wildcard policy)
- HANDOFF::STRATEGOS::HA-BB8::2025-09-03T06:50Z-001 (Integration patterns, hardware requirements)

## Context

**Problem Statement:** Define the integration architecture for MQTT command/telemetry channels and BLE hardware interaction, including topic schemas, authentication patterns, hardware prerequisites, and validation methodologies.

**Investigation Method:**
- Live MQTT probes with `mosquitto_pub/sub` 
- BLE hardware validation via Supervisor device mapping
- Topic override configuration testing
- FakeMQTT seam validation with policy enforcement
- Integration pattern analysis from runtime logs

**Evidence Gathered:**

### MQTT Topic Architecture
```bash
# Base topic structure (configurable)
<base>/echo/cmd          # Command input  
<base>/echo/ack          # Acknowledgment response
<base>/echo/state        # State publication
<base>/telemetry/echo_roundtrip  # RTT metrics with BLE evidence
<base>/ble_ready/cmd     # BLE readiness command
<base>/ble_ready/summary # BLE readiness status

# STP4 Strict Requirements (device-originated echoes)
<base>/presence/state    # retain=true
<base>/rssi/state        # retain=true  
<base>/power/state       # retain=false, MUST include source:'device'
<base>/led/state         # retain=false, payload={"r","g","b"} only (exempt from source field)
```

### Topic Override Configuration  
```yaml
# Optional topic overrides in options.json
mqtt_echo_cmd_topic: "custom/echo/cmd"
mqtt_echo_ack_topic: "custom/echo/ack"  
mqtt_echo_state_topic: "custom/echo/state"
mqtt_telemetry_echo_roundtrip_topic: "custom/telemetry/roundtrip"
mqtt_ble_ready_cmd_topic: "custom/ble_ready/cmd"
mqtt_ble_ready_summary_topic: "custom/ble_ready/summary"
```

### Live MQTT Probe Evidence
```bash
# Observed successful echo sequence
bb8/echo/cmd {"value":1}
bb8/echo/ack {"ts": "2025-09-03T10:23:35Z", "value": 1}
bb8/echo/state {"ts": "2025-09-03T10:23:35Z", "state": "touched"}

# Telemetry with BLE evidence fields
bb8/telemetry/echo_roundtrip {"ts": "...", "rtt_ms": 0, "ble_ok": false, "ble_latency_ms": null}

# BLE readiness status
bb8/ble_ready/summary {"ts": "...", "detected": false, "attempts": 0, "source": "echo_responder"}
```

### BLE Hardware Evidence
```yaml
# Device mapping (from ha addons info)
devices:
  - /dev/hci0

# Hardware configuration  
options:
  ble_adapter: hci0
  bb8_mac: ED:ED:87:D7:27:50
```

### Connection Logs
```
# MQTT connectivity confirmation
Starting MQTT loop on 192.168.0.129:1883
Connected to MQTT broker with rc=Success
Subscribed to bb8/echo/cmd

# BLE initialization
{'event': 'ble_gateway_init', 'mode': 'bleak', 'adapter': 'hci0'}
{'event': 'core_init', 'address': 'ED:ED:87:D7:27:50'}
```

## Decision

**Technical Choice:** Implement a **dual-channel integration architecture** with MQTT for command/telemetry and BLE for device control, using configurable topic schemas and evidence-based validation.

### 1. MQTT Integration Pattern

**Connection Configuration:**
```python
# Observed implementation pattern (from code analysis)
from paho.mqtt.enums import CallbackAPIVersion
client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
```

**Topic Schema Design:**
- **Base-prefixed topics** with runtime configurability  
- **Topic override support** via options.json for multi-instance deployments
- **Structured message payloads** with timestamp and evidence fields
- **No wildcard subscriptions** (policy enforced, prevents hazardous patterns)

**Authentication & Authorization:**
```yaml
# Broker configuration
mqtt_host: 192.168.0.129
mqtt_port: 1883  
mqtt_user: mqtt_bb8
mqtt_password: mqtt_bb8
mqtt_tls: false  # Clear-text for local deployment
```

### 2. BLE Integration Pattern  

**Hardware Prerequisites:**
- Device mapping: `/dev/hci0` accessible to container
- Hardware permissions: `host_dbus: true`, `apparmor: disable`
- Adapter configuration: `ble_adapter: hci0`
- Target device: MAC address `ED:ED:87:D7:27:50`

**Integration Library Stack:**
```
bleak: 0.22.3     # BLE abstraction layer
spherov2: 0.12.1  # Sphero protocol implementation
```

### 3. Validation & Testing Architecture

**FakeMQTT Testing (Production Validated):**
```bash
# FakeMQTT seam via bleep_run.py
addon/tools/bleep_run.py  # Provides broker simulation
# Generates: reports/bleep_run_*.log
```

**STP4 Strict Mode Validation:**
```yaml
# Environment toggles for strict validation
environment_toggles:
  MQTT_BASE: "bb8"
  ENABLE_BRIDGE_TELEMETRY: 1
  REQUIRE_DEVICE_ECHO: 1      # Enforces source:'device' field validation
  EVIDENCE_TIMEOUT_SEC: 3.0
```

**Integration Validation Commands:**
```bash
# Echo probe with topic override support
BASE=$(jq -r '.mqtt_base // "bb8"' /data/options.json)
E_CMD=$(jq -r '.mqtt_echo_cmd_topic // empty' /data/options.json)
[ -z "$E_CMD" ] && E_CMD="$BASE/echo/cmd"

mosquitto_sub -h 192.168.0.129 -p 1883 -u mqtt_bb8 -P mqtt_bb8 \
-t "$BASE/echo/#" -C 3 -W 8 -v & SP=$!; sleep 0.2
mosquitto_pub -h 192.168.0.129 -p 1883 -u mqtt_bb8 -P mqtt_bb8 \
-t "$E_CMD" -m '{"value":1}'
wait $SP || true

# BLE readiness probe  
mosquitto_sub -h 192.168.0.129 -p 1883 -u mqtt_bb8 -P mqtt_bb8 \
-t "$(jq -r '.mqtt_ble_ready_summary_topic // "bb8/ble_ready/summary"' /data/options.json)" \
-C 1 -W 8 -v & SP=$!; sleep 0.2
mosquitto_pub -h 192.168.0.129 -p 1883 -u mqtt_bb8 -P mqtt_bb8 \
-t "$(jq -r '.mqtt_ble_ready_cmd_topic // "bb8/ble_ready/cmd"' /data/options.json)" \
-m '{"timeout_s":10,"retry_interval_s":1.5,"max_attempts":5,"nonce":"manual"}'
wait $SP || true
```

### 4. Telemetry & Evidence Schema

**Echo Roundtrip Telemetry:**
```json
{
  "ts": "2025-09-03T10:23:35Z",
  "rtt_ms": 0,
  "ble_ok": false,
  "ble_latency_ms": null,
  "source": "echo_responder"
}
```

**BLE Readiness Status:**
```json
{
  "ts": "2025-09-03T10:23:35Z", 
  "detected": false,
  "attempts": 0,
  "source": "echo_responder",
  "adapter": "hci0",
  "target_mac": "ED:ED:87:D7:27:50"
}
```

## Consequences

### Positive
- **Topic override flexibility** verified operational for multi-instance deployments
- **Evidence-based telemetry** supports STP5 attestation with BLE gating  
- **FakeMQTT testing** provides deterministic integration validation without broker dependency
- **Clear separation of concerns** between MQTT command/control and BLE device interaction
- **Structured message schemas** enable programmatic validation and monitoring
- **No wildcard policy** prevents accidental broad subscriptions and resource exhaustion

### Negative  
- **BLE evidence frequently absent** (`ble_ok: false`) in telemetry during testing
- **BlueZ/DBus access limitations** within container context
- **Single broker configuration** limits redundancy options
- **Clear-text MQTT** suitable only for trusted network segments
- **Policy/test mismatch** on wildcard handling causes test suite failure

### Unknown/Untested
- **TLS MQTT configuration** and certificate handling not validated
- **BLE device wake strategies** for reliable `ble_ok: true` evidence
- **MQTT QoS/retain behavior** beyond default configurations
- **Multi-broker failover** patterns not implemented or tested
- **BLE connection recovery** after device sleep/wake cycles

### Implementation Evidence

### Discovery Integration Issues Resolved
```python
# Fixed: publish_discovery() signature alignment
# Error: TypeError: publish_discovery() got an unexpected keyword argument 'dbus_path'
# Source: addon/bb8_core/facade.py:293 → publish_discovery(...)
# Resolution: Aligned attach_mqtt path to not pass unsupported kwargs
```

### Configuration Discovered
```yaml
# Complete integration configuration
options:
  # MQTT Configuration
  mqtt_base: bb8
  mqtt_host: 192.168.0.129
  mqtt_port: 1883
  mqtt_user: mqtt_bb8
  mqtt_password: mqtt_bb8
  mqtt_tls: false
  qos: 1
  keepalive: 60
  
  # Topic Overrides (optional)
  mqtt_echo_cmd_topic: ""           # empty = use default
  mqtt_echo_ack_topic: ""
  mqtt_echo_state_topic: ""
  mqtt_telemetry_echo_roundtrip_topic: ""
  mqtt_ble_ready_cmd_topic: ""
  mqtt_ble_ready_summary_topic: ""
  
  # BLE Configuration  
  ble_adapter: hci0
  bb8_mac: ED:ED:87:D7:27:50
  bb8_name: "S33 BB84 LE"

# Container Integration
devices:
  - /dev/hci0
host_dbus: true
apparmor: disable
```

### Message Patterns Observed
```bash
# Successful MQTT Integration Flow
Connected to MQTT broker with rc=Success
Subscribed to bb8/echo/cmd
Received message on bb8/echo/cmd: b'{"value":1}'

# BLE Integration Initialization  
{'event': 'ble_gateway_init', 'mode': 'bleak', 'adapter': 'hci0'}
{'event': 'version_probe', 'bleak': '0.22.3', 'spherov2': '0.12.1'}
{'event': 'core_init', 'address': 'ED:ED:87:D7:27:50'}
```

### Validation Results Summary
- **MQTT Echo Probe:** ✅ Command → Ack → State sequence confirmed
- **Topic Override Support:** ✅ Custom topic configuration operational  
- **BLE Hardware Detection:** ✅ Adapter initialization successful
- **Telemetry Schema:** ✅ Structured payloads with evidence fields
- **FakeMQTT Testing:** ✅ Integration seam validated without real broker
- **BLE Device Evidence:** ❌ `ble_ok: false` in all telemetry samples
- **Wildcard Policy:** ❌ Policy/test mismatch causing test failure

## Integration Patterns & Best Practices

### MQTT Topic Naming Convention
```bash
# Standard pattern
<base>/<component>/<message_type>

# Examples
bb8/echo/cmd           # Commands to echo responder
bb8/echo/ack           # Acknowledgments from echo responder  
bb8/telemetry/roundtrip # Performance metrics with evidence
bb8/ble_ready/summary  # BLE readiness status
```

### Error Handling & Recovery
```bash
# Connection failure patterns (observed)
Connection Refused: not authorised.  # ACL/credential issues
Connection timeout                   # Network/broker availability
```

### Development & Testing Workflow
```bash
# 1. FakeMQTT validation (no broker required)
python addon/tools/bleep_run.py

# 2. Live integration testing
mosquitto_pub/sub commands as documented above

# 3. STP5 attestation with BLE enforcement
/config/domain/shell_commands/stp5_supervisor_ble_attest.sh
```

### Gaps Requiring Further Investigation

### Critical
- **BLE AsyncIO Threading:** Implement dedicated event-loop thread to prevent "There is no current event loop" warnings
- **Device-originated Echo Validation:** Implement runtime enforcement of `source:'device'` for scalar topics when `REQUIRE_DEVICE_ECHO=1`
- **LED State Schema Validation:** Ensure LED/state remains `{r,g,b}` only without source field
- **BLE wake strategy:** Develop reliable method to achieve `ble_ok: true` evidence
- **Wildcard test resolution:** Align test expectations with no-wildcard policy
- **DBus/BlueZ permissions:** Resolve container BLE access limitations

### Secondary
- **TLS MQTT implementation:** Add encrypted broker support for production
- **Multi-broker failover:** Implement redundancy for critical deployments  
- **QoS/retain optimization:** Tune MQTT delivery guarantees for telemetry streams
- **BLE connection pooling:** Optimize device interaction patterns

## References

**Source Files Examined:**
- `/data/options.json` (runtime configuration materialization)
- `addon/bb8_core/echo_responder.py` (MQTT client implementation) 
- `addon/tools/bleep_run.py` (FakeMQTT testing framework)
- Supervisor device configuration and logs

**Commands Executed:**
- All MQTT probe commands with successful topic override validation
- BLE hardware detection and initialization logging
- FakeMQTT integration testing with policy enforcement
- STP5 attestation runs with both NO_BLE and BLE_ENFORCED modes

**Tests Performed:**
- End-to-end MQTT echo sequence validation  
- Topic override configuration testing
- BLE hardware initialization and readiness probing
- Integration seam validation via FakeMQTT
- Telemetry schema validation with evidence field verification

**Session References:**
- STRAT-HA-BB8-2025-09-03T06:50Z-001: MQTT/BLE integration validation
- BB8-STP5-MVP trace-bb8-2f0c9e9a: FakeMQTT seam and wildcard policy
- HANDOFF::STRATEGOS::HA-BB8::2025-09-03T06:50Z-001: Hardware requirements and patterns

---

**Extraction Date:** 28 September 2025
**Session ID/Reference:** Synthesis of multiple integration validation sessions  
**Evidence Quality:** Complete for MQTT patterns; Partial for BLE device interaction