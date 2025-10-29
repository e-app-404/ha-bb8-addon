# Milestone 2: Device Connectivity Enhancement - Workspace Resources

## Primary ADR Documentation (Critical Reading)

### **Core Architecture & Integration**
- **ADR-0032**: MQTT/BLE Integration Architecture
  - Location: `docs/ADR/ADR-0032-mqtt-ble-integration-architecture.md`
  - Relevance: MQTT topic schemas, BLE hardware patterns, paho-mqtt v2 compatibility fixes
  - Priority: **CRITICAL** - Contains production-validated patterns and topic structure

- **ADR-0031**: Supervisor-only Operations & Testing Protocol  
  - Location: `docs/ADR/ADR-0031-supervisor-only-operations-testing.md`
  - Relevance: SSH access methods, container validation, operational constraints
  - Priority: **CRITICAL** - Defines deployment and testing boundaries

- **ADR-0034**: HA OS Infrastructure
  - Location: `docs/ADR/ADR-0034-ha-os-infrastructure.md`
  - Relevance: Alpine Linux environment, Docker paths, BLE tools availability
  - Priority: **HIGH** - Infrastructure knowledge for BLE development

### **Development Standards**
- **ADR-0025**: Canonical Repo Layout BB8 Addon
  - Location: `docs/ADR/ADR-0025-canonical-repo-layout-bb8-addon.md`
  - Relevance: Module organization, import patterns, code structure
  - Priority: **HIGH** - Ensures proper code organization

- **ADR-0020**: Motion Safety and MQTT Contract
  - Location: `docs/ADR/ADR-0020-motion-safety-and-mqtt-contract.md`
  - Relevance: Safety protocols for device commands, MQTT contracts
  - Priority: **MEDIUM** - Safety constraints for BLE commands

### **Governance & Quality**
- **ADR-0009**: ADR Governance Formatting
  - Location: `docs/ADR/ADR-0009-adr-governance-formatting.md`
  - Relevance: Documentation standards for updates
  - Priority: **MEDIUM** - For creating new ADRs or updating existing ones

- **ADR-0036**: AI Model Selection Governance
  - Location: `docs/ADR/ADR-0036-ai-model-selection-governance.md`
  - Relevance: Model-specific capabilities and constraints
  - Priority: **LOW** - Context for autonomous vs collaborative decisions

## Core Source Code Files (Primary Focus)

### **BLE Infrastructure (Critical Fixes Needed)**
- **`addon/bb8_core/bb8_presence_scanner.py`**
  - Issue: Coroutine TypeError causing log spam every 60 seconds
  - Priority: **P0 CRITICAL** - Must fix first
  - Error: `TypeError("'coroutine' object is not iterable")`

- **`addon/bb8_core/ble_bridge.py`**
  - Enhancement: BLE command/response handling improvements
  - Priority: **P1 HIGH** - Core device interaction
  - Focus: Asyncio management, retry logic, timeout handling

- **`addon/bb8_core/ble_gateway.py`**
  - Enhancement: Low-level BLE connection management
  - Priority: **P1 HIGH** - Device discovery and pairing
  - Focus: Connection stability, device wake-up sequences

### **MQTT Integration (Stable - Limited Changes)**
- **`addon/bb8_core/mqtt_dispatcher.py`**
  - Status: **STABLE** - Milestone 1 validated
  - Priority: **READ-ONLY** - Avoid modifications unless critical
  - Note: Contains paho-mqtt v2 compatibility fixes

- **`addon/bb8_core/facade.py`**
  - Enhancement: Unified interface improvements
  - Priority: **MEDIUM** - Interface between MQTT and BLE
  - Focus: Error propagation, state synchronization

### **Configuration & Utilities**
- **`addon/bb8_core/addon_config.py`**
  - Status: **STABLE** - Configuration loading patterns
  - Priority: **READ-ONLY** - Use existing patterns
  - Usage: `cfg, src = load_config()`

- **`addon/bb8_core/logging_setup.py`**
  - Status: **STABLE** - Centralized logging
  - Priority: **READ-ONLY** - Use existing logger
  - Usage: `from .logging_setup import logger`

- **`addon/bb8_core/telemetry.py`**
  - Enhancement: BLE metrics and diagnostics
  - Priority: **P2 MEDIUM** - After core fixes
  - Focus: BLE connection metrics, device state telemetry

## Configuration Files

### **Runtime Configuration**
- **`addon/config.yaml`**
  - Relevance: Add-on metadata, capabilities, device permissions
  - Priority: **MEDIUM** - May need BLE permission updates
  - Note: Contains `host_dbus: true` and device mappings

- **`addon/options.json`** (Template)
  - Relevance: User configuration schema
  - Priority: **MEDIUM** - BLE device configuration options
  - Runtime Location: `/data/options.json` in container

### **Development Configuration**  
- **`pyproject.toml`**
  - Relevance: Project metadata, dependencies
  - Priority: **LOW** - Dependency management if needed

- **`Makefile`**
  - Relevance: QA pipeline, testing commands
  - Priority: **HIGH** - Quality gates: `make qa`, `make testcov`
  - Commands: `make evidence-stp4` for integration testing

## Test Infrastructure

### **BLE-Specific Tests**
- **`addon/tests/test_ble_*`**
  - Files: `test_ble_event_loop.py`, `test_ble_link.py`
  - Priority: **HIGH** - Understanding current BLE test patterns
  - Focus: Asyncio event loop management patterns

