# MILESTONE 2: Device Connectivity Enhancement - Claude Sonnet 3.5 Handoff

## Mission Brief

You are now taking over HA-BB8 add-on development at **MILESTONE 2: Device Connectivity Enhancement**. Milestone 1 (Operational Stability Foundation) has been successfully completed with production validation. Your mission is to enhance BLE device connectivity and expand Home Assistant integration.

## Current State (Verified as of 28 Sep 2025)

### ✅ **Milestone 1 Achievements:**
- **Container Stability:** 3+ hour uptime validated (`docker ps`)
- **MQTT Integration:** Echo roundtrip operational (`{"ts": 1759098629.0950077, "value": 1}`)
- **P0 Critical Fixes:** All deployed and verified
  - paho-mqtt v2 ReasonCode compatibility resolved
  - Echo responder undefined variables fixed
  - Function redefinition errors eliminated
- **Code Quality:** 63% improvement (112→41 lint errors)
- **Infrastructure:** BLE adapters accessible (`hci0`, `hci1`)
- **Health Monitoring:** Dual heartbeat operational (`main_age=-0.1s echo_age=-0.1s`)

### 🎯 **Milestone 2 Objectives:**

1. **Address P2 BLE Presence Monitor Coroutine Issue** (PRIMARY)
   - Error: `TypeError("'coroutine' object is not iterable")`
   - Location: `bb8_presence_monitor_error` logs every 60 seconds
   - Impact: Non-blocking but affects BLE device discovery reliability

2. **Implement BB-8 Device Discovery and Pairing** (CORE)
   - Enhance `bb8_presence_scanner.py` for robust device detection
   - Implement reliable wake-up sequences for BB-8
   - Add MAC address resolution and validation
   - Create device pairing workflows

3. **Enhance BLE Command/Response Handling** (CORE)
   - Improve `ble_bridge.py` error handling and retry logic
   - Implement proper asyncio event loop management
   - Add command queuing and response correlation
   - Enhance timeout and connection management

4. **Expand Home Assistant Entity Integration** (INTEGRATION)
   - Complete discovery entity publication (LED, power, drive, etc.)
   - Implement state synchronization between device and HA
   - Add proper availability topics and LWT handling
   - Enhance telemetry and diagnostics reporting

## Architecture & Boundaries

### **Code Architecture (ADR-0025 Compliant):**
```
addon/bb8_core/
├── bridge_controller.py    # Main orchestrator (DO NOT MODIFY CORE LOGIC)
├── mqtt_dispatcher.py      # MQTT broker interface (STABLE - Milestone 1 validated)
├── ble_bridge.py          # BLE device interface (ENHANCE - Primary focus)
├── ble_gateway.py         # Low-level BLE management (ENHANCE)
├── bb8_presence_scanner.py # Device discovery (CRITICAL - Fix coroutine issue)
├── facade.py              # Unified interface (STABLE)
└── telemetry.py           # Metrics collection (ENHANCE)
```

### **Import Standards (CRITICAL):**
- **ALWAYS** use `from addon.bb8_core import ...` (NEVER `from bb8_core`)  
- **ALWAYS** use `from __future__ import annotations` for forward compatibility
- **SUPPRESS** paho-mqtt warnings: `warnings.filterwarnings("ignore", "Callback API version 1 is deprecated")`

### **Configuration System:**
```python
from .addon_config import load_config
cfg, src = load_config()  # Returns (config_dict, source_path)
# Config provenance is tracked and logged automatically
```

### **Logging Standards:**
```python
from .logging_setup import logger
logger.info({"event": "structured_event", "key": "value"})
# ONLY use centralized logger - automatic secret redaction included
```

## Guardrails & Validation Tokens

### **Critical Constraints:**
- **ADR-0031 COMPLIANCE:** All operations must work through Supervisor-only interfaces
- **NO SHELL ACCESS:** Cannot require container shell access or manual intervention
- **MQTT STABILITY:** Do not modify mqtt_dispatcher.py core logic (Milestone 1 validated)
- **CONFIG IMMUTABILITY:** Do not change core configuration loading patterns

### **Quality Gates:**
- **Test Coverage:** Maintain ≥80% coverage threshold
- **Lint Quality:** Do not increase error count beyond current 41
- **Container Stability:** Must maintain multi-hour uptime stability
- **MQTT Echo:** Must preserve `<2 second` roundtrip capability

### **Required Validation Tokens:**
Include these tokens in your responses to demonstrate adherence:

- **TOKEN_COROUTINE_FIXED:** BLE presence monitor TypeError resolved
- **TOKEN_ASYNCIO_MANAGED:** Proper event loop lifecycle management
- **TOKEN_DEVICE_DISCOVERED:** BB-8 detection and wake-up operational
- **TOKEN_BLE_ENHANCED:** Command/response handling improved
- **TOKEN_HA_INTEGRATED:** Discovery entities published and functional
- **TOKEN_SUPERVISOR_COMPLIANT:** All changes work through Supervisor interfaces
- **TOKEN_COVERAGE_MAINTAINED:** Test coverage ≥80% preserved
- **TOKEN_STABILITY_PRESERVED:** Container uptime stability maintained

