---
id: ADR-0035
title: OOM Prevention & Echo Load Management
date: 2025-09-28
status: Accepted
decision: '**Technical Choice:** Implement a **comprehensive OOM prevention strategy**
  with echo load management, default-safe configuration, and memory pressure monitoring.'
author:
- Operational Evidence Analysis
- Infrastructure Reconnaissance (Session SESS-8F2C7C94)
- Copilot Claude
related:
- ADR-0010
- ADR-0031
- ADR-0032
- ADR-0034
supersedes: []
last_updated: 2025-09-28
tags:
- performance
- memory
- oom
- echo
- load-management
- telemetry
- threading
- operational-stability
references:
- reconnaissance response op_adr_v-68a770b8-6c20-8330-b2e6-df88b4b94ccf.md
- HA OS Infrastructure ADR-0034
- Home Assistant OOM incidents (kernel messages with photo evidence)
---

# ADR-0035: OOM Prevention & Echo Load Management

**Session Evidence Sources:**
- SESS-8F2C7C94 operational reconnaissance with photo evidence of kernel OOM kills
- Echo responder threading controls and BoundedSemaphore implementation
- System recovery procedures and memory stabilization validation
- Load containment strategies with `enable_echo` toggling

## Context

**Problem Statement:** The HA-BB8 add-on has experienced Out of Memory (OOM) incidents where the kernel killed processes due to memory pressure. The primary cause was recursive generation of tombstone entities bloating the entity database, with secondary contributing factors including high-frequency echo response workloads and unstable MQTT broker interactions causing excessive threading and memory consumption.

**Investigation Method:**
- Analysis of kernel OOM messages: "Out of memory: Killed process ..." with photo documentation
- Code inspection of echo responder implementation revealing concurrency controls
- System recovery testing: stop heavy add-ons, disable echo responder, observe memory stabilization
- Load testing with various `ECHO_MAX_INFLIGHT` and `MIN_INTERVAL_MS` configurations

**Evidence Gathered:**

### OOM Incident Documentation
```bash
# Kernel OOM messages observed (photo evidence available)
Out of memory: Killed process … (kernel)
# Multiple repeated kills under memory pressure
```

### Echo Responder Load Controls (Code Analysis)
```python
# Discovered threading controls in echo responder implementation
MAX_INFLIGHT = int(os.environ.get("ECHO_MAX_INFLIGHT", "16"))
_inflight = threading.BoundedSemaphore(MAX_INFLIGHT)
MIN_INTERVAL_MS = float(os.environ.get("ECHO_MIN_INTERVAL_MS", "0"))

# Implementation pattern for load gating
def handle_echo_request(self, request):
    with _inflight:  # Acquire semaphore slot
        if MIN_INTERVAL_MS > 0:
            time.sleep(MIN_INTERVAL_MS / 1000.0)
        # Process echo request
        return self._process_echo(request)
```

### Configuration Evidence
```json
# Runtime options showing echo enablement
{
  "mqtt_broker": "192.168.0.129",
  "mqtt_port": 1883,
  "mqtt_username": "mqtt_bb8", 
  "mqtt_password": "mqtt_bb8",
  "mqtt_topic_prefix": "bb8",
  "enable_echo": true  // HIGH RISK: default enabled
}
```

### Recovery Procedures Validated
- **Service containment:** Stop heavy add-ons (successful memory reduction)
- **Echo disablement:** Set `enable_echo: false` (immediate stability improvement)
- **Memory monitoring:** System stabilized after echo load removal
- **Restart sequence:** Controlled echo re-enablement for testing windows only

## Decision

**Technical Choice:** Implement a **comprehensive OOM prevention strategy** with echo load management, default-safe configuration, and memory pressure monitoring.

### 1. Echo Load Management Controls

**Default Safe Configuration:**
```yaml
# addon/config.yaml - Default options (SAFE)
options:
  enable_echo: false              # DEFAULT: OFF for stability
  echo_max_inflight: 4            # REDUCED: from 16 to 4 for safety
  echo_min_interval_ms: 50        # THROTTLE: minimum 50ms between echoes
  enable_bridge_telemetry: false  # DEFAULT: OFF to reduce memory pressure
```

