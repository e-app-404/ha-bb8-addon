# HA-BB8 Add-on Development Plan
**Generated:** 2025-09-28T19:00:00+01:00  
**Based on:** Milestone 1 Assessment (development/workspace-intake-20250928)  
**Target:** Production-ready deployment across Milestones 1-3  

## Executive Summary

This development plan addresses critical operational gaps identified in the Milestone 1 assessment and provides a structured roadmap to production readiness. The plan prioritizes immediate operational stability (P0 issues) followed by device connectivity and Home Assistant integration.

**Current Status:** 🟡 Partially Ready (60% complete)  
**Target Timeline:** 2-3 weeks to production readiness  
**Critical Path:** Supervisor access → BLE infrastructure → Health monitoring  

## Phase 1: Immediate Stability (P0) - Days 1-3

### 1.1 Supervisor API Access Resolution
**Priority:** P0 - Blocking  
**Owner:** System Administrator + DevOps  
**Timeline:** 24 hours  

**Problem:** All `ha` commands return 401 unauthorized, preventing operational monitoring.

**Implementation Steps:**
1. **Option A: Sudoers Configuration (Recommended)**
   ```bash
   # On HA host (as root):
   cat > /etc/sudoers.d/ha-bb8-supervisor << 'EOF'
   # HA-BB8 Add-on operational access
   babylon-babes ALL=(root) NOPASSWD: /usr/bin/ha
   babylon-babes ALL=(root) NOPASSWD: /usr/bin/docker ps*, /usr/bin/docker logs*, /usr/bin/docker inspect*
   babylon-babes ALL=(root) NOPASSWD: /bin/journalctl
   EOF
   chmod 440 /etc/sudoers.d/ha-bb8-supervisor
   ```

2. **Option B: Group Membership**
   ```bash
   # Alternative: Add to hassio group if it exists
   usermod -aG hassio babylon-babes
   usermod -aG docker babylon-babes
   ```

3. **Validation Test:**
   ```bash
   ssh hass 'sudo ha info && sudo docker ps && echo "SUCCESS: Supervisor access restored"'
   ```

**Success Criteria:**
- ✅ `sudo ha info` returns system information without password prompt
- ✅ `sudo ha addons info local_beep_boop_bb8` shows add-on status
- ✅ Container inspection commands functional

### 1.2 BLE Infrastructure Restoration
**Priority:** P0 - Functional  
**Owner:** Infrastructure Team  
**Timeline:** 48 hours  

**Problem:** `hciconfig` command not found, preventing BB-8 Bluetooth communication.

**Implementation Steps:**
1. **Diagnostic Assessment:**
   ```bash
   ssh hass 'systemctl status bluetooth; which hciconfig bluetoothctl; ls -la /dev/hci*'
   ```

2. **Package Installation (if missing):**
   ```bash
   ssh hass 'sudo apt-get update && sudo apt-get install -y bluez bluez-tools'
   ```

3. **Service Verification:**
   ```bash
   ssh hass 'sudo systemctl enable bluetooth && sudo systemctl start bluetooth'
   ```

4. **Permission Validation:**
   ```bash
   ssh hass 'sudo usermod -aG bluetooth babylon-babes; hciconfig hci0'
   ```

**Success Criteria:**
- ✅ `hciconfig hci0` shows adapter status without errors
- ✅ `bluetoothctl` interactive mode accessible
- ✅ BB-8 device scannable via `bluetoothctl scan on`

### 1.3 Diagnostic Infrastructure Update
**Priority:** P0 - Operational  
**Owner:** Development Team  
**Timeline:** 24 hours  

**Problem:** Diagnostics script cannot collect supervisor data due to permission issues.

**Implementation Steps:**
1. **Update diagnostics script to use sudo:**
   ```bash
   # In ops/diag/collect_ha_bb8_diagnostics.sh
   # Replace: ha info
   # With: sudo ha info
   ```

2. **Re-run comprehensive diagnostics:**
   ```bash
   ./ops/diag/collect_ha_bb8_diagnostics.sh hass
   ```

3. **Verify full data collection:**
   - Supervisor information captured
   - Container logs accessible
   - System logs included
   - BLE adapter status confirmed

