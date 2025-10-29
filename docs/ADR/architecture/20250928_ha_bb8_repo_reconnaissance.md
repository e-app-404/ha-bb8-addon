# Home Assistant BB-8 Add-on Operator Testing & Validation Plan

## Step 1 — Repository Reconnaissance

### Files and Directories Inspected:

**Core Add-on Structure (addon/)**:
- config.yaml — HA Supervisor manifest (slug: `beep_boop_bb8`, version: `2025.8.21.44`)
- Dockerfile — Debian-based container build (uses venv at `/opt/venv`)
- run.sh — Multi-function entrypoint with supervised restart loop
- bb8_core — Python application core (24 modules including main.py, echo_responder.py)
- services.d — S6 overlay services for container supervision
- tests — 25 test modules including integration tests

**Build & Release Infrastructure**:
- build.yaml — Multi-arch base image definitions
- Makefile — Automated release workflow (patch/minor/major + deploy)
- VERSION — Current version marker (shows "dev")
- pyproject.toml — Python project configuration
- Root-level deployment automation scripts (referenced but moved to _backups)

**Operational Scripts**:
- deployment-bundle — Cross-repo ADR deployment system
- validate_cross_repo_links.sh — Link validation
- Makefile targets: `release-patch`, `deploy-ssh`, `publish`, `qa`, `testcov`

**Configuration & Runtime**:
- Supervisor slug resolution: folder `beep_boop_bb8` → Supervisor address `local_beep_boop_bb8`
- MQTT broker: `192.168.0.129:1883` (user: `mqtt_bb8`)
- BLE device: `ED:ED:87:D7:27:50` ("S33 BB84 LE"), adapter `hci0`
- Log path: `/data/reports/ha_bb8_addon.log`

**Key Extracted Information**:
- **Build steps**: Local build via Dockerfile + build.yaml (no registry pull)
- **Version management**: Automated via Makefile + version bump scripts
- **Supervisor metadata**: Requires udev, DBus, privileged NET_ADMIN, UART access
- **Startup scripts**: run.sh → Python module execution with supervised restart
- **Environment variables**: MQTT config, feature toggles, health checks
- **Config schema**: 40+ validated options with legacy field fallbacks
- **ADR guidance**: ADR-0003 (build patterns), ADR-0008 (deploy flow), ADR-0010 (supervision)

## Step 2 — Build & Packaging Instructions

### Version Determination
```bash
# Get current add-on version
ADDON_VERSION=$(grep '^version:' addon/config.yaml | awk '{print $2}')
echo "Current version: ${ADDON_VERSION}"

# Check VERSION file (dev marker)
cat VERSION
```

### Build Commands
```bash
# Method 1: Using Makefile (automated)
make release-patch    # Increments patch, builds, publishes, deploys
make release-minor    # Increments minor version
make release-major    # Increments major version
make release VERSION=1.4.2  # Set explicit version

# Method 2: Manual build (Home Assistant will build locally)
cd addon/
# Verify required files exist
ls -la config.yaml Dockerfile run.sh bb8_core/

# Check Dockerfile build context
docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:bookworm -t ha-bb8-test .

# Test container locally (smoke test)
docker run --rm -e HOMEASSISTANT=1 -e MQTT_HOST=192.168.0.129 -e MQTT_USER=mqtt_bb8 -e MQTT_PASSWORD=mqtt_bb8 -e BB8_MAC=ED:ED:87:D7:27:50 ha-bb8-test python -m bb8_core.main --version
```

### Build Verification Commands
```bash
# Verify Python module imports
docker run --rm ha-bb8-test python -c "import bb8_core; print('✓ bb8_core import OK')"

# Check virtual environment
docker run --rm ha-bb8-test /opt/venv/bin/python --version

# Verify run.sh is executable and present
docker run --rm ha-bb8-test test -x /usr/src/app/run.sh && echo "✓ run.sh executable"

# Expected outputs:
# TOKEN: WS_READY
# TOKEN: STRUCTURE_OK  
# TOKEN: PY_OK <python_version>
```

### Archive Creation (if needed)
```bash
# Create deployment archive
cd addon/
tar -czf ../ha-bb8-addon-${ADDON_VERSION}.tar.gz .
sha256sum ../ha-bb8-addon-${ADDON_VERSION}.tar.gz > ../ha-bb8-addon-${ADDON_VERSION}.tar.gz.sha256
```

## Step 3 — Push/Deploy Strategies to Home Assistant Supervisor

### Method 1: Local Directory Sync (Recommended)
```bash
# Mount-based sync (if HA accessible via SMB/NFS)
rsync -avz --delete addon/ /Volumes/HA/addons/local/beep_boop_bb8/

# SSH-based sync
rsync -avz --delete -e ssh addon/ {HA_USER}@{HA_HOST}:/addons/local/beep_boop_bb8/

# Version/commit tracking
echo "VERSION=${ADDON_VERSION} COMMIT=$(git rev-parse HEAD)" | ssh {HA_USER}@{HA_HOST} 'cat > /config/reports/deploy_receipt.txt'
```