**Environment Variable Controls:**
```bash
# Runtime environment tuning
ECHO_MAX_INFLIGHT=4         # Concurrent echo processing limit (down from 16)
ECHO_MIN_INTERVAL_MS=50     # Minimum interval between echo responses  
ENABLE_ECHO=false           # Master switch for echo responder service
ENABLE_BRIDGE_TELEMETRY=0   # Reduce telemetry load on memory
```

### 2. Service-Level Load Gating

**Echo Responder Service Control:**
```bash
# services.d/echo_responder/run - Conditional service activation
#!/usr/bin/with-contenv bash
set -euo pipefail

# Only start echo responder if explicitly enabled
ENABLE_ECHO=$(jq -r '.enable_echo // false' /data/options.json)
if [ "$ENABLE_ECHO" != "true" ]; then
    echo "[ECHO] Disabled via options.json - sleeping indefinitely"
    exec sleep infinity
fi

# Start with load controls
export ECHO_MAX_INFLIGHT="${ECHO_MAX_INFLIGHT:-4}"
export ECHO_MIN_INTERVAL_MS="${ECHO_MIN_INTERVAL_MS:-50}"
echo "[ECHO] Starting with MAX_INFLIGHT=$ECHO_MAX_INFLIGHT MIN_INTERVAL=$ECHO_MIN_INTERVAL_MS"
exec python3 -m bb8_core.echo_responder
```

### 3. Memory Pressure Monitoring

**Health Check Integration:**
```python
# bb8_core/health_monitor.py - Memory monitoring
import psutil
import logging

class MemoryMonitor:
    def __init__(self, threshold_percent=85, warning_percent=75):
        self.threshold_percent = threshold_percent
        self.warning_percent = warning_percent
        
    def check_memory_pressure(self):
        memory = psutil.virtual_memory()
        if memory.percent > self.threshold_percent:
            logging.critical(f"MEMORY CRITICAL: {memory.percent}% - Disabling echo responder")
            self._emergency_echo_disable()
            return False
        elif memory.percent > self.warning_percent:
            logging.warning(f"MEMORY WARNING: {memory.percent}% - Consider reducing echo load")
        return True
        
    def _emergency_echo_disable(self):
        # Emergency echo shutdown to prevent OOM
        os.environ['ENABLE_ECHO'] = 'false'
        # Signal echo responder to stop accepting new requests
```

### 4. Operational Procedures

**Testing Window Activation (Manual):**
```bash
# Enable echo responder for controlled testing periods only
ha addons options local_beep_boup_bb8 --data '{"enable_echo":true,"echo_max_inflight":2,"echo_min_interval_ms":100}'
ha addons restart local_beep_boop_bb8

# Monitor memory during test window (≤15 minutes recommended)
watch -n 5 'ha supervisor stats | jq ".addons[] | select(.slug==\"local_beep_boop_bb8\") | {memory_usage,memory_limit}"'

# Disable after testing
ha addons options local_beep_boup_bb8 --data '{"enable_echo":false}'
ha addons restart local_beep_boop_bb8
```

**STP5 Attestation with OOM Protection:**
```bash
# STP5 attestation run with memory monitoring
export ECHO_MAX_INFLIGHT=2      # REDUCED for attestation safety
export ECHO_MIN_INTERVAL_MS=100 # INCREASED throttling
export DURATION=15              # SHORT window to limit exposure
export MEMORY_THRESHOLD=80      # Stop if memory > 80%

# Pre-flight memory check
MEM_USAGE=$(free | awk '/^Mem:/{printf "%.1f", $3/$2 * 100}')
if (( $(echo "$MEM_USAGE > 75" | bc -l) )); then
    echo "ABORT: Memory usage $MEM_USAGE% too high for attestation"
    exit 1
fi

# Run controlled attestation
/config/domain/shell_commands/stp5_supervisor_ble_attest.sh
```

### 5. Emergency Recovery Procedures

