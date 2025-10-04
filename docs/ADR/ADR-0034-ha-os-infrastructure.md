---
id: ADR-0034
title: "Home Assistant OS Development Environment Infrastructure"
date: 2025-09-28
status: Accepted
author:
  - Operational Evidence Analysis
  - Infrastructure Reconnaissance (P0 Implementation)
  - Copilot Claude
related: ["ADR-0031", "ADR-0032", "ADR-0010", "ADR-0035", "ADR-0008"]
supersedes: []
last_updated: 2025-10-04
tags: ["infrastructure", "alpine-linux", "docker", "bluetooth", "ble", "supervisor", "authentication", "diagnostics", "ha-os"]
references:
  - P0 critical fixes implementation and diagnostics collection
  - development/workspace-intake-20250928 session evidence
evidence_sessions:
  - 2025-10-04: "Alpine package compatibility verification - py3-venv removal, Docker build fixes, deployment pipeline resolution"
---

# ADR-0034: Home Assistant OS Development Environment Infrastructure  

## Context

During the comprehensive workspace intake and P0 critical fixes implementation, extensive reconnaissance was performed on the Home Assistant OS environment to resolve operational stability issues. This ADR canonicalizes the infrastructure knowledge gained through direct system inspection, command execution, and troubleshooting.

### Problem Statement

The HA-BB8 add-on development required detailed understanding of:
- Home Assistant OS architecture and package management
- Docker container runtime environment and paths
- Bluetooth/BLE infrastructure and tool availability
- Supervisor API authentication and access patterns
- Permission models and sudo configuration requirements

### Investigation Method

- Direct SSH inspection of HA OS environment
- Package manager and service discovery (`apk`, Alpine Linux identification)
- Docker path resolution and container inspection
- Bluetooth tools availability and installation
- Supervisor CLI authentication testing
- Enhanced diagnostics script development and validation

## Decision

### Technical Architecture Findings

**Operating System Foundation:**
```bash
# Confirmed: Alpine Linux v3.22 (not Debian/Ubuntu)
NAME="Alpine Linux"
ID=alpine
VERSION_ID=3.22.1
PRETTY_NAME="Alpine Linux v3.22"
```

**Package Management:**
- ✅ Package Manager: `apk` (Alpine Package Keeper)
- ❌ NOT available: `apt-get`, `yum`, `dnf`, `systemctl`, `usermod`
- ✅ Service Management: s6 overlay system (not systemd)

**Alpine Package Compatibility (Critical for Dockerfile):**
```bash
# Available Alpine 3.22 packages for Python development
python3           # Core Python 3 interpreter
py3-pip          # Python package installer
python3-dev      # Python development headers
build-base       # GCC, make, libc-dev (equivalent to build-essential)
ca-certificates  # SSL certificate bundle
bash             # Bash shell (not always default in minimal Alpine)
jq               # JSON processor

# REMOVED packages (do not exist in Alpine 3.22):
py3-venv         # ❌ NOT AVAILABLE - Python3 includes venv by default
python3-venv     # ❌ NOT AVAILABLE - use python3 -m venv instead
```

