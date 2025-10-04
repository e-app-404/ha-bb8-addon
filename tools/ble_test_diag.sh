#!/bin/sh
# ═══════════════════════════════════════════════════════════════════════
# ▶ BB-8 Add-on STP1-9.BLE_TEST – S6/BLE Diagnostic Protocol ◀
# Version: 20250804-merged
# Logs to: /tmp/ble_test_diag_$(date +%Y%m%d_%H%M%S).log
# ═══════════════════════════════════════════════════════════════════════

LOG="/tmp/ble_test_diag_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

echo "==[ BB-8 Add-on S6/BLE DIAGNOSTIC START: $(date) ]=="
echo "LOGFILE: $LOG"
echo

echo "## 1. List S6, service, and envdir paths"
/bin/ls -l /app / /etc/services.d /etc/s6-overlay /etc/s6 /run/s6 2>/dev/null

echo
echo "## 2. Check /run/s6/container_environment"
/bin/ls -l /run/s6/container_environment 2>/dev/null || echo "[!] MISSING: /run/s6/container_environment"

echo
echo "## 3. Print S6 environment variables and overlay dirs"
env | grep S6 || echo "[!] No S6-related env vars found"
ls -l /run/s6 /etc/s6-overlay /etc/services.d 2>/dev/null

echo
echo "## 4. BLE Test script: existence and permissions"
ls -l /app/test_ble_adapter.py /test_ble_adapter.py 2>/dev/null || echo "[!] BLE test script not found"

echo
echo "## 5. Execute BLE test script (capture all output)"
if [ -x /app/test_ble_adapter.py ] || [ -f /app/test_ble_adapter.py ]; then
    python3 /app/test_ble_adapter.py 2>&1 || echo "[!] test_ble_adapter.py failed"
elif [ -x /test_ble_adapter.py ] || [ -f /test_ble_adapter.py ]; then
    python3 /test_ble_adapter.py 2>&1 || echo "[!] test_ble_adapter.py failed"
else
    echo "[!] test_ble_adapter.py missing in both /app and /"
fi

echo
echo "## 6. Display config.yaml (slug/name/folder check)"
cat /config.yaml 2>/dev/null || cat /app/config.yaml 2>/dev/null || echo "[!] config.yaml missing"

echo
echo "## 7. Dockerfile: s6-overlay install and entrypoint/cmd"
grep -i s6 Dockerfile || echo "[!] No s6-overlay reference in Dockerfile"
grep -i entrypoint Dockerfile || echo "[!] ENTRYPOINT not found in Dockerfile"
grep -i cmd Dockerfile || echo "[!] CMD not found in Dockerfile"

echo
echo "## 8. Last 40 lines of container log (if running under Docker)"
if command -v docker >/dev/null 2>&1; then
    container_id=$(cat /etc/hostname 2>/dev/null)
    if [ -n "$container_id" ]; then
        docker logs "$container_id" | tail -40 || echo "[!] Unable to fetch container logs"
    else
        echo "[!] Could not determine container ID from /etc/hostname"
    fi
else
    echo "[!] docker command not available in this environment"
    echo "# (If running manually, use: docker logs <addon-container> | tail -40)"
fi

echo
echo "==[ DIAGNOSTIC COMPLETE: $(date) ]=="
echo "See log at: $LOG"