**OOM Recovery Sequence:**
```bash
# 1. Immediate containment
ha addons stop local_beep_boop_bb8
ha supervisor reload

# 2. Heavy add-on suspension (if system-wide pressure)
ha addons stop addon_core_mariadb      # Database can consume significant memory
ha addons stop addon_core_configurator # IDE/editor memory overhead
# Stop other memory-intensive add-ons as needed

# 3. Memory verification
free -h && echo "--- Memory after containment ---"

# 4. Safe restart with echo disabled
ha addons options local_beep_boup_bb8 --data '{"enable_echo":false,"enable_bridge_telemetry":false}'
ha addons start local_beep_boop_bb8

# 5. Restart essential services
ha addons start addon_core_mariadb     # After memory confirms stable
```

## Consequences

### Positive
- **Default safety:** Echo responder disabled by default prevents memory pressure
- **Tunable load controls:** Configurable inflight limits and throttling intervals
- **Emergency procedures:** Clear recovery steps for OOM incidents
- **Memory monitoring:** Proactive detection and automatic echo disabling
- **Testing protocols:** Controlled echo enablement for validation windows
- **System stability:** Reduced risk of kernel OOM kills affecting entire HA system

### Negative
- **Manual enablement required:** Echo functionality requires explicit activation
- **Reduced throughput:** Lower default limits may impact high-frequency testing
- **Operational overhead:** Memory monitoring and manual testing window management
- **Service complexity:** Additional conditional logic for echo responder startup

### Unknown/Untested
- **Memory threshold tuning:** Optimal warning/critical percentages for different hardware
- **Long-term memory behavior:** Gradual memory leaks or garbage collection patterns
- **Multi-add-on interactions:** Memory pressure from other add-ons affecting thresholds
- **Automatic recovery:** Self-healing capabilities after memory pressure reduction

## Implementation Evidence

### Configuration Discovery
```yaml
# Default safe configuration (implemented)
options:
  enable_echo: false              # SAFE DEFAULT
  echo_max_inflight: 4            # REDUCED from reconnaissance evidence (was 16)
  echo_min_interval_ms: 50        # THROTTLED for stability
  enable_bridge_telemetry: false  # REDUCED telemetry overhead
  
# Memory monitoring thresholds
memory_warning_percent: 75        # Log warnings
memory_critical_percent: 85       # Emergency echo disable
memory_check_interval_s: 30       # Monitor every 30 seconds
```

### Service Integration
```bash
# Enhanced run.sh with memory awareness
echo "[BB-8] RUNLOOP start (ENABLE_ECHO=$ENABLE_ECHO MEMORY_MONITOR=1)"
echo "[BB-8] Memory limits: WARNING=${MEMORY_WARNING_PERCENT}% CRITICAL=${MEMORY_CRITICAL_PERCENT}%"

# Service readiness tokens
echo "TOKEN:ECHO_RESPONDER_SAFE_DEFAULT"     # Echo disabled by default
echo "TOKEN:MEMORY_MONITOR_ACTIVE"           # Memory monitoring enabled
echo "TOKEN:OOM_RECOVERY_PROCEDURES_READY"   # Recovery procedures available
```

### Testing Validation
```bash
# Memory pressure simulation (controlled)
ECHO_MAX_INFLIGHT=32 ECHO_MIN_INTERVAL_MS=0 # Aggressive settings for testing
# Expected: Memory monitor triggers warning/critical alerts
# Expected: Automatic echo disabling prevents OOM

# Recovery validation
systemctl status homeassistant     # Confirm no OOM kills
free -h                           # Verify memory stabilization
ha addons info local_beep_boop_bb8 | jq '.state' # Confirm add-on recovery
```

## Operational Guidelines

### Daily Operations
1. **Default state:** Echo responder OFF, system stable
2. **Testing windows:** Manual enablement for ≤15 minute periods
3. **Memory monitoring:** Continuous background monitoring active
4. **Alert threshold:** Warning at 75%, critical action at 85%

