#!/bin/sh
# ═══════════════════════════════════════════════════════════════════════
# ▶ BB-8 Add-on STP1-9.BLE_TEST – S6/BLE Diagnostic Protocol ◀
# Version: 20250804 (POSIX)
# ═══════════════════════════════════════════════════════════════════════

LOG="/tmp/bb8_bletest_diag_$(date +%Y%m%d_%H%M%S).log"

echo "==[ BB-8 Add-on S6/BLE DIAGNOSTIC START: $(date) ]==" | tee -a "$LOG"
echo "LOGFILE: $LOG" | tee -a "$LOG"
echo | tee -a "$LOG"

echo "## 1. List S6, service, and envdir paths" | tee -a "$LOG"
/bin/ls -l /app / /etc/services.d /etc/s6-overlay /etc/s6 /run/s6 2>/dev/null | tee -a "$LOG"

echo | tee -a "$LOG"
echo "## 2. Check /run/s6/container_environment" | tee -a "$LOG"
/bin/ls -l /run/s6/container_environment 2>/dev/null | tee -a "$LOG" || echo "[!] MISSING: /run/s6/container_environment" | tee -a "$LOG"

echo | tee -a "$LOG"
echo "## 3. Print S6 environment variables and overlay dirs" | tee -a "$LOG"
env | grep S6 | tee -a "$LOG"
ls -l /run/s6 /etc/s6-overlay /etc/services.d 2>/dev/null | tee -a "$LOG"

echo | tee -a "$LOG"
echo "## 4. BLE Test script: existence and permissions" | tee -a "$LOG"
ls -l /app/test_ble_adapter.py /test_ble_adapter.py 2>/dev/null | tee -a "$LOG"

echo | tee -a "$LOG"
echo "## 5. Execute BLE test script (capture all output)" | tee -a "$LOG"
if [ -x /app/test_ble_adapter.py ] || [ -f /app/test_ble_adapter.py ]; then
    python3 /app/test_ble_adapter.py 2>&1 | tee -a "$LOG"
elif [ -x /test_ble_adapter.py ] || [ -f /test_ble_adapter.py ]; then
    python3 /test_ble_adapter.py 2>&1 | tee -a "$LOG"
else
    echo "[!] test_ble_adapter.py missing in both /app and /" | tee -a "$LOG"
fi

echo | tee -a "$LOG"
echo "## 6. Display config.yaml (slug/name/folder check)" | tee -a "$LOG"
cat /config.yaml 2>/dev/null | tee -a "$LOG" || cat /app/config.yaml 2>/dev/null | tee -a "$LOG" || echo "[!] config.yaml missing" | tee -a "$LOG"

echo | tee -a "$LOG"
echo "## 7. Dockerfile: s6-overlay install and entrypoint/cmd" | tee -a "$LOG"
grep -i s6 Dockerfile | tee -a "$LOG"
grep -i entrypoint Dockerfile | tee -a "$LOG"
grep -i cmd Dockerfile | tee -a "$LOG"

echo | tee -a "$LOG"
echo "## 8. Last 40 lines of container log (if running under Docker)" | tee -a "$LOG"
if command -v docker >/dev/null 2>&1; then
    container_id=$(cat /etc/hostname 2>/dev/null)
    docker logs "$container_id" | tail -40 | tee -a "$LOG" || echo "[!] Unable to fetch container logs" | tee -a "$LOG"
else
    echo "[!] docker command not available in this environment" | tee -a "$LOG"
fi

echo | tee -a "$LOG"
echo "==[ DIAGNOSTIC COMPLETE: $(date) ]==" | tee -a "$LOG"
echo "See log at: $LOG" | tee -a "$LOG"
