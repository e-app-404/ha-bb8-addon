# HA BB-8 Add-on Test Report

## Test Environment
- **Date**: YYYY-MM-DD HH:MM:SS
- **Operator**: [Your Name]
- **HA Supervisor Version**: [Run: `ha info | grep supervisor`]
- **HA Host**: [IP Address]
- **Add-on Version**: [From config.yaml]
- **Git Commit**: [Run: `git rev-parse HEAD`]

## Build & Deployment Results

### Build Test
- [ ] **PASS** / [ ] **FAIL** - Docker build completed successfully
- [ ] **PASS** / [ ] **FAIL** - All required files present in build context
- **Build Command**: `docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:bookworm -t ha-bb8-test .`
- **Exit Code**: [0 = success]
- **Build Time**: [duration]
- **Image Size**: [docker images | grep ha-bb8-test]

### Deployment Test  
- [ ] **PASS** / [ ] **FAIL** - Add-on appears in Supervisor Local Add-ons
- [ ] **PASS** / [ ] **FAIL** - Add-on installs without errors
- [ ] **PASS** / [ ] **FAIL** - Configuration options accessible via UI
- **Deployment Method**: [rsync/ssh/UI upload]
- **Supervisor Command**: `ha addons info local_beep_boop_bb8`
- **Status**: [started/stopped/error]

## Startup & Banner Validation

### Banner Test Results
- [ ] **PASS** / [ ] **FAIL** - Entry banner present with correct format
- [ ] **PASS** / [ ] **FAIL** - Version number matches expected
- [ ] **PASS** / [ ] **FAIL** - Process PID messages appear
- [ ] **PASS** / [ ] **FAIL** - Application ready messages appear

**Expected Banner Pattern**:
```
[timestamp] [BB-8] run.sh entry (version=X.X.X) wd=/usr/src/app LOG=/data/reports/ha_bb8_addon.log HEALTH=X ECHO=true
```

**Actual Log Output** (first 20 lines):
```
[Paste actual log output here from: ha addons logs local_beep_boop_bb8 | head -20]
```

### Connectivity Test Results
- [ ] **PASS** / [ ] **FAIL** - MQTT broker reachable
- [ ] **PASS** / [ ] **FAIL** - MQTT authentication successful  
- [ ] **PASS** / [ ] **FAIL** - BLE adapter accessible
- [ ] **PASS** / [ ] **FAIL** - Required permissions granted

**MQTT Test Command**: `mosquitto_pub -h 192.168.0.129 -p 1883 -u mqtt_bb8 -P mqtt_bb8 -t test/ping -m hello`
**MQTT Result**: [success/timeout/auth failed]

**BLE Test Command**: `hciconfig hci0 && hcitool dev`  
**BLE Result**: [device listed/permission denied/not found]

## Functional Testing

### Happy Path Test
- [ ] **PASS** / [ ] **FAIL** - Home Assistant discovery topics published
- [ ] **PASS** / [ ] **FAIL** - BB-8 presence sensor appears in HA
- [ ] **PASS** / [ ] **FAIL** - RSSI sensor appears in HA
- [ ] **PASS** / [ ] **FAIL** - Echo responder responds to commands

**Discovery Test**: `mosquitto_sub -h 192.168.0.129 -p 1883 -u mqtt_bb8 -P mqtt_bb8 -t 'homeassistant/+/+/config' -C 3`
**Discovery Result**: [JSON configs received/timeout/no messages]

### Edge Case Tests

**Test 1: MQTT Broker Unavailable**
- [ ] **PASS** / [ ] **FAIL** - Add-on handles MQTT connection failure gracefully
- [ ] **PASS** / [ ] **FAIL** - Connection retry logic activates
- [ ] **PASS** / [ ] **FAIL** - Add-on reconnects when broker returns
- **Test Method**: [Stopped broker service/blocked port/invalid host]
- **Observed Behavior**: [Describe what happened]

**Test 2: Invalid Configuration**
- [ ] **PASS** / [ ] **FAIL** - Add-on reports configuration errors clearly
- [ ] **PASS** / [ ] **FAIL** - Add-on exits gracefully with invalid config
- [ ] **PASS** / [ ] **FAIL** - Error messages are actionable
- **Test Config**: [Invalid setting used]
- **Error Message**: [Exact error from logs]

## Health & Monitoring

### Health Check Results
- [ ] **PASS** / [ ] **FAIL** - Heartbeat files created and updated
- [ ] **PASS** / [ ] **FAIL** - Heartbeat timestamps within 30 seconds
- [ ] **PASS** / [ ] **FAIL** - Health summary messages appear in logs

**Heartbeat Check**: `docker exec [CONTAINER_ID] ls -la /tmp/bb8_heartbeat_*`
**Heartbeat Ages**: 
- main: [X seconds]
- echo: [X seconds]

### Resource Usage
- **Memory Usage**: [docker stats output]
- **CPU Usage**: [docker stats output]  
- **Log File Size**: [ls -lh /data/reports/ha_bb8_addon.log]

## Test Summary

### Overall Result
- [ ] **PASS** - All critical tests passed, add-on fully functional
- [ ] **PARTIAL** - Some issues found but add-on basically works  
- [ ] **FAIL** - Critical failures prevent normal operation

### Critical Issues Found
1. [Issue description and severity]
2. [Issue description and severity]
3. [Issue description and severity]

### Recommendations
- [ ] **PROCEED** - Add-on ready for production use
- [ ] **INVESTIGATE** - Issues need investigation but not blocking
- [ ] **BLOCK** - Critical issues must be resolved before deployment

### Next Steps
1. [Specific action items]
2. [Follow-up testing needed]
3. [Documentation updates required]

## Attachments
- [ ] Diagnostics bundle: `ha_bb8_diagnostics_[timestamp].tar.gz`
- [ ] Full add-on logs: `addon_logs.txt`
- [ ] Container inspection: `container_info.txt`
- [ ] Configuration snapshot: `addon_config.yaml`, `addon_options.json`

---
**Report Generated**: [timestamp]  
**Operator Signature**: [Your Name]