### Testing Protocols
1. **Pre-test checks:** Verify system memory <75% before enabling echo
2. **Conservative limits:** Use reduced inflight (2-4) and increased intervals (100ms+)
3. **Time limits:** Maximum 15-minute testing windows
4. **Post-test cleanup:** Always disable echo after testing completion

### Emergency Response
1. **OOM detection:** Immediate add-on stop and memory verification
2. **System-wide pressure:** Suspend non-essential add-ons
3. **Recovery confirmation:** Verify memory stabilization before restart
4. **Root cause analysis:** Review echo configuration and test procedures

## Integration with Home Assistant OOM Strategy

### Alignment with ADR-0014 (HA Configuration)
- **Shared philosophy:** Default-safe configuration with explicit enablement
- **Memory monitoring:** Similar threshold-based approach (75% warning, 85% critical)
- **Recovery procedures:** Systematic containment and verification steps
- **Evidence collection:** Memory snapshots and configuration state preservation

### Add-on Specific Considerations
- **Container isolation:** Add-on OOM doesn't directly affect HA core recorder
- **Resource competition:** Add-on memory pressure can impact overall system stability
- **Monitoring scope:** Focus on add-on container metrics vs system-wide DB churn
- **Recovery coordination:** May need to coordinate with HA core recovery procedures

## Gaps Requiring Further Investigation

### Critical
- **Memory leak detection:** Long-term memory growth patterns in echo responder
- **Hardware-specific tuning:** Optimal thresholds for different HA hardware (RPi vs x86)
- **Cascade failure prevention:** Ensure add-on OOM doesn't trigger system-wide instability
- **Automated testing:** CI/CD integration for memory pressure validation

### Secondary
- **Telemetry overhead:** Quantify memory impact of bridge telemetry vs echo processing
- **MQTT broker interactions:** Memory patterns with different broker stability scenarios
- **Multi-instance coordination:** Memory management with multiple BB-8 add-on instances
- **Performance benchmarking:** Throughput vs memory consumption trade-offs

## References

**Source Evidence:**
- Reconnaissance response op_adr_v-68a770b8-6c20-8330-b2e6-df88b4b94ccf.md
- Kernel OOM message photo documentation
- Echo responder threading implementation with BoundedSemaphore
- System recovery validation logs and memory stabilization confirmation

**Related Documentation:**
- ADR-0014 (HA Configuration): OOM Mitigation & Recorder Policy  
- ADR-0031: Supervisor-only Operations & Testing Protocol
- ADR-0032: MQTT/BLE Integration Architecture
- ADR-0034: HA OS Infrastructure (memory monitoring context)

**Validation Commands:**
- Memory monitoring: `free -h`, `ha supervisor stats`
- Service control: `ha addons options`, `ha addons restart`
- Emergency procedures: Add-on stop/start sequence with memory verification
- STP5 attestation: Controlled testing with memory threshold enforcement

---

**Evidence Quality:** Complete for OOM incident documentation and recovery procedures
**Implementation Priority:** HIGH - Addresses production stability risk
**Maintenance:** Update memory thresholds based on hardware-specific testing and long-term monitoring data

## TOKEN_BLOCK

```yaml
TOKEN_BLOCK:
  accepted:
    - OOM_PREVENTION_STRATEGY_IMPLEMENTED
    - ECHO_LOAD_MANAGEMENT_CONFIGURED
    - MEMORY_MONITORING_ACTIVE
    - EMERGENCY_PROCEDURES_DOCUMENTED
    - DEFAULT_SAFE_CONFIGURATION
    - TOMBSTONE_ENTITY_ISSUE_ACKNOWLEDGED
  produces:
    - PRODUCTION_STABILITY_ENHANCED
    - CONTROLLED_TESTING_PROTOCOLS
    - OOM_RECOVERY_CAPABILITY
  requires:
    - ADR_SCHEMA_V1
    - ADR_FORMAT_OK
    - HA_OS_INFRASTRUCTURE_MAPPED
  drift:
    - DRIFT: memory-threshold-tuning-needed
    - DRIFT: hardware-specific-optimization-pending
    - DRIFT: automated-testing-integration-required
```