**Success Criteria:**
- ✅ Diagnostics archive contains supervisor data
- ✅ Container inspection results included
- ✅ System logs captured for troubleshooting
- ✅ Archive size > 10KB (vs current 2.9KB)

## Phase 2: Operational Monitoring (P1) - Days 4-7

### 2.1 Health Check Automation
**Priority:** P1 - Operational Excellence  
**Owner:** Development Team  
**Timeline:** 3 days  

**Implementation Steps:**
1. **Create health check service:**
   ```python
   # addon/health_monitor.py
   class HealthMonitor:
       def check_ble_adapter(self) -> bool
       def check_mqtt_connectivity(self) -> bool  
       def check_bb8_presence(self) -> bool
       def check_heartbeat_files(self) -> bool
   ```

2. **Implement heartbeat file monitoring:**
   - Monitor `/tmp/bb8_heartbeat_*` files per ADR-0010
   - Detect stale heartbeats (>30s = potential crash)
   - Trigger restart automation on failure

3. **Deploy health check endpoint:**
   - HTTP endpoint for external monitoring
   - Supervisor integration for auto-restart
   - Alerting integration (email/webhook)

**Success Criteria:**
- ✅ Automated health checks running every 30 seconds
- ✅ Crash detection within 60 seconds
- ✅ Auto-restart capability functional
- ✅ Health status accessible via API

### 2.2 Logging and Telemetry Enhancement
**Priority:** P1 - Debugging  
**Owner:** Development Team  
**Timeline:** 2 days  

**Implementation Steps:**
1. **Centralized logging configuration:**
   ```yaml
   # Update addon/config.yaml
   options:
     log_path: "/share/ha_bb8_addon.log"
     enable_bridge_telemetry: true
     telemetry_interval_s: 20
   ```

2. **Structured logging implementation:**
   - JSON format for log aggregation
   - Correlation IDs for request tracing
   - Performance metrics collection

3. **Dashboard integration:**
   - Home Assistant sensor entities
   - Grafana dashboard (optional)
   - Alert threshold configuration

**Success Criteria:**
- ✅ Structured logs accessible from HA interface
- ✅ Telemetry data flowing to configured endpoints
- ✅ Performance metrics tracked and visualized

## Phase 3: Device Connectivity (Milestone 2) - Days 8-14

### 3.1 BB-8 Communication Validation
**Priority:** P1 - Core Functionality  
**Owner:** Development Team  
**Timeline:** 4 days  

**Implementation Steps:**
1. **BLE communication testing:**
   ```python
   # Test script for BB-8 connectivity
   bb8_scanner = BB8Scanner(
       mac="ED:ED:87:D7:27:50",
       name="S33 BB84 LE",
       adapter="hci0"
   )
   ```

2. **MQTT discovery implementation:**
   - Device auto-discovery via Home Assistant MQTT
   - Entity publication for BB-8 controls
   - State synchronization testing

3. **Echo response system:**
   - Command/response cycle validation
   - Latency measurement and optimization
   - Error handling and retry logic

**Success Criteria:**
- ✅ BB-8 device discovered and paired reliably
- ✅ MQTT entities visible in Home Assistant
- ✅ Command response latency < 200ms average
- ✅ Error rate < 5% under normal conditions

### 3.2 Reliability and Error Handling
**Priority:** P1 - Production Readiness  
**Owner:** Development Team  
**Timeline:** 3 days  

**Implementation Steps:**
1. **Connection resilience:**
   - Automatic reconnection on BLE dropout
   - MQTT broker failover handling
   - Network interruption recovery

2. **Error boundaries:**
   - Graceful degradation on partial failures
   - Circuit breaker pattern for external dependencies
   - Comprehensive error logging and alerting

3. **Performance optimization:**
   - BLE scan interval tuning
   - MQTT message batching
   - Memory usage optimization

**Success Criteria:**
- ✅ 99.5% uptime over 48-hour test period
- ✅ Automatic recovery from common failure modes
- ✅ Memory usage stable over extended operation
- ✅ CPU usage < 10% average on HA host

## Phase 4: Home Assistant Integration (Milestone 3) - Days 15-21

### 4.1 Advanced Entity Integration
**Priority:** P2 - Feature Enhancement  
**Owner:** Development Team  
**Timeline:** 4 days  

