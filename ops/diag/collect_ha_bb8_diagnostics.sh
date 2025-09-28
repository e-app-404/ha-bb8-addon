#!/bin/bash
# HA BB-8 Add-on Diagnostics Collection Script (migrated to ops/diag)
# Usage:
#   ./collect_ha_bb8_diagnostics.sh <ssh_alias>
#   ./collect_ha_bb8_diagnostics.sh <HA_HOST> <HA_USER>

set -euo pipefail

# Input handling: accept either two args (host user) or single ssh alias
if [ "$#" -eq 2 ]; then
    HA_HOST="$1"
    HA_USER="$2"
    SSH_TARGET=""
elif [ "$#" -eq 1 ]; then
    SSH_TARGET="$1"
    HA_HOST=""
    HA_USER=""
else
    # defaults kept for backward compatibility when no args; still allow explicit ssh alias
    SSH_TARGET="hass"
    HA_HOST=""
    HA_USER=""
fi

ADDON_SLUG="local_beep_boop_bb8"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DIAG_DIR="ha_bb8_diagnostics_${TIMESTAMP}"
ADDON_VERSION=$(grep '^version:' addon/config.yaml | awk '{print $2}' 2>/dev/null || echo "unknown")

echo "🔍 HA BB-8 Add-on Diagnostics Collection"
if [ -n "${SSH_TARGET}" ]; then
    echo "Target SSH alias: ${SSH_TARGET}"
else
    echo "Target: ${HA_USER}@${HA_HOST}"
fi
echo "Add-on: ${ADDON_SLUG}"
echo "Version: ${ADDON_VERSION}"
echo "Output: ${DIAG_DIR}.tar.gz"
echo ""

# Create diagnostics directory
mkdir -p "${DIAG_DIR}"

# Helper wrappers to use either ssh alias or explicit host/user
remote_prefix()
{
    if [ -n "${SSH_TARGET}" ]; then
        printf "%s" "${SSH_TARGET}"
    else
        printf "%s@%s" "${HA_USER}" "${HA_HOST}"
    fi
}

remote_ssh()
{
    if [ -n "${SSH_TARGET}" ]; then
        ssh "${SSH_TARGET}" "$1"
    else
        ssh "${HA_USER}@${HA_HOST}" "$1"
    fi
}

# System information
echo "📋 Collecting system information..."
{
    echo "# HA BB-8 Diagnostics Report"
    echo "Generated: $(date -Iseconds)"
    echo "Host: ${HA_HOST:-<ssh_alias>}"
    echo "Add-on Version: ${ADDON_VERSION}"
    echo ""
} > "${DIAG_DIR}/diagnostics_summary.md"

# Local workspace info
echo "🏠 Collecting local workspace info..."
{
    echo "## Local Workspace"
    echo "Git commit: $(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
    echo "Git branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
    echo "Workspace VERSION: $(cat VERSION 2>/dev/null || echo 'unknown')"
    echo ""
} >> "${DIAG_DIR}/diagnostics_summary.md"

# HA Supervisor info
echo "🏠 Collecting HA Supervisor information..."
remote_ssh "echo '## Home Assistant Supervisor Info' >> /tmp/ha_diag.txt; sudo ha info >> /tmp/ha_diag.txt 2>&1 || echo 'ha info failed (try: sudo ha info)' >> /tmp/ha_diag.txt; echo '' >> /tmp/ha_diag.txt; echo '## Add-on Status' >> /tmp/ha_diag.txt; sudo ha addons info ${ADDON_SLUG} >> /tmp/ha_diag.txt 2>&1 || echo 'addon info failed (try: sudo ha addons info)' >> /tmp/ha_diag.txt; echo '' >> /tmp/ha_diag.txt; echo '## System Info' >> /tmp/ha_diag.txt; uname -a >> /tmp/ha_diag.txt 2>&1; free -h >> /tmp/ha_diag.txt 2>&1 || true; df -h >> /tmp/ha_diag.txt 2>&1 || true; echo '' >> /tmp/ha_diag.txt" 2>/dev/null || echo "⚠️  SSH connection failed"