**Docker Build Implications:**
- **HA Supervisor Override**: Always uses Alpine base regardless of Dockerfile BUILD_FROM
- **Package Manager**: Must use `apk add` not `apt-get` in Dockerfiles
- **Python Venv**: Use `python3 -m venv` (py3-venv package doesn't exist)

**Docker Infrastructure:**
```bash
# Docker 28.3.3 location (critical for diagnostics)
/usr/local/bin/docker  # NOT /usr/bin/docker
Docker version 28.3.3, build 980b85681696fbd95927fd8ded8f6d91bdca95b0
```

**Bluetooth/BLE Infrastructure:**
```bash
# Required package for hciconfig/hcitool
apk add bluez-deprecated  # NOT bluez-tools (doesn't exist)

# Tools available after installation
/usr/bin/bluetoothctl    # Always available
/usr/bin/hciconfig       # After bluez-deprecated
/usr/bin/hcitool         # After bluez-deprecated

# Detected adapters
hci0: Type: Primary Bus: USB (BC:07:1D:48:04:5A)
hci1: Type: Primary Bus: UART (2C:CF:67:65:F9:00)
```

**Home Assistant Supervisor:**
```bash
# CLI available but authentication restricted
/usr/bin/ha              # Present and executable
# Returns: 401 unauthorized for non-privileged users
# Requires: System-level authentication or proper supervisor group membership
```

### Permission Model and Security

**User Context:**
```bash
# SSH user context
User: babylon-babes
Groups: babylon-babes wheel
# No direct supervisor access despite wheel group membership
```

**Sudoers Configuration (Working):**
```bash
# /etc/sudoers.d/ha-bb8-operations
Defaults:babylon-babes !requiretty
babylon-babes ALL=(root) NOPASSWD: /usr/bin/ha*
babylon-babes ALL=(root) NOPASSWD: /usr/local/bin/docker ps*, /usr/local/bin/docker logs*, /usr/local/bin/docker inspect*, /usr/local/bin/docker exec* env, /usr/local/bin/docker exec* ls*
babylon-babes ALL=(root) NOPASSWD: /bin/journalctl*, /usr/bin/journalctl*
```

**Authentication Limitation:**
- Sudoers configuration validated and active
- Docker commands work via sudo with correct paths
- HA Supervisor API returns 401 even with sudo (authentication vs authorization issue)
- Suggests Supervisor requires system-level token or specific user context

### Enhanced Diagnostics Capabilities

**Successful Data Collection:**
- ✅ Network connectivity (MQTT broker: 192.168.0.129:1883)
- ✅ BLE adapter inspection (both USB and UART adapters)
- ✅ Docker container enumeration and inspection
- ✅ Enhanced error messaging with actionable Alpine commands

**Diagnostic Script Improvements:**
```bash
# Enhanced with HA OS specific paths and error messages
sudo /usr/local/bin/docker ps --filter name=addon_${ADDON_SLUG}
sudo ha info  # With informative error: "try: sudo ha info"
hciconfig hci0  # With fallback to bluetoothctl diagnostics
```

## Implementation Evidence

### Commands Verified
```bash
# Alpine package management
apk update && apk list | grep bluez
apk add bluez-deprecated

# Docker with correct paths
sudo /usr/local/bin/docker ps --filter name=addon
sudo /usr/local/bin/docker logs <container_id>

# Bluetooth infrastructure
hciconfig hci0  # Shows full adapter details
bluetoothctl show  # Always available fallback

# Permission validation
sudo -l | grep ha  # Shows allowed commands
visudo -c -f /etc/sudoers.d/ha-bb8-operations  # Syntax validation
```

### Log Patterns Observed
```bash
# Successful BLE detection
✓ BLE adapter accessible
hci0: Type: Primary Bus: USB
      BD Address: BC:07:1D:48:04:5A ACL MTU: 1021:6 SCO MTU: 255:12
      UP RUNNING

# Supervisor authentication failure
unexpected server response. Status code: 401
time="2025-09-28T19:36:25+01:00" level=error msg="unexpected server response. Status code: 401"

# Docker access success
CONTAINER ID   IMAGE                                             COMMAND
c358ba8b9c4f   homeassistant/aarch64-addon-matter-server:8.1.1   "/init"
```

### Configuration Discovered
- **25+ active containers** in HA environment
- **Mosquitto MQTT broker** on ports 1883-1884, 8883-8884
- **Multiple BLE adapters** available for device connectivity
- **s6 service supervision** with proper init system

## Consequences

### Positive
- **Complete infrastructure map** for HA OS development environment
- **Reliable BLE access** restored with correct Alpine packages
- **Docker integration** working with proper paths
- **Enhanced diagnostics** providing actionable troubleshooting information
- **Security model** understood with minimal privilege implementation

### Negative
- **Supervisor API access** remains limited (requires further investigation)
- **Platform-specific knowledge** required (Alpine vs Debian differences)
- **Package ecosystem** constraints (limited tool availability)

### Unknown/Untested
- **Root user Supervisor access** (may resolve 401 issues)
- **Alternative authentication mechanisms** for Supervisor API
- **Long-term stability** of sudo-based diagnostic collection

## Implementation Guidance

### For Add-on Development
1. **Target Alpine Linux 3.22** (not Debian) for package compatibility
2. **Use Docker path:** `/usr/local/bin/docker` in all scripts and diagnostics
3. **Install BLE tools:** `apk add bluez-deprecated` for hciconfig/hcitool
4. **Implement sudoers:** Minimal privilege access for operational commands

### For Diagnostics and Monitoring
1. **Enhanced error messages** with platform-specific guidance
2. **Fallback mechanisms** (bluetoothctl when hciconfig unavailable)
3. **Path-aware commands** using full Alpine/HA OS paths
4. **Permission-aware operations** with sudo prefixes

### For Troubleshooting
1. **Check Alpine packages:** `apk list | grep <package>`
2. **Verify Docker paths:** `/usr/local/bin/docker` not `/usr/bin/docker`
3. **Test BLE infrastructure:** `hciconfig` and `bluetoothctl show`
4. **Validate sudoers:** `sudo -l` and `visudo -c`

## References

### Session Evidence
- **SSH inspection outputs:** Operating system identification, package discovery
- **Docker path resolution:** Version verification and container enumeration
- **BLE infrastructure testing:** Adapter detection and tool installation
- **Sudoers configuration:** Syntax validation and permission testing
- **Enhanced diagnostics:** Multiple diagnostic runs with improved error reporting

### Related ADRs
- **ADR-0031:** Supervisor-only operations testing (authentication patterns)
- **ADR-0032:** Device connectivity patterns (BLE infrastructure requirements)
- **ADR-0010:** Process supervision (s6 service management context)

### Technical Validation
- **P0 Critical Fixes:** 2/3 resolved (BLE infrastructure, container monitoring)
- **Diagnostic Enhancement:** Archive size increased, error messages improved
- **Security Implementation:** Minimal privilege sudoers configuration validated

---

**Evidence Quality:** Complete  
**Session Impact:** Enables reliable P1/P2 development phases  
**Maintenance:** Update when HA OS version changes or new infrastructure patterns discovered

## TOKEN_BLOCK

```yaml
TOKEN_BLOCK:
  accepted:
    - HA_OS_INFRASTRUCTURE_MAPPED
    - ALPINE_LINUX_CONFIRMED
    - DOCKER_PATHS_VALIDATED
    - BLE_INFRASTRUCTURE_RESTORED
    - DIAGNOSTICS_ENHANCED
    - SUPERVISOR_AUTH_DOCUMENTED
  produces:
    - HA_OS_FOUNDATION_COMPLETE
    - P1_P2_DEVELOPMENT_ENABLED
  requires:
    - ADR_SCHEMA_V1
    - ADR_FORMAT_OK
  drift:
    - DRIFT: supervisor-401-unresolved
    - DRIFT: platform-specific-knowledge-required
```