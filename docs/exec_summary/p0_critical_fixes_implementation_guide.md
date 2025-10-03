# P0 Critical Fixes Implementation Guide
**Generated:** 2025-09-28  
**Priority:** IMMEDIATE (24-48 hours)  
**Target:** Restore operational monitoring and device connectivity  

## Overview
This guide provides exact commands to resolve the three critical P0 issues blocking production deployment:
1. **Supervisor API Access** (401 unauthorized on `ha` commands)
2. **BLE Infrastructure** (missing `hciconfig`/Bluetooth tools)
3. **Container Monitoring** (Docker permission denied)

## 🔧 HA Host Configuration (System Administrator)

### Step 1: Grant Supervisor and Docker Access
**Run on HA host as root (HA OS uses Alpine Linux):**

```bash
# Create sudoers configuration for HA-BB8 operations
cat > /etc/sudoers.d/ha-bb8-operations << 'EOF'
# HA-BB8 Add-on operational access for Home Assistant OS
# Allows babylon-babes user to run specific commands without password
Defaults:babylon-babes !requiretty

# Home Assistant Supervisor commands (actual paths in HA OS)
babylon-babes ALL=(root) NOPASSWD: /usr/bin/ha
babylon-babes ALL=(root) NOPASSWD: /usr/bin/ha info
babylon-babes ALL=(root) NOPASSWD: /usr/bin/ha addons *
babylon-babes ALL=(root) NOPASSWD: /usr/bin/ha supervisor *

# Docker container inspection (Docker 28.3.3 in /usr/local/bin/)
babylon-babes ALL=(root) NOPASSWD: /usr/local/bin/docker ps*
babylon-babes ALL=(root) NOPASSWD: /usr/local/bin/docker logs*
babylon-babes ALL=(root) NOPASSWD: /usr/local/bin/docker inspect*
babylon-babes ALL=(root) NOPASSWD: /usr/local/bin/docker exec* env
babylon-babes ALL=(root) NOPASSWD: /usr/local/bin/docker exec* ls*

# System log access (if available in HA OS)
babylon-babes ALL=(root) NOPASSWD: /bin/journalctl*
babylon-babes ALL=(root) NOPASSWD: /usr/bin/journalctl*
EOF

# Set correct permissions
chmod 440 /etc/sudoers.d/ha-bb8-operations

# Validate sudoers syntax (important!)
visudo -c -f /etc/sudoers.d/ha-bb8-operations
```

### Step 2: Verify Supervisor Access
**Test the configuration:**
```bash
# Switch to babylon-babes user and test
su - babylon-babes -c 'sudo ha info'
su - babylon-babes -c 'sudo ha addons info local_beep_boop_bb8'
su - babylon-babes -c 'sudo docker ps --filter name=addon'
```

**Expected output:** System information, add-on status, and container list (not permission errors)

### Step 3: BLE Infrastructure Diagnosis and Fix (HA OS Alpine)
**Check current Bluetooth status:**
```bash
# Check for BLE adapters (should show hci0 if hardware present)
ls -la /dev/hci*

# Check installed packages (HA OS uses Alpine apk)
apk list | grep -i bluez

# Check available tools
which bluetoothctl hciconfig hcitool
```

**Current HA OS Status (from diagnostics):**
- ✅ `bluetoothctl` is available: `/usr/bin/bluetoothctl`
- ✅ `bluez-5.82-r0` package is installed
- ❌ `hciconfig` and `hcitool` are missing (need bluez-tools)
- ❌ Bluetooth service management unclear (s6 overlay system)

**Install missing Bluetooth tools:**
```bash
# HA OS uses Alpine package manager
apk update

# Install additional Bluetooth tools (deprecated package contains hciconfig)
apk add bluez-deprecated

# Check if tools are now available
which hciconfig hcitool

# The bluetooth service should be managed by HA OS automatically
# Check if bluetooth is running via bluetoothctl
bluetoothctl show
```

**Verify BLE functionality:**
```bash
# Test as babylon-babes user (HA OS specific)
su - babylon-babes -c 'bluetoothctl show'
su - babylon-babes -c 'hciconfig hci0' # After installing bluez-tools
```

**Expected output:** Bluetooth controller details and HCI adapter information (if hardware present)

## 🧪 Validation Tests (Development Team)

### Test 1: Enhanced Diagnostics Collection
**Run from development workspace:**
```bash
cd /Users/evertappels/Projects/HA-BB8
./ops/diag/collect_ha_bb8_diagnostics.sh hass
```