REMOTE_PREFIX=$(remote_prefix)
scp "${REMOTE_PREFIX}:/tmp/ha_diag.txt" "${DIAG_DIR}/ha_supervisor_info.txt" 2>/dev/null || echo "⚠️  Could not retrieve HA info"

# Container information
echo "🐳 Collecting container information..."
remote_ssh "echo '## Docker Container Info' > /tmp/container_diag.txt; sudo /usr/local/bin/docker ps -a --filter name=addon_${ADDON_SLUG} >> /tmp/container_diag.txt 2>&1 || echo 'docker ps failed (try: sudo /usr/local/bin/docker ps)' >> /tmp/container_diag.txt; echo '' >> /tmp/container_diag.txt; CONTAINER_ID=\$(sudo /usr/local/bin/docker ps --filter name=addon_${ADDON_SLUG} --format '{{.ID}}' | head -1); if [ -n \"\$CONTAINER_ID\" ]; then echo '## Container Inspect' >> /tmp/container_diag.txt; sudo /usr/local/bin/docker inspect \$CONTAINER_ID >> /tmp/container_diag.txt 2>&1 || echo 'docker inspect failed' >> /tmp/container_diag.txt; echo '' >> /tmp/container_diag.txt; echo '## Container Environment' >> /tmp/container_diag.txt; sudo /usr/local/bin/docker exec \$CONTAINER_ID env | grep -E 'MQTT|BB8|ADDON|DIAG|HEALTH' >> /tmp/container_diag.txt 2>&1 || echo 'env failed' >> /tmp/container_diag.txt; echo '' >> /tmp/container_diag.txt; echo '## Container File System' >> /tmp/container_diag.txt; sudo /usr/local/bin/docker exec \$CONTAINER_ID ls -la /usr/src/app/ >> /tmp/container_diag.txt 2>&1 || echo 'ls failed' >> /tmp/container_diag.txt; echo '' >> /tmp/container_diag.txt; echo '## Heartbeat Files' >> /tmp/container_diag.txt; sudo /usr/local/bin/docker exec \$CONTAINER_ID ls -la /tmp/bb8_heartbeat_* >> /tmp/container_diag.txt 2>&1 || echo 'no heartbeat files' >> /tmp/container_diag.txt; else echo 'Container not running' >> /tmp/container_diag.txt; fi" 2>/dev/null || echo "⚠️  Container inspection failed"

scp "${REMOTE_PREFIX}:/tmp/container_diag.txt" "${DIAG_DIR}/container_info.txt" 2>/dev/null || echo "⚠️  Could not retrieve container info"

# Add-on logs
echo "📝 Collecting add-on logs..."
remote_ssh "sudo ha addons logs ${ADDON_SLUG} > /tmp/addon_logs.txt 2>&1 || echo 'ha addons logs failed (try: sudo ha addons logs)' > /tmp/addon_logs.txt" 2>/dev/null || echo "⚠️  Could not retrieve logs"
scp "${REMOTE_PREFIX}:/tmp/addon_logs.txt" "${DIAG_DIR}/addon_logs.txt" 2>/dev/null || echo "⚠️  Could not retrieve addon logs"

# Recent system logs (journalctl)
echo "📰 Collecting system logs..."
remote_ssh "sudo journalctl --since '1 hour ago' --no-pager > /tmp/system_logs.txt 2>&1 || echo 'journalctl failed (try: sudo journalctl)' > /tmp/system_logs.txt" 2>/dev/null || echo "⚠️  System logs failed"
scp "${REMOTE_PREFIX}:/tmp/system_logs.txt" "${DIAG_DIR}/system_logs.txt" 2>/dev/null || echo "⚠️  Could not retrieve system logs"