**Implementation Steps:**
1. **Device entity enhancement:**
   - Battery level reporting
   - Movement tracking entities
   - LED control interface
   - Audio feedback controls

2. **Automation integration:**
   - Scene activation via BB-8 gestures
   - Location-based automation triggers
   - Voice command integration

3. **Configuration UI:**
   - HA configuration panel for add-on
   - Real-time device status display
   - Diagnostic information interface

**Success Criteria:**
- ✅ Rich device entities available in HA
- ✅ Automation triggers functional and responsive
- ✅ Configuration changes applied without restart
- ✅ User experience comparable to native HA devices

### 4.2 Documentation and Governance
**Priority:** P1 - Maintainability  
**Owner:** Documentation Team  
**Timeline:** 3 days  

**Implementation Steps:**
1. **ADR compliance resolution:**
   - Fix ADR-0031 cross-repo link validation
   - Update ADRs for new operational procedures
   - Document deployment and troubleshooting procedures

2. **User documentation:**
   - Installation guide update
   - Configuration reference
   - Troubleshooting guide
   - Performance tuning recommendations

3. **Operational runbooks:**
   - Incident response procedures
   - Monitoring and alerting setup
   - Backup and recovery procedures

**Success Criteria:**
- ✅ All ADR validation scripts passing
- ✅ Complete user documentation available
- ✅ Operational procedures documented and tested
- ✅ Knowledge transfer completed

## Implementation Timeline

### Week 1: Critical Stability
- **Days 1-2:** Supervisor access + BLE infrastructure
- **Days 3-4:** Diagnostic improvements + health monitoring
- **Days 5-7:** Logging enhancement + initial testing

### Week 2: Device Integration  
- **Days 8-10:** BB-8 communication validation
- **Days 11-14:** Reliability testing + performance optimization

### Week 3: Production Readiness
- **Days 15-17:** HA integration completion
- **Days 18-21:** Documentation + final validation

## Risk Management

### High Risk Items
1. **BLE Infrastructure Issues:** May require hardware troubleshooting
   - **Mitigation:** USB BLE adapter fallback option
   - **Contingency:** 48-hour window for hardware diagnosis

2. **Supervisor API Permissions:** Security policies may restrict access
   - **Mitigation:** Minimum privilege principle implementation
   - **Contingency:** Alternative monitoring via file system watching

3. **Device Compatibility:** BB-8 firmware variations may cause issues
   - **Mitigation:** Extended device testing across firmware versions
   - **Contingency:** Fallback to basic connectivity mode

### Medium Risk Items
1. **Performance Degradation:** Resource constraints on HA host
2. **Integration Conflicts:** Potential conflicts with other HA add-ons
3. **Documentation Drift:** ADR compliance maintenance overhead

## Success Metrics

### Technical Metrics
- **Uptime:** >99.5% over 7-day period
- **Response Latency:** <200ms average for BB-8 commands
- **Error Rate:** <5% failed commands under normal load
- **Resource Usage:** <10% CPU, <50MB RAM sustained

### Operational Metrics
- **Time to Recovery:** <2 minutes from failure to restoration
- **Diagnostic Coverage:** >90% of issues identifiable via diagnostics
- **Deployment Time:** <15 minutes from code to production
- **Documentation Coverage:** 100% of operational procedures documented

## Resource Requirements

### Development Team
- **Senior Developer:** 15 days (full-time equivalent)
- **DevOps Engineer:** 5 days (infrastructure + deployment)
- **Documentation Specialist:** 3 days (user docs + runbooks)

### Infrastructure
- **Development Environment:** Existing HA test instance
- **Monitoring Tools:** Existing Grafana/Prometheus stack
- **Testing Hardware:** Spare BB-8 device for regression testing

### Timeline Commitments
- **Phase 1 (P0):** 3 days - No delays acceptable
- **Phase 2 (P1):** 7 days - 1-day buffer included  
- **Phase 3-4:** 14 days - 2-day buffer for integration testing

---

**Plan Owner:** GitHub Copilot (Development Session)  
**Approval Required:** Development Team Lead + System Administrator  
**Next Review:** 2025-10-01 (3 days) - Phase 1 completion checkpoint