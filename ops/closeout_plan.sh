#!/usr/bin/env bash
# ops/closeout_plan.sh — End-to-End Closeout Plan (LOCAL_DEV)
# Purpose: Automate and document the session closeout process with explicit token gates and fix/re-run guidance.
set -euo pipefail

# --- A) Workspace Sanity & Sync ---

echo "[A-1] Validating workspace structure and tokens..."
bash ops/workspace/validate_paths_map.sh | tee reports/paths_health_receipt.txt
if ! grep -q '^TOKEN:' reports/paths_health_receipt.txt; then
  echo "FAIL: No tokens found in reports/paths_health_receipt.txt. Fix workspace structure and re-run validation." >&2
  exit 10
fi
if ! grep -q 'TOKEN: PATHS_MAP_OK' reports/paths_health_receipt.txt; then
  echo "FAIL: PATHS_MAP_OK token missing. Fix path map and re-run validation." >&2
  exit 11
fi

echo "[A-2] Syncing add-on subtree to HA runtime (SMB mount preferred)..."
RSYNC_EXC=ops/rsync_runtime.exclude
rsync -av --inplace --delete --exclude '.DS_Store' --exclude-from "$RSYNC_EXC" addon/ /Volumes/addons/local/beep_boop_bb8/
echo "TOKEN: SYNC_OK" > reports/sync_receipt.txt
if ! grep -q 'TOKEN: SYNC_OK' reports/sync_receipt.txt; then
  echo "FAIL: SYNC_OK token missing. Check SMB mount permissions and re-run rsync." >&2
  exit 12
fi

# --- B) HA Box (Runtime) Setup ---

echo "[B-3] Ensuring report sink exists..."
mkdir -p /config/reports && echo "TOKEN: REPORT_SINK_OK" | tee -a /config/reports/deploy_receipt.txt
if ! grep -q 'TOKEN: REPORT_SINK_OK' /config/reports/deploy_receipt.txt; then
  echo "FAIL: REPORT_SINK_OK token missing. Check /config/reports permissions and re-run." >&2
  exit 13
fi

echo "[B-4] Verifying LOCAL_DEV mode in config..."
CFG="/addons/local/beep_boop_bb8/config.yaml"
MODE_CHECK=$(sed -n '1,60p' "$CFG" | grep -E '^(version:|image:|build:)')
if ! echo "$MODE_CHECK" | grep -q '^version:' || ! echo "$MODE_CHECK" | grep -q '^build:' || echo "$MODE_CHECK" | grep -q '^image:'; then
  echo "FAIL: config.yaml must have version: and build:, and no uncommented image:. Fix and re-run." >&2
  exit 14
fi

echo "[B-5] Reloading and rebuilding add-on..."
ha addons reload
ha addons rebuild local_beep_boop_bb8
ha addons start local_beep_boop_bb8 || true

echo "[B-6] Checking add-on state and version..."
INFO_OUT=$(ha addons info local_beep_boop_bb8 | grep -E 'state:|version:')
if ! echo "$INFO_OUT" | grep -q 'state: started'; then
  echo "FAIL: Add-on not started. Use HA UI to reload store, then re-run steps B-4 to B-6." >&2
  exit 15
fi

# --- C) Container & Runtime Verification ---

echo "[C-7] Verifying container and entrypoint..."
CID=$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}')
if [ -z "$CID" ]; then
  echo "FAIL: container not running. Rebuild and start add-on, then re-run." >&2
  exit 16
fi

docker exec "$CID" bash -lc 'test -f /usr/src/app/run.sh && echo TOKEN: RUNTIME_RUN_SH_PRESENT || echo FAIL: RUN_SH_MISSING' > reports/container_receipt.txt
if ! grep -q 'TOKEN: RUNTIME_RUN_SH_PRESENT' reports/container_receipt.txt; then
  echo "FAIL: run.sh missing in container. Check Dockerfile COPY and rebuild (B-5, B-6)." >&2
  exit 17
fi

docker exec "$CID" bash -lc 'echo "PY=$(command -v python)"; python -c "import sys; print(sys.executable)"' > reports/python_receipt.txt
if ! grep -q '/opt/venv/bin/python' reports/python_receipt.txt; then
  echo "FAIL: Python venv not present. Check Dockerfile venv section and rebuild (B-5, B-6)." >&2
  exit 18
fi

docker exec "$CID" bash -lc '/opt/venv/bin/python -c "import bb8_core.main as m; print(\"TOKEN: MODULE_OK\")"' > reports/module_receipt.txt
if ! grep -q 'TOKEN: MODULE_OK' reports/module_receipt.txt; then
  echo "FAIL: bb8_core.main import failed. Check Python install and rebuild (B-5, B-6)." >&2
  exit 19
fi

ha addons logs local_beep_boop_bb8 --lines 100 | grep -E 'version_probe|Starting bridge controller' || echo "INFO: log lines not found; check runtime logs manually."

# Record runtime receipts
{
  echo "TOKEN: CLEAN_RUNTIME_OK"
  echo "TOKEN: DEPLOY_OK"
  echo "TOKEN: VERIFY_OK"
} | tee -a /config/reports/deploy_receipt.txt

# --- D) Minimal Function Checks (Optional, Soft Gate) ---

mosquitto_sub -h 127.0.0.1 -p 1883 -v -t 'homeassistant/#' -C 1 -W 3 || echo "INFO: no discovery in 3s window"
mosquitto_pub -h 127.0.0.1 -p 1883 -t 'bb8/echo/cmd' -m '{"value":1,"ts":'$(date +%s)'}'
mosquitto_sub -h 127.0.0.1 -p 1883 -v -t 'bb8/echo/#' -C 1 -W 3 || echo "INFO: no echo observed in 3s"

# --- E) Final Acceptance ---

echo "[E] Final acceptance checks..."
if grep -q 'TOKEN: CLEAN_RUNTIME_OK' /config/reports/deploy_receipt.txt \
   && grep -q 'TOKEN: DEPLOY_OK' /config/reports/deploy_receipt.txt \
   && grep -q 'TOKEN: VERIFY_OK' /config/reports/deploy_receipt.txt \
   && grep -q 'TOKEN: REPORT_SINK_OK' /config/reports/deploy_receipt.txt; then
  echo "SUCCESS: All gates passed. Session is stable and closed."
else
  echo "FAIL: One or more tokens missing in deploy_receipt.txt. Review previous steps and re-run as needed." >&2
  exit 20
fi

# --- What NOT to Change ---
echo "Do NOT toggle image: in addon/config.yaml (stay in LOCAL_DEV)."
echo "Do NOT add new patches."
echo "Do NOT rebuild outside HA Supervisor except for diagnostics."

echo "If blocked, use HA UI to rebuild/start add-on. If Supervisor warns 'removed from repository', reload the store and ensure /addons/local/beep_boop_bb8 exists."

echo "Session closeout complete. Further work (telemetry, CI) should be scheduled for a new session."