# Configuration files
echo "⚙️  Collecting configuration files..."
cp addon/config.yaml "${DIAG_DIR}/addon_config.yaml" 2>/dev/null || echo "⚠️  Could not copy config.yaml"
remote_ssh "cat /data/addons/${ADDON_SLUG}/options.json 2>/dev/null" > "${DIAG_DIR}/addon_options.json" 2>/dev/null || echo "{}" > "${DIAG_DIR}/addon_options.json"

# Network connectivity tests
echo "🌐 Testing network connectivity..."
{
    echo "## Network Connectivity Tests"
    echo "### MQTT Broker Test"
    if remote_ssh "timeout 5 nc -zv 192.168.0.129 1883" 2>&1; then
        echo "✓ MQTT broker reachable"
    else
        echo "✗ MQTT broker unreachable"
    fi
    echo ""

    echo "### BLE Adapter Test"
    if remote_ssh "hciconfig hci0" 2>&1; then
        echo "✓ BLE adapter accessible"
        remote_ssh "hciconfig hci0" 2>&1 | head -3
    else
        echo "✗ BLE adapter not accessible"
        echo "Checking Bluetooth service and tools..."
        remote_ssh "systemctl is-active bluetooth 2>/dev/null || echo 'bluetooth service not active'"
        remote_ssh "which hciconfig bluetoothctl 2>/dev/null || echo 'bluez tools missing: try sudo apt-get install bluez bluez-tools'"
        remote_ssh "ls -la /dev/hci* 2>/dev/null || echo 'no BLE adapters found in /dev/'"
    fi
    echo ""
} >> "${DIAG_DIR}/connectivity_tests.txt" 2>/dev/null || echo "⚠️  Connectivity tests failed"

# Validation script results
echo "✅ Running validation tests..."
if [ -f "ops/ADR/validate_cross_repo_links.sh" ]; then
    ./ops/ADR/validate_cross_repo_links.sh > "${DIAG_DIR}/validation_results.txt" 2>&1 || echo "Validation script failed" >> "${DIAG_DIR}/validation_results.txt"
fi

# Create manifest
echo "📦 Creating diagnostics manifest..."
{
    echo "# HA BB-8 Diagnostics Bundle Manifest"
    echo "Created: $(date -Iseconds)"
    echo "Host: ${HA_HOST:-<ssh_alias>}"
    echo "Bundle: ${DIAG_DIR}.tar.gz"
    echo ""
    echo "## Files:"
    find "${DIAG_DIR}" -type f -exec basename {} \; | sort
    echo ""
    echo "## File Sizes:"
    find "${DIAG_DIR}" -type f -exec ls -lh {} \; | awk '{print $9 ": " $5}'
} > "${DIAG_DIR}/MANIFEST.txt"

# Cleanup remote temp files
remote_ssh "rm -f /tmp/ha_diag.txt /tmp/container_diag.txt /tmp/addon_logs.txt /tmp/system_logs.txt" 2>/dev/null || true

# Create archive
echo "📦 Creating diagnostics archive..."
tar -czf "${DIAG_DIR}.tar.gz" "${DIAG_DIR}/"
rm -rf "${DIAG_DIR}/"

echo ""
echo "✅ Diagnostics collection complete!"
echo "📦 Archive: ${DIAG_DIR}.tar.gz"
echo "📊 Size: $(ls -lh ${DIAG_DIR}.tar.gz | awk '{print $5}')"
echo ""
echo "📤 Upload instructions:"
echo "   scp ${DIAG_DIR}.tar.gz support@{SUPPORT_HOST}:/uploads/"
echo "   curl -F 'file=@${DIAG_DIR}.tar.gz' https://support.example.com/upload"
echo ""

# Display quick summary
if [ -f "${DIAG_DIR}.tar.gz" ]; then
    echo "🔍 Quick Summary:"
    tar -tzf "${DIAG_DIR}.tar.gz" | head -10
    echo "   ... ($(tar -tzf "${DIAG_DIR}.tar.gz" | wc -l) total files)"
fi