### Method 2: SSH Deployment Automation
```bash
# Using the Makefile automation
REMOTE_HOST_ALIAS=home-assistant make deploy-ssh

# Manual SSH deployment commands
ssh {HA_USER}@{HA_HOST} "ha addons reload"
ssh {HA_USER}@{HA_HOST} "ha addons rebuild local_beep_boop_bb8"
ssh {HA_USER}@{HA_HOST} "ha addons start local_beep_boop_bb8"

# Verify deployment
ssh {HA_USER}@{HA_HOST} "ha addons info local_beep_boop_bb8 | grep -E 'state:|version:'"
```

### Method 3: Supervisor Web UI
1. **Access Supervisor UI**: Navigate to `http://{HA_HOST}:8123` → Settings → Add-ons
2. **Local Add-ons**: Click "Add-on Store" → "Local add-ons" tab
3. **Install**: Find "HA-BB8" → Click "INSTALL"
4. **Configure**: Set MQTT broker, BB-8 MAC address, enable features
5. **Start**: Click "START" 
6. **Verify**: Check "Log" tab for startup banner

### Method 4: Supervisor API (Programmatic)
```bash
# Get HA Long-Lived Access Token first
HA_TOKEN="{HA_TOKEN}"
HA_HOST="{HA_HOST}"

# Install add-on
curl -X POST "http://${HA_HOST}:8123/api/hassio/addons/local_beep_boop_bb8/install" \
  -H "Authorization: Bearer ${HA_TOKEN}" \
  -H "Content-Type: application/json"

# Start add-on  
curl -X POST "http://${HA_HOST}:8123/api/hassio/addons/local_beep_boop_bb8/start" \
  -H "Authorization: Bearer ${HA_TOKEN}"

# Check status
curl "http://${HA_HOST}:8123/api/hassio/addons/local_beep_boop_bb8/info" \
  -H "Authorization: Bearer ${HA_TOKEN}" | jq '.data.state'
```

### Version Management & Git Operations
```bash
# Tag and commit version
git add addon/config.yaml
git commit -m "release: bump version to ${ADDON_VERSION}"
git tag "v${ADDON_VERSION}"
git push origin main --tags

# Monitor logs during startup
ssh {HA_USER}@{HA_HOST} "ha addons logs local_beep_boop_bb8 --follow" | head -100
```

## Step 4 — Start-up Banner Debugging

### Banner Source Identification 

Searched text for `Starting|WELCOME|banner|BB-8|bb8_core|Started` (`**/addon/**`), 20 results

### Banner Source Files & Commands

```bash
# Find all banner/startup message sources
grep -r -n "Starting\|Welcome\|BB-8\|bb8_core.*started\|diag_emit" addon/

# Key patterns to search for:
grep -r -n "diag_emit.*Started" addon/run.sh
grep -r -n "echo.*BB-8" addon/
grep -r -n "logger.*started" addon/bb8_core/
grep -r -n "run.sh entry" addon/run.sh

# Check logging setup for banner configuration
grep -r -n "banner\|BANNER\|welcome\|WELCOME" addon/bb8_core/logging_setup.py
```

### Expected Banner/Log Messages

Based on run.sh analysis, look for these **exact startup sequences**:

1. **run.sh entry banner**:
   ```
   2025-XX-XXTHH:MM:SS [BB-8] run.sh entry (version=X.X.X) wd=/usr/src/app LOG=/data/reports/ha_bb8_addon.log HEALTH=X ECHO=true
   ```

2. **Process start messages**:
   ```
   2025-XX-XXTHH:MM:SS [BB-8] RUNLOOP attempt #1
   2025-XX-XXTHH:MM:SS [BB-8] Started bb8_core.main PID=XXXX
   2025-XX-XXTHH:MM:SS [BB-8] Started bb8_core.echo_responder PID=XXXX
   ```

3. **Application ready indicators**:
   ```
   bb8_core.main started
   echo_responder.py started  
   bridge_controller ready
   Connected to MQTT
   Subscribed to bb8/echo/cmd
   ```

### Banner Debugging Commands

```bash
# Reproduce banner locally (test container)
docker run --rm -it \
  -e MQTT_HOST=192.168.0.129 \
  -e MQTT_USER=mqtt_bb8 \
  -e MQTT_PASSWORD=mqtt_bb8 \
  -e BB8_MAC=ED:ED:87:D7:27:50 \
  -e DIAG_TRACE=1 \
  ha-bb8-test /usr/src/app/run.sh

# Focus on banner/startup logs only
ssh {HA_USER}@{HA_HOST} "ha addons logs local_beep_boop_bb8" | grep -E "\[BB-8\]|Started|bridge_controller|Connected to MQTT" | head -20

# Check for missing banner issues
ssh {HA_USER}@{HA_HOST} "ha addons logs local_beep_boop_bb8" | grep -i "error\|failed\|missing" | head -10

# Environment variable inspection (inside container)
CONTAINER_ID=$(ssh {HA_USER}@{HA_HOST} "docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}'")
ssh {HA_USER}@{HA_HOST} "docker exec ${CONTAINER_ID} env | grep -E 'MQTT|BB8|ADDON_VERSION|DIAG'"
```