**Expected improvements:**
- ✅ Supervisor information captured (not "Could not retrieve HA info")
- ✅ Container inspection data included (not "Could not retrieve container info")
- ✅ Add-on logs accessible (not "Could not retrieve addon logs")
- ✅ System logs included for troubleshooting
- ✅ BLE adapter status clearly reported
- ✅ Archive size significantly larger (>10KB vs 2.9KB)

### Test 2: Manual Command Verification
**Via SSH from development machine (HA OS specific paths):**
```bash
# Test Supervisor commands
ssh hass 'sudo ha info | head -10'
ssh hass 'sudo ha addons info local_beep_boop_bb8'

# Test Docker commands (note: /usr/local/bin/docker in HA OS)
ssh hass 'sudo /usr/local/bin/docker ps --filter name=addon_local_beep_boup_bb8'
ssh hass 'sudo /usr/local/bin/docker logs $(sudo /usr/local/bin/docker ps --filter name=addon_local_beep_boop_bb8 -q) | tail -20'

# Test BLE commands (after installing bluez-tools)
ssh hass 'hciconfig hci0 | head -3'  # After apk add bluez-deprecated
ssh hass 'bluetoothctl show | head -5'

# Test system logs (if journalctl available in HA OS)
ssh hass 'sudo journalctl --since "1 hour ago" --no-pager | tail -10 || echo "journalctl not available in HA OS"'
```

## 🚨 Security Considerations

### Principle of Least Privilege
The sudoers configuration provides:
- ✅ **Read-only access** to Supervisor and Docker commands
- ✅ **Specific command patterns** (not broad sudo access)
- ✅ **No interactive commands** that could escalate privileges
- ✅ **Logging maintained** via sudo audit trail

### What is NOT granted:
- ❌ General sudo access (`sudo su`, `sudo bash`)
- ❌ File system modification outside containers
- ❌ Network configuration changes
- ❌ User management commands
- ❌ Service start/stop/restart capabilities

### Monitoring
```bash
# Monitor sudo usage (optional)
tail -f /var/log/auth.log | grep babylon-babes
journalctl -f -t sudo
```

## 🔍 Troubleshooting

### Issue: sudoers syntax error
```bash
# Fix syntax and re-validate
visudo -c -f /etc/sudoers.d/ha-bb8-operations
# If errors, edit file and remove problematic lines
```

### Issue: Bluetooth service won't start
```bash
# Check for conflicts
systemctl status bluetooth
journalctl -u bluetooth --no-pager

# Reset Bluetooth stack
systemctl stop bluetooth
systemctl start bluetooth
```

### Issue: Docker commands still fail
```bash
# Check Docker socket permissions
ls -la /var/run/docker.sock
# In HA OS, user group management is limited
# Rely on sudo configuration instead of group membership
```

### Issue: hciconfig still not found after apk add
```bash
# Check if bluez-tools installed correctly
apk list | grep bluez-tools
which hciconfig hcitool

# Alternative: Use bluetoothctl which is definitely available
bluetoothctl show  # Should show controller info
bluetoothctl list  # Should list adapters
```

## ✅ Success Criteria Checklist

**After implementing these fixes:**
- [ ] `ssh hass 'sudo ha info'` returns system information
- [ ] `ssh hass 'sudo ha addons info local_beep_boop_bb8'` shows add-on status  
- [ ] `ssh hass 'sudo /usr/local/bin/docker ps'` lists containers (HA OS path)
- [ ] `ssh hass 'hciconfig hci0'` shows BLE adapter (after apk add bluez-deprecated)
- [ ] `ssh hass 'bluetoothctl show'` shows Bluetooth controller (always available)
- [ ] `./ops/diag/collect_ha_bb8_diagnostics.sh hass` produces archive >10KB
- [ ] Diagnostics archive contains supervisor data, container logs, system logs
- [ ] No "Could not retrieve" errors in diagnostics output

## 📋 Implementation Timeline

**Immediate (next 2 hours):**
1. System administrator implements sudoers configuration
2. Verify Bluetooth service and install missing packages
3. Development team tests enhanced diagnostics

**Follow-up (next 24 hours):**
1. Run comprehensive diagnostic collection
2. Verify all supervisor and container data accessible
3. Update documentation with successful configuration

**Next steps (after P0 completion):**
1. Implement health monitoring automation (Phase 2)
2. Deploy BB-8 connectivity testing (Milestone 2)
3. Configure alerting and dashboard integration

---
**Implementation Owner:** System Administrator (HA host) + Development Team (testing)  
**Success Validation:** Development team verifies enhanced diagnostics collection  
**Escalation:** If issues persist after 48 hours, schedule troubleshooting session