### **Integration Tests**
- **`addon/tests/test_discovery_publisher.py`**
  - Relevance: MQTT discovery entity publication
  - Priority: **HIGH** - Home Assistant integration patterns
  - Note: Contains telemetry test patterns

- **`addon/tests/test_facade_*.py`**
  - Files: `test_facade.py`, `test_facade_attach_mqtt.py`
  - Priority: **MEDIUM** - Interface testing patterns
  - Focus: MQTT/BLE integration testing

### **MQTT Tests (Reference Only)**
- **`addon/tests/test_mqtt_*.py`**
  - Status: **STABLE** - Reference patterns only
  - Priority: **LOW** - Don't modify unless critical
  - Note: Contains echo and dispatcher test patterns

## Progress Documentation

### **Current Session Documentation**
- **`docs/ADR/addon_progress/20250928_milestone2_handoff.md`**
  - Content: Comprehensive handoff instructions
  - Priority: **CRITICAL** - Primary mission brief
  - Contains: Objectives, constraints, validation tokens

- **`docs/ADR/addon_progress/20250928_adr_update_plan.md`**
  - Content: Documentation update plan
  - Priority: **MEDIUM** - For ADR updates after fixes
  - Contains: Evidence requirements, validation tokens

- **`docs/ADR/addon_progress/20250928_2010_milestone1_intake.log`**
  - Content: Milestone 1 completion evidence
  - Priority: **LOW** - Historical reference
  - Contains: Validation results and evidence

## Tools & Scripts

### **Development Tools**
- **`addon/tools/bleep_run.py`**
  - Purpose: FakeMQTT testing framework
  - Priority: **MEDIUM** - For MQTT integration testing
  - Usage: Integration seam validation

### **Diagnostic Scripts**
- **`ops/diag/collect_ha_bb8_diagnostics.sh`**
  - Purpose: System diagnostics collection
  - Priority: **LOW** - For troubleshooting
  - Usage: Environment validation

### **Quality Assurance**
- **`.github/workflows/shape.yml`**
  - Purpose: Repository validation
  - Priority: **LOW** - CI/CD patterns
  - Note: Automated quality gates

## External Resources

### **SSH Access (Production Validation)**
- **SSH Config**: `~/.ssh/config` (home-assistant alias)
- **Commands**: Documented in ADR-0031 and Milestone 2 handoff
- **Credentials**: `mqtt_bb8:mqtt_bb8` for MQTT testing
- **Host**: `192.168.0.129` (Home Assistant instance)

### **Development Environment**
- **Python Version**: 3.13
- **OS**: Alpine Linux v3.22
- **Container Runtime**: Docker
- **BLE Adapters**: hci0, hci1 (validated accessible)

## Priority Matrix for Milestone 2

### **P0 Critical (Start Here)**
1. `addon/bb8_core/bb8_presence_scanner.py` - Fix coroutine issue
2. ADR-0032 - MQTT/BLE integration patterns
3. ADR-0031 - Operational constraints and SSH procedures

### **P1 High (Core Development)**
1. `addon/bb8_core/ble_bridge.py` - Command/response handling
2. `addon/bb8_core/ble_gateway.py` - Device discovery
3. `addon/tests/test_ble_*.py` - Test patterns
4. ADR-0025 - Code organization standards

### **P2 Medium (Enhancement)**
1. `addon/bb8_core/telemetry.py` - BLE metrics
2. `addon/tests/test_discovery_publisher.py` - HA integration
3. `addon/config.yaml` - Configuration updates
4. Progress documentation updates

### **P3 Low (Reference)**
1. Historical documentation
2. CI/CD patterns
3. Diagnostic tools
4. External configuration files

## Validation Checklist

Before starting Milestone 2 development, ensure access to:
- [ ] SSH connection: `ssh home-assistant`
- [ ] Docker logs: `sudo docker logs addon_local_beep_boop_bb8`
- [ ] MQTT testing: `mosquitto_pub/sub` commands
- [ ] QA pipeline: `make qa`, `make testcov`
- [ ] BLE adapters: `ls /sys/class/bluetooth/`

## Quick Reference Summary

| Resource Type | File/Location | Priority | Purpose |
|---------------|---------------|----------|---------|
| **ADR** | `ADR-0032-mqtt-ble-integration-architecture.md` | CRITICAL | MQTT/BLE patterns, paho-mqtt v2 fixes |
| **ADR** | `ADR-0031-supervisor-only-operations-testing.md` | CRITICAL | SSH procedures, validation methods |
| **CODE** | `addon/bb8_core/bb8_presence_scanner.py` | P0 | **FIX FIRST** - Coroutine TypeError |
| **CODE** | `addon/bb8_core/ble_bridge.py` | P1 | BLE command/response enhancement |
| **CODE** | `addon/bb8_core/ble_gateway.py` | P1 | Device discovery and connection |
| **HANDOFF** | `20250928_milestone2_handoff.md` | CRITICAL | Complete mission brief |
| **SSH** | `ssh home-assistant` | CRITICAL | Production validation access |
| **QA** | `make qa`, `make testcov` | HIGH | Quality gates (≥80% coverage) |

**Start with P0 coroutine fix in bb8_presence_scanner.py, then proceed through P1 BLE enhancements.**

**Ready for Milestone 2 development with comprehensive resource mapping.**