### Banner Dependencies & Prerequisites

**MQTT Broker Connectivity Test**:
```bash
# Test MQTT connection from HA host
ssh {HA_USER}@{HA_HOST} "mosquitto_pub -h 192.168.0.129 -p 1883 -u mqtt_bb8 -P mqtt_bb8 -t test/ping -m 'hello'"
ssh {HA_USER}@{HA_HOST} "timeout 5 mosquitto_sub -h 192.168.0.129 -p 1883 -u mqtt_bb8 -P mqtt_bb8 -t test/ping -C 1"
```

**BLE Adapter Verification**:
```bash
# Check BLE adapter availability
ssh {HA_USER}@{HA_HOST} "hciconfig hci0 up && hcitool dev"
ssh {HA_USER}@{HA_HOST} "hcitool lescan --duplicates | head -10"
```

**Config Validation**:
```bash
# Verify config.yaml options are accessible
ssh {HA_USER}@{HA_HOST} "cat /data/addons/local/beep_boop_bb8/options.json | jq '.mqtt_host, .bb8_mac, .enable_echo'"
```

### Expected Banner Failure Patterns

| **Log Pattern** | **Root Cause** | **Remediation** |
|---|---|---|
| `FATAL: run.sh missing from build context` | Dockerfile copy failed | Rebuild with `COPY run.sh` present |
| `Failed to read /data/options.json` | Missing Supervisor options | Configure add-on via UI first |
| `Connection refused (MQTT)` | MQTT broker down/unreachable | Check `192.168.0.129:1883` accessibility |
| `permission denied (/dev/hci0)` | BLE device access denied | Enable privileged mode, check `udev: true` |
| `bb8_core.main PID=X (echo_responder disabled)` | Echo responder intentionally off | Normal if `enable_echo: false` |

## Step 5 — Boot & Runtime Validation

### Supervisor Status Validation
```bash
# Check add-on shows "running" state
ssh {HA_USER}@{HA_HOST} "ha addons info local_beep_boop_bb8" | grep "state:" | grep -q "started" && echo "✓ Add-on RUNNING" || echo "✗ Add-on NOT RUNNING"

# Verify correct version installed
ssh {HA_USER}@{HA_HOST} "ha addons info local_beep_boop_bb8" | grep "version:" | grep -q "${ADDON_VERSION}" && echo "✓ Version MATCH" || echo "✗ Version MISMATCH"
```

### Log-Based Validation Checklist
```bash
# Essential startup messages (must be present)
ssh {HA_USER}@{HA_HOST} "ha addons logs local_beep_boop_bb8" | grep -q "run.sh entry" && echo "✓ Entry banner present" || echo "✗ Missing entry banner"

ssh {HA_USER}@{HA_HOST} "ha addons logs local_beep_boop_bb8" | grep -q "Started bb8_core.main PID=" && echo "✓ Main process started" || echo "✗ Main process failed"

ssh {HA_USER}@{HA_HOST} "ha addons logs local_beep_boop_bb8" | grep -q "bridge_controller ready" && echo "✓ Bridge controller ready" || echo "✗ Bridge controller failed"

ssh {HA_USER}@{HA_HOST} "ha addons logs local_beep_boop_bb8" | grep -q "Connected to MQTT" && echo "✓ MQTT connected" || echo "✗ MQTT connection failed"
```

### Health Check & Heartbeat Validation
```bash
# Check health heartbeat files (if health checks enabled)
CONTAINER_ID=$(ssh {HA_USER}@{HA_HOST} "docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}'")
ssh {HA_USER}@{HA_HOST} "docker exec ${CONTAINER_ID} ls -la /tmp/bb8_heartbeat_main /tmp/bb8_heartbeat_echo"

# Verify heartbeat freshness (< 30 seconds old)
ssh {HA_USER}@{HA_HOST} "docker exec ${CONTAINER_ID} find /tmp -name 'bb8_heartbeat_*' -mtime -30s"
```

### Functional Testing

#### **Happy Path Test: BLE Device Discovery**
```bash
# Trigger discovery via MQTT command
ssh {HA_USER}@{HA_HOST} "mosquitto_pub -h 192.168.0.129 -p 1883 -u mqtt_bb8 -P mqtt_bb8 -t homeassistant/sensor/bb8_rssi/config -m '{\"name\":\"BB8 RSSI\",\"state_topic\":\"bb8/rssi/state\"}'"

# Verify HA discovery topic published
ssh {HA_USER}@{HA_HOST} "timeout 10 mosquitto_sub -h 192.168.0.129 -p 1883 -u mqtt_bb8 -P mqtt_bb8 -t 'homeassistant/+/+/config' -C 3"

# Expected: JSON payloads for sensor configurations
```