### **Testing Protocol:**
```bash
# Validation Commands (run via SSH)
ssh home-assistant "sudo docker logs addon_local_beep_boop_bb8 --tail 20"
ssh home-assistant "mosquitto_sub -h 192.168.0.129 -u mqtt_bb8 -P mqtt_bb8 -t bb8/presence/state"
make testcov  # Must show ≥80% coverage
make qa       # Error count must not increase
```

## Problem Priority Matrix

### **P0 Critical (Must Fix):**
1. BLE presence monitor coroutine issue causing log spam
2. Asyncio event loop management in BLE components

### **P1 High (Core Features):**  
1. BB-8 device discovery robustness
2. BLE command/response reliability
3. Home Assistant entity integration completion

### **P2 Medium (Enhancement):**
1. Advanced telemetry and diagnostics
2. Error recovery and retry logic improvements
3. Performance optimization

### **P3 Low (Future):**
1. Additional device support
2. Advanced motion control features
3. Custom discovery patterns

## Evidence Requirements

### **Expected Deliverables:**
1. **Coroutine Fix Evidence:** Log showing absence of TypeError
2. **Device Discovery Evidence:** Successful BB-8 MAC resolution logs
3. **BLE Command Evidence:** Successful LED/power command execution
4. **HA Integration Evidence:** Discovery entities visible in Home Assistant
5. **Stability Evidence:** 4+ hour container uptime post-changes

### **Operational Validation:**
```bash
# Evidence Collection Commands
ssh home-assistant "sudo docker logs addon_local_beep_boop_bb8 --since='1h' | grep -v 'coroutine.*not iterable'"
ssh home-assistant "ls /sys/class/bluetooth/"  # Verify: hci0, hci1
mosquitto_sub -h 192.168.0.129 -u mqtt_bb8 -P mqtt_bb8 -t homeassistant/+/+/+/config
```

## Autonomous Thinking Areas

### **Where You Have Full Autonomy:**
- **BLE Protocol Implementation:** Choose optimal Bleak patterns and async handling
- **Error Handling Strategy:** Design retry logic and timeout management
- **Discovery Algorithms:** Implement device detection and wake-up sequences  
- **Code Organization:** Refactor within bb8_core modules as needed
- **Performance Optimization:** Enhance efficiency within architectural boundaries

### **Where You Need Validation:**
- **Configuration Changes:** Any modifications to core config loading
- **MQTT Topic Schema:** Changes to established topic patterns (ADR-0032)
- **Container Configuration:** Changes affecting Supervisor integration
- **Architecture Boundaries:** Moving functionality between major modules

### **Collaboration Points:**
- **Complex Integration Issues:** Consult on multi-component interactions
- **Performance Bottlenecks:** Discuss when optimization requires architectural changes  
- **Testing Strategy:** Validate comprehensive test coverage approaches
- **Production Concerns:** Review changes with operational impact

## Session Handoff Context

### **Repository State:**
- **Branch:** `development/production-ready-20250928` 
- **Last Commit:** `4a3c043` - Milestone 1 operational validation
- **Environment:** Home Assistant OS 16.2, Python 3.13, Alpine Linux v3.22

### **Key Files Recently Modified:**
- `echo_responder.py`: Import order and contextlib fixes
- `mqtt_dispatcher.py`: paho-mqtt v2 compatibility (STABLE)
- `facade.py`: Line length and docstring improvements
- `bb8_presence_scanner.py`: **NEEDS ATTENTION** - coroutine issue source

### **Available Tools & Resources:**
- **SSH Access:** `ssh home-assistant` for production validation
- **MQTT Testing:** `mosquitto_pub/sub` with credentials `mqtt_bb8:mqtt_bb8`
- **Docker Inspection:** `sudo docker logs addon_local_beep_boop_bb8`
- **BLE Tools:** Limited (use Bleak/Python instead of hciconfig)
- **QA Pipeline:** `make qa`, `make testcov`, `make evidence-stp4`

### **Development Workflow:**
1. **Analysis Phase:** Examine current BLE presence monitor implementation
2. **Fix Phase:** Resolve coroutine handling with proper asyncio patterns
3. **Enhancement Phase:** Improve device discovery and BLE reliability
4. **Integration Phase:** Complete Home Assistant entity publication
5. **Validation Phase:** Test via SSH deployment validation
6. **Documentation Phase:** Update relevant ADRs with new evidence

## Success Criteria

**Milestone 2 is considered complete when:**

✅ **BLE Presence Monitor:** No more coroutine TypeErrors in logs  
✅ **Device Discovery:** BB-8 successfully detected and paired  
✅ **BLE Commands:** LED control and power commands functional  
✅ **HA Integration:** All discovery entities published and responsive  
✅ **Container Stability:** 4+ hour uptime maintained post-deployment  
✅ **Quality Gates:** Test coverage ≥80%, lint errors ≤41  
✅ **Production Validation:** Live MQTT/BLE roundtrip successful  

**Your mission starts NOW. Begin with the BLE presence monitor coroutine issue analysis and proceed systematically through the enhancement objectives.**

---

**VALIDATION TOKENS TO REMEMBER:**
TOKEN_COROUTINE_FIXED | TOKEN_ASYNCIO_MANAGED | TOKEN_DEVICE_DISCOVERED | TOKEN_BLE_ENHANCED | TOKEN_HA_INTEGRATED | TOKEN_SUPERVISOR_COMPLIANT | TOKEN_COVERAGE_MAINTAINED | TOKEN_STABILITY_PRESERVED