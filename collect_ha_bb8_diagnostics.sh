#!/bin/bash
# HA BB-8 Add-on Diagnostics Collection Script
# Usage: ./collect_ha_bb8_diagnostics.sh [HA_HOST] [HA_USER]

set -euo pipefail

# Configuration
HA_HOST="${1:-192.168.0.129}"
HA_USER="${2:-homeassistant}"
ADDON_SLUG="local_beep_boop_bb8"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DIAG_DIR="ha_bb8_diagnostics_${TIMESTAMP}"
ADDON_VERSION=$(grep '^version:' addon/config.yaml | awk '{print $2}' 2>/dev/null || echo "unknown")

echo "🔍 HA BB-8 Add-on Diagnostics Collection"
echo "Target: ${HA_USER}@${HA_HOST}"
echo "Add-on: ${ADDON_SLUG}"
echo "Version: ${ADDON_VERSION}"
echo "Output: ${DIAG_DIR}.tar.gz"
echo ""

# Create diagnostics directory
mkdir -p "${DIAG_DIR}"

# System information
echo "📋 Collecting system information..."
{
    echo "# HA BB-8 Diagnostics Report"
    echo "Generated: $(date -Iseconds)"
    echo "Host: ${HA_HOST}"
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
ssh "${HA_USER}@${HA_HOST}" "
    echo '## Home Assistant Supervisor Info' >> /tmp/ha_diag.txt
    ha info >> /tmp/ha_diag.txt 2>&1 || echo 'ha info failed' >> /tmp/ha_diag.txt
    echo '' >> /tmp/ha_diag.txt
    echo '## Add-on Status' >> /tmp/ha_diag.txt
    ha addons info ${ADDON_SLUG} >> /tmp/ha_diag.txt 2>&1 || echo 'addon info failed' >> /tmp/ha_diag.txt
    echo '' >> /tmp/ha_diag.txt
    echo '## System Info' >> /tmp/ha_diag.txt
    uname -a >> /tmp/ha_diag.txt 2>&1
    free -h >> /tmp/ha_diag.txt 2>&1
    df -h >> /tmp/ha_diag.txt 2>&1
    echo '' >> /tmp/ha_diag.txt
" 2>/dev/null || echo "⚠️  SSH connection failed"

scp "${HA_USER}@${HA_HOST}:/tmp/ha_diag.txt" "${DIAG_DIR}/ha_supervisor_info.txt" 2>/dev/null || echo "⚠️  Could not retrieve HA info"

# Container information
echo "🐳 Collecting container information..."
ssh "${HA_USER}@${HA_HOST}" "
    echo '## Docker Container Info' > /tmp/container_diag.txt
    docker ps -a --filter name=addon_${ADDON_SLUG} >> /tmp/container_diag.txt 2>&1 || echo 'docker ps failed' >> /tmp/container_diag.txt
    echo '' >> /tmp/container_diag.txt
    
    CONTAINER_ID=\$(docker ps --filter name=addon_${ADDON_SLUG} --format '{{.ID}}' | head -1)
    if [ -n \"\$CONTAINER_ID\" ]; then
        echo '## Container Inspect' >> /tmp/container_diag.txt
        docker inspect \$CONTAINER_ID >> /tmp/container_diag.txt 2>&1 || echo 'docker inspect failed' >> /tmp/container_diag.txt
        echo '' >> /tmp/container_diag.txt
        
        echo '## Container Environment' >> /tmp/container_diag.txt
        docker exec \$CONTAINER_ID env | grep -E 'MQTT|BB8|ADDON|DIAG|HEALTH' >> /tmp/container_diag.txt 2>&1 || echo 'env failed' >> /tmp/container_diag.txt
        echo '' >> /tmp/container_diag.txt
        
        echo '## Container File System' >> /tmp/container_diag.txt
        docker exec \$CONTAINER_ID ls -la /usr/src/app/ >> /tmp/container_diag.txt 2>&1 || echo 'ls failed' >> /tmp/container_diag.txt
        echo '' >> /tmp/container_diag.txt
        
        echo '## Heartbeat Files' >> /tmp/container_diag.txt
        docker exec \$CONTAINER_ID ls -la /tmp/bb8_heartbeat_* >> /tmp/container_diag.txt 2>&1 || echo 'no heartbeat files' >> /tmp/container_diag.txt
    else
        echo 'Container not running' >> /tmp/container_diag.txt
    fi
" 2>/dev/null || echo "⚠️  Container inspection failed"

scp "${HA_USER}@${HA_HOST}:/tmp/container_diag.txt" "${DIAG_DIR}/container_info.txt" 2>/dev/null || echo "⚠️  Could not retrieve container info"

# Add-on logs
echo "📝 Collecting add-on logs..."
ssh "${HA_USER}@${HA_HOST}" "ha addons logs ${ADDON_SLUG} > /tmp/addon_logs.txt 2>&1" 2>/dev/null || echo "⚠️  Could not retrieve logs"
scp "${HA_USER}@${HA_HOST}:/tmp/addon_logs.txt" "${DIAG_DIR}/addon_logs.txt" 2>/dev/null || echo "⚠️  Could not retrieve addon logs"

# Recent system logs (journalctl)
echo "📰 Collecting system logs..."
ssh "${HA_USER}@${HA_HOST}" "
    journalctl --since '1 hour ago' --no-pager > /tmp/system_logs.txt 2>&1 || echo 'journalctl failed' > /tmp/system_logs.txt
" 2>/dev/null || echo "⚠️  System logs failed"
scp "${HA_USER}@${HA_HOST}:/tmp/system_logs.txt" "${DIAG_DIR}/system_logs.txt" 2>/dev/null || echo "⚠️  Could not retrieve system logs"

# Configuration files
echo "⚙️  Collecting configuration files..."
cp addon/config.yaml "${DIAG_DIR}/addon_config.yaml" 2>/dev/null || echo "⚠️  Could not copy config.yaml"
ssh "${HA_USER}@${HA_HOST}" "cat /data/addons/${ADDON_SLUG}/options.json 2>/dev/null" > "${DIAG_DIR}/addon_options.json" 2>/dev/null || echo "{}" > "${DIAG_DIR}/addon_options.json"

# Network connectivity tests
echo "🌐 Testing network connectivity..."
{
    echo "## Network Connectivity Tests"
    echo "### MQTT Broker Test"
    if ssh "${HA_USER}@${HA_HOST}" "timeout 5 nc -zv 192.168.0.129 1883" 2>&1; then
        echo "✓ MQTT broker reachable"
    else
        echo "✗ MQTT broker unreachable"
    fi
    echo ""
    
    echo "### BLE Adapter Test"
    if ssh "${HA_USER}@${HA_HOST}" "hciconfig hci0" 2>&1; then
        echo "✓ BLE adapter accessible"
    else
        echo "✗ BLE adapter not accessible"
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
    echo "Host: ${HA_HOST}"
    echo "Bundle: ${DIAG_DIR}.tar.gz"
    echo ""
    echo "## Files:"
    find "${DIAG_DIR}" -type f -exec basename {} \; | sort
    echo ""
    echo "## File Sizes:"
    find "${DIAG_DIR}" -type f -exec ls -lh {} \; | awk '{print $9 ": " $5}'
} > "${DIAG_DIR}/MANIFEST.txt"

# Cleanup remote temp files
ssh "${HA_USER}@${HA_HOST}" "rm -f /tmp/ha_diag.txt /tmp/container_diag.txt /tmp/addon_logs.txt /tmp/system_logs.txt" 2>/dev/null || true

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