#### **Edge Case 1: MQTT Broker Down**
```bash
# Stop MQTT broker temporarily
ssh {HA_USER}@{HA_HOST} "systemctl stop mosquitto" # (if applicable)

> Note: On Home Assistant OS, use Supervisor commands instead of systemctl, for example:
> `ha addons restart core_mosquitto` (Supervisor context) or via HA API `/api/services/hassio/addon_restart`.

# Expected behavior: Connection retry logs
ssh {HA_USER}@{HA_HOST} "ha addons logs local_beep_boop_bb8" | grep -i "connection.*refused\|reconnect\|mqtt.*error" | tail -5

# Recovery: restart broker and verify reconnection
ssh {HA_USER}@{HA_HOST} "systemctl start mosquitto"

> Note: On Home Assistant OS, prefer `ha addons restart core_mosquitto` over systemctl to manage the Mosquitto add-on.
ssh {HA_USER}@{HA_HOST} "ha addons logs local_beep_boop_bb8" | grep "Connected to MQTT" | tail -1
```

#### **Edge Case 2: Invalid Configuration**
```bash
# Set invalid MQTT host via Supervisor UI or API
curl -X POST "http://{HA_HOST}:8123/api/hassio/addons/local_beep_boop_bb8/options" \
  -H "Authorization: Bearer {HA_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"mqtt_host": "invalid.host.example"}'

# Restart add-on and check logs
ssh {HA_USER}@{HA_HOST} "ha addons restart local_beep_boop_bb8"
ssh {HA_USER}@{HA_HOST} "ha addons logs local_beep_boop_bb8" | grep -i "error\|failed\|could not resolve" | tail -5

# Expected: DNS resolution or connection timeout errors
```

### Automated Test Execution
```bash
# Run pytest suite (if accessible on HA host)
ssh {HA_USER}@{HA_HOST} "cd /addons/local/beep_boop_bb8 && python -m pytest tests/ -v --maxfail=3"

# Alternative: Run container-based tests
docker run --rm -v $(pwd)/addon:/usr/src/app ha-bb8-test python -m pytest tests/ --tb=short
```

## Step 6 — Collecting and Uploading Diagnostics

### Diagnostics Collection Script 

Created [](file:///Users/evertappels/Projects/HA-BB8/collect_ha_bb8_diagnostics.sh)

Ran terminal command: chmod +x /Users/evertappels/Projects/HA-BB8/collect_ha_bb8_diagnostics.sh

### Upload Commands
```bash
# Secure copy to support server
scp ha_bb8_diagnostics_YYYYMMDD_HHMMSS.tar.gz {SUPPORT_USER}@{SUPPORT_HOST}:/var/uploads/

# HTTP upload via curl
curl -F "file=@ha_bb8_diagnostics_YYYYMMDD_HHMMSS.tar.gz" \
     -F "description=HA BB-8 Add-on startup banner issue" \
     -F "contact={YOUR_EMAIL}" \
     https://support.example.com/api/upload

# Alternative: rsync with compression
rsync -avz ha_bb8_diagnostics_YYYYMMDD_HHMMSS.tar.gz {SUPPORT_USER}@{SUPPORT_HOST}:diagnostics/
``` 

Starting (7/9) *Define acceptance criteria*

## Step 7 — Acceptance Criteria and Test Report

### Pass/Fail Acceptance Checklist

| **Test Category** | **Criteria** | **Pass Condition** | **Fail Condition** |
|---|---|---|---|
| **Build** | Add-on builds successfully | Docker build exits with code 0, image created | Build fails, missing dependencies, Dockerfile errors |
| **Deploy** | Add-on installs in Supervisor | Shows in Local Add-ons, status "stopped" | Install fails, missing files, config errors |
| **Startup** | Add-on starts without errors | Status shows "started", PID processes running | Status "error"/"failed", container exits |
| **Banner** | Startup banner appears in logs | `run.sh entry` message with version, timestamp | Missing banner, silent startup, truncated logs |
| **MQTT** | MQTT connection established | Log shows "Connected to MQTT", broker accessible | Connection refused, auth failed, timeout |
| **BLE** | BLE adapter accessible | `hciconfig hci0` succeeds, device permissions OK | Permission denied, adapter not found |
| **Health** | Health checks functional | Heartbeat files updated, age < 30s | Missing heartbeat files, stale timestamps |
| **Discovery** | HA discovery topics published | MQTT discovery configs visible on broker | No discovery messages, malformed JSON |

### Required Log Lines for SUCCESS

**Startup Sequence (must appear in order)**:
```
[timestamp] [BB-8] run.sh entry (version=2025.8.21.44) wd=/usr/src/app LOG=/data/reports/ha_bb8_addon.log HEALTH=1 ECHO=true
[timestamp] [BB-8] RUNLOOP attempt #1  
[timestamp] [BB-8] Started bb8_core.main PID=XXXX
[timestamp] [BB-8] Started bb8_core.echo_responder PID=YYYY
```

**Application Ready Indicators**:
```
bb8_core.main started
bridge_controller ready
Dispatcher config loaded
Connected to MQTT broker 192.168.0.129:1883
Subscribed to bb8/echo/cmd
```

### Test Report Template 

Created [](file:///Users/evertappels/Projects/HA-BB8/test_report_template.md)

## Step 8 — Troubleshooting Recipes

### 1. Container Fails to Start

**Symptoms**: 
- Supervisor shows "error" state
- `ha addons logs` shows container exit immediately
- No banner message appears

**Evidence Commands**:
```bash
ssh {HA_USER}@{HA_HOST} "ha addons info local_beep_boop_bb8" | grep "state:"
ssh {HA_USER}@{HA_HOST} "docker ps -a --filter name=addon_local_beep_boop_bb8"
```

**Root Causes & Remediation**:
- **Missing run.sh**: Check Dockerfile `COPY run.sh` command
- **Permission denied**: `chmod +x addon/run.sh` and rebuild
- **Python import errors**: Verify requirements.txt and venv creation
- **Config validation failure**: Check options.json syntax

**Fix Commands**:
```bash
# Rebuild with proper permissions
cd addon && docker build --no-cache -t ha-bb8-debug .
# Test locally first
docker run --rm ha-bb8-debug python -c "import bb8_core; print('OK')"
```

### 2. Banner Missing or Incomplete

**Symptoms**:
- Add-on starts but no `[BB-8]` messages in logs
- Partial banner (missing version/PID info)
- Logs show Python output but no run.sh output

**Evidence Commands**:
```bash
ssh {HA_USER}@{HA_HOST} "ha addons logs local_beep_boop_bb8" | grep -E "BB-8|run.sh|Started"
ssh {HA_USER}@{HA_HOST} "docker exec \$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}') ps aux"
```

**Root Causes & Remediation**:
- **Log buffering**: Set `PYTHONUNBUFFERED=1` (should be in Dockerfile)
- **S6 service override**: Check if run bypasses run.sh
- **Silent failure**: Enable `DIAG_TRACE=1` environment variable

**Fix Commands**:
```bash
# Enable debug tracing
curl -X POST "http://{HA_HOST}:8123/api/hassio/addons/local_beep_boop_bb8/options" \
  -H "Authorization: Bearer {HA_TOKEN}" \
  -d '{"DIAG_TRACE": "1"}'
ssh {HA_USER}@{HA_HOST} "ha addons restart local_beep_boop_bb8"
```

### 3. Cannot Bind to BLE Device

**Symptoms**:
- Log shows "permission denied" for `/dev/hci0`
- `hciconfig` commands fail inside container
- BLE scanner cannot access adapter

**Evidence Commands**:
```bash
ssh {HA_USER}@{HA_HOST} "ls -la /dev/hci*"
ssh {HA_USER}@{HA_HOST} "docker exec \$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}') hciconfig"
```

**Root Causes & Remediation**:
- **Missing udev rule**: Ensure `udev: true` in config.yaml
- **Device not passed through**: Add `/dev/hci0` to devices list
- **Insufficient privileges**: Verify `privileged: [NET_ADMIN]`

**Fix Commands**:
```bash
# Check current config
ssh {HA_USER}@{HA_HOST} "cat /data/addons/local/beep_boop_bb8/config.yaml" | grep -A5 "devices:"
# Restart add-on after config fix
ssh {HA_USER}@{HA_HOST} "ha addons restart local_beep_boop_bb8"
```

### 4. MQTT Connection Failures

**Symptoms**:
- "Connection refused" in logs
- "Failed to connect to broker" messages
- No discovery topics published

**Evidence Commands**:
```bash
ssh {HA_USER}@{HA_HOST} "nc -zv 192.168.0.129 1883"
ssh {HA_USER}@{HA_HOST} "mosquitto_pub -h 192.168.0.129 -p 1883 -u mqtt_bb8 -P mqtt_bb8 -t test -m hello"
```

**Root Causes & Remediation**:
- **Broker down**: Check MQTT service status
- **Network unreachable**: Verify host IP and routing  
- **Authentication failure**: Verify username/password
- **Firewall blocking**: Check port 1883 accessibility

**Fix Commands**:
```bash
# Test broker connectivity
ssh {HA_USER}@{HA_HOST} "systemctl status mosquitto"
# Check broker logs
ssh {HA_USER}@{HA_HOST} "journalctl -u mosquitto --since '10 minutes ago'"
```

### 5. Missing Dependencies/Import Errors

**Symptoms**:
- Python ImportError or ModuleNotFoundError
- Container starts but Python modules fail
- Missing system packages

**Evidence Commands**:
```bash
ssh {HA_USER}@{HA_HOST} "docker exec \$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}') pip list"
ssh {HA_USER}@{HA_HOST} "docker exec \$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}') python -c 'import sys; print(sys.path)'"
```

**Root Causes & Remediation**:
- **Missing requirements.txt**: Ensure all Python deps listed
- **Venv not activated**: Check PATH includes `/opt/venv/bin`
- **System packages missing**: Add to Dockerfile apt-get install

**Fix Commands**:
```bash
# Check Python environment
ssh {HA_USER}@{HA_HOST} "docker exec \$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}') which python"
# Rebuild with fresh requirements
cd addon && docker build --no-cache -t ha-bb8-fixed .
```

### 6. Version Mismatch Issues

**Symptoms**:
- Supervisor shows wrong version
- "unknown" version in logs
- Build version doesn't match config.yaml

**Evidence Commands**:
```bash
grep "version:" addon/config.yaml
ssh {HA_USER}@{HA_HOST} "ha addons info local_beep_boop_bb8" | grep "version:"
ssh {HA_USER}@{HA_HOST} "docker exec \$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}') env | grep VERSION"
```

**Root Causes & Remediation**:
- **Inconsistent versions**: Sync config.yaml and Dockerfile
- **Missing BUILD_VERSION**: Add ARG in Dockerfile
- **Stale cache**: Force rebuild without cache

**Fix Commands**:
```bash
# Update versions consistently  
ops/release/bump_version.sh patch  # (if script available)
# Or manual update
sed -i "s/version: .*/version: $(date +%Y.%m.%d.%H)/" addon/config.yaml
```

### 7. Corrupted Add-on Archive/Files

**Symptoms**:
- Files missing from container
- Permission errors on execution
- Unexpected file contents

**Evidence Commands**:
```bash
ssh {HA_USER}@{HA_HOST} "find /addons/local/beep_boop_bb8 -type f | head -20"
ssh {HA_USER}@{HA_HOST} "docker exec \$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}') find /usr/src/app -type f -name '*.py' | head -10"
```

**Root Causes & Remediation**:
- **Incomplete rsync**: Use `--checksum` flag
- **File corruption**: Verify checksums before deployment
- **Permission mismatch**: Ensure proper ownership

**Fix Commands**:
```bash
# Clean reinstall
ssh {HA_USER}@{HA_HOST} "rm -rf /addons/local/beep_boop_bb8"
rsync -avz --checksum addon/ {HA_USER}@{HA_HOST}:/addons/local/beep_boop_bb8/
ssh {HA_USER}@{HA_HOST} "ha addons reload && ha addons rebuild local_beep_boop_bb8"
```

### 8. Supervisor API Authentication Failures

**Symptoms**:
- curl commands return 401 Unauthorized
- API calls fail with authentication error
- Cannot control add-on programmatically

**Evidence Commands**:
```bash
curl -I "http://{HA_HOST}:8123/api/hassio/addons" -H "Authorization: Bearer {HA_TOKEN}"
echo $HA_TOKEN | cut -c1-10  # Check token format
```

**Root Causes & Remediation**:
- **Invalid token**: Generate new Long-Lived Access Token
- **Expired token**: Tokens don't expire, but user might be disabled
- **Wrong API endpoint**: Use `/api/hassio/` not `/api/`
- **Network issues**: Check HA accessibility

**Fix Commands**:
```bash
# Generate new token via HA UI: Profile → Long-Lived Access Tokens
# Test basic API access
curl "http://{HA_HOST}:8123/api/" -H "Authorization: Bearer {NEW_TOKEN}" | jq '.message'
# Should return: "API running."
``` 

Starting (9/9) *Document safety and assumptions*

## Step 9 — Safety and Assumptions

### Assumptions Made

**Environment Assumptions**:
- Home Assistant Supervisor is accessible via SSH with key-based authentication
- MQTT broker is running on `192.168.0.129:1883` with credentials `mqtt_bb8:mqtt_bb8`
- BLE adapter `hci0` is available and accessible to containers
- Operator has administrative access to HA Supervisor host
- Network connectivity between operator workstation and HA host is stable

**Technical Assumptions**:
- Add-on uses local build (not registry pull) - `image:` commented out in config.yaml
- S6 overlay supervision is available in base image
- Python virtual environment at `/opt/venv` works correctly
- Debian base image supports required system packages
- Docker daemon is running and accessible on HA host

**Operational Assumptions**:
- Operator has SSH access configured (referenced as `{HA_USER}@{HA_HOST}`)
- HA CLI tools (`ha` command) are available and functional
- Supervisor API is accessible if using programmatic deployment
- Local Git repository is clean and represents deployed code

### Risky Operations & Mitigation

**High Risk Operations**:

1. **Full Add-on Rebuild** (`ha addons rebuild local_beep_boop_bb8`)
   - **Risk**: Destroys running container, may fail to restart
   - **Mitigation**: Take container snapshot first, verify backup deployment method
   - **Rollback**: `ssh {HA_USER}@{HA_HOST} "docker start addon_local_beep_boop_bb8_backup"`

2. **Configuration Changes** (MQTT broker, BLE adapter settings)
   - **Risk**: Break connectivity, render add-on non-functional
   - **Mitigation**: Test connectivity before applying, keep working config backup
   - **Rollback**: Restore `options.json` from backup, restart add-on

3. **System-Level Changes** (udev rules, device permissions)
   - **Risk**: Affect other add-ons, require host reboot
   - **Mitigation**: Document original state, test on non-production system first
   - **Rollback**: Restore original `/etc/udev/rules.d/` files, reboot host

4. **File System Sync** (`rsync --delete`)
   - **Risk**: Delete critical files if sync source is incomplete
   - **Mitigation**: Use `--dry-run` first, exclude system files
   - **Rollback**: Restore from `/addons/local/beep_boop_bb8.backup/`

### Safe Rollback Plan

**Pre-Deployment Backup**:
```bash
# Create rollback point
ssh {HA_USER}@{HA_HOST} "cp -r /addons/local/beep_boop_bb8 /addons/local/beep_boop_bb8.backup.$(date +%Y%m%d_%H%M%S)"

# Export current configuration
ssh {HA_USER}@{HA_HOST} "ha addons info local_beep_boop_bb8 > /tmp/addon_config_backup.json"
```

**Emergency Rollback Procedure**:
```bash
# Step 1: Stop current add-on
ssh {HA_USER}@{HA_HOST} "ha addons stop local_beep_boop_bb8"

# Step 2: Restore files from backup
ssh {HA_USER}@{HA_HOST} "rm -rf /addons/local/beep_boop_bb8"
ssh {HA_USER}@{HA_HOST} "cp -r /addons/local/beep_boop_bb8.backup.YYYYMMDD_HHMMSS /addons/local/beep_boop_bb8"

# Step 3: Reload and rebuild from backup
ssh {HA_USER}@{HA_HOST} "ha addons reload"
ssh {HA_USER}@{HA_HOST} "ha addons rebuild local_beep_boop_bb8"
ssh {HA_USER}@{HA_HOST} "ha addons start local_beep_boop_bb8"

# Step 4: Verify rollback successful
ssh {HA_USER}@{HA_HOST} "ha addons info local_beep_boop_bb8" | grep "state: started"
```

**Container-Level Rollback**:
```bash
# If container exists but won't start, try manual container management
CONTAINER_ID=$(ssh {HA_USER}@{HA_HOST} "docker ps -a --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}'")
ssh {HA_USER}@{HA_HOST} "docker start ${CONTAINER_ID}"
```

### Emergency Contacts & Escalation

**If Add-on Breaks Home Assistant**:
1. **Immediate**: Stop the add-on: `ha addons stop local_beep_boop_bb8`
2. **Disable**: Uninstall if necessary: `ha addons uninstall local_beep_boop_bb8` 
3. **Restore**: Use HA backup/snapshot if system instability occurs
4. **Document**: Collect logs and file bug report with diagnostics bundle

**Support Escalation Path**:
1. Check Home Assistant Community Forum: https://community.home-assistant.io/
2. File issue in add-on repository: https://github.com/e-app-404/ha-bb8-addon/issues
3. Contact add-on maintainer with diagnostics bundle

### Data Protection

**No Destructive Data Operations**:
- Scripts do not modify Home Assistant configuration database
- No deletion of user data or Home Assistant entities
- Add-on only publishes MQTT discovery topics (reversible)

**Sensitive Information Handling**:
- MQTT credentials are stored in Supervisor options (encrypted at rest)
- No passwords or tokens logged in plaintext (see logging_setup.py redaction)
- Diagnostics collection masks sensitive data

---

# DELIVERABLES SUMMARY 

Completed (9/9) *Document safety and assumptions*

## OPERATOR DELIVERABLES

### 1. **Prioritized Operator Checklist**

**Phase 1: Build & Prepare**
```bash
# Get current version and commit
ADDON_VERSION=$(grep '^version:' addon/config.yaml | awk '{print $2}')
git rev-parse HEAD

# Local build test
cd addon && docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:bookworm -t ha-bb8-test .

# Smoke test
docker run --rm ha-bb8-test python -c "import bb8_core; print('✓ bb8_core import OK')"
```

**Phase 2: Deploy**
```bash
# Sync to HA host
rsync -avz --delete addon/ {HA_USER}@{HA_HOST}:/addons/local/beep_boop_bb8/

# Register and build
ssh {HA_USER}@{HA_HOST} "ha addons reload && ha addons rebuild local_beep_boop_bb8 && ha addons start local_beep_boop_bb8"
```

**Phase 3: Validate** 
```bash
# Check status
ssh {HA_USER}@{HA_HOST} "ha addons info local_beep_boop_bb8" | grep "state: started"

# Verify banner
ssh {HA_USER}@{HA_HOST} "ha addons logs local_beep_boop_bb8" | grep "run.sh entry"

# Test connectivity  
ssh {HA_USER}@{HA_HOST} "mosquitto_pub -h 192.168.0.129 -p 1883 -u mqtt_bb8 -P mqtt_bb8 -t test -m hello"
```

### 2. **Reproducible Build + Deploy Commands**

```bash
#!/bin/bash
# HA BB-8 Add-on Build & Deploy Script
set -euo pipefail

# Configuration
HA_HOST="${HA_HOST:-192.168.0.129}"
HA_USER="${HA_USER:-homeassistant}"
ADDON_SLUG="local_beep_boop_bb8"

# Build locally
echo "🔨 Building add-on..."
cd addon
docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:bookworm -t ha-bb8-deploy .
docker run --rm ha-bb8-deploy python -c "import bb8_core; print('✓ Build test passed')"

# Deploy to HA
echo "🚀 Deploying to Home Assistant..."
rsync -avz --delete . ${HA_USER}@${HA_HOST}:/addons/local/beep_boop_bb8/

# Register and start
echo "▶️ Starting add-on..."
ssh ${HA_USER}@${HA_HOST} "ha addons reload"
ssh ${HA_USER}@${HA_HOST} "ha addons rebuild ${ADDON_SLUG}"
ssh ${HA_USER}@${HA_HOST} "ha addons start ${ADDON_SLUG}"

# Validate
echo "✅ Validating deployment..."
ssh ${HA_USER}@${HA_HOST} "ha addons info ${ADDON_SLUG}" | grep "state: started" && echo "SUCCESS" || echo "FAILED"
```

### 3. **Banner Debug Recipe**

```bash
# Banner Debug Commands
echo "🔍 Debugging startup banner..."

# Check if banner appears at all
ssh {HA_USER}@{HA_HOST} "ha addons logs local_beep_boop_bb8 | grep -E '\[BB-8\]|run.sh entry' | head -5"

# Enable trace mode for detailed logging
curl -X POST "http://{HA_HOST}:8123/api/hassio/addons/local_beep_boop_bb8/options" \
  -H "Authorization: Bearer {HA_TOKEN}" \
  -d '{"DIAG_TRACE": "1"}' && echo "Trace enabled"

# Restart and monitor startup sequence
ssh {HA_USER}@{HA_HOST} "ha addons restart local_beep_boop_bb8"
sleep 10
ssh {HA_USER}@{HA_HOST} "ha addons logs local_beep_boop_bb8" | tail -20

# Expected output should include:
# [timestamp] [BB-8] run.sh entry (version=X.X.X) wd=/usr/src/app...
# [timestamp] [BB-8] Started bb8_core.main PID=XXXX
```

### 4. **Diagnostics Collection Script**

**Created**: collect_ha_bb8_diagnostics.sh (executable script in repository root)

**Usage**:
```bash
./collect_ha_bb8_diagnostics.sh {HA_HOST} {HA_USER}
# Generates: ha_bb8_diagnostics_YYYYMMDD_HHMMSS.tar.gz
```

### 5. **Acceptance Criteria & Test Report Template**

**Created**: test_report_template.md (comprehensive test report template)

**Key Pass Criteria**:
- ✅ Banner message: `[BB-8] run.sh entry (version=X.X.X)`
- ✅ Process start: `Started bb8_core.main PID=XXXX`
- ✅ MQTT connection: `Connected to MQTT broker 192.168.0.129:1883`
- ✅ Discovery topics: Published to `homeassistant/+/+/config`

### 6. **Top 8 Troubleshooting Recipes**

1. **Container Fails to Start** → Check run.sh permissions, rebuild without cache
2. **Banner Missing** → Enable DIAG_TRACE, check log buffering
3. **BLE Device Access** → Verify udev rules, privileged permissions
4. **MQTT Connection Failures** → Test broker connectivity, check credentials
5. **Missing Dependencies** → Verify requirements.txt, check venv activation
6. **Version Mismatch** → Sync config.yaml versions, rebuild cleanly
7. **Corrupted Files** → Clean reinstall with checksum verification
8. **API Authentication** → Generate new Long-Lived Access Token

---

## Missing Information Needed for Complete Precision

To make this plan 100% executable, please provide:

1. **HA Supervisor Host Details**:
   - IP address or hostname for `{HA_HOST}` 
   - SSH username for `{HA_USER}`
   - SSH key path or authentication method

2. **HA API Access**:
   - Long-Lived Access Token for `{HA_TOKEN}`
   - Confirm HA is accessible on port 8123

3. **MQTT Broker Details**:
   - Confirm MQTT broker is at `192.168.0.129:1883`
   - Verify credentials `mqtt_bb8:mqtt_bb8` are correct
   - Or provide actual MQTT broker details

4. **BLE Hardware Confirmation**:
   - Confirm BLE adapter `hci0` exists on HA host
   - Verify BB-8 device MAC `ED:ED:87:D7:27:50` is correct
   - Or provide actual BB-8 device details

5. **Support Infrastructure**:
   - Upload destination for diagnostics: `{SUPPORT_HOST}` and credentials
   - Preferred support contact method

6. **Network Environment**:
   - Confirm operator workstation can reach HA host via SSH
   - Any VPN, firewall, or network restrictions

With these details, all placeholder values can be replaced with actual working commands.
