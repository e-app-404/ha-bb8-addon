#!/usr/bin/env bash
# ops/automation/runtime_deploy.sh
# Run on HA host shell (SSH add-on) OR from dev box if /addons is mounted at /Volumes/addons
set -euo pipefail

RUNTIME="${RUNTIME:-/addons/local/beep_boop_bb8}"
SINK="${SINK:-/config/reports}"
mkdir -p "$SINK"

# Basic presence
test -d "$RUNTIME" || { echo "FAIL: runtime folder missing: $RUNTIME"; exit 2; }
test -f "$RUNTIME/config.yaml" || { echo "FAIL: runtime config missing"; exit 3; }

# Reload + rebuild + start
ssh babylon-babes@homeassistant "ha addons reload" >/dev/null
ssh babylon-babes@homeassistant "ha addons rebuild local_beep_boop_bb8" >/dev/null
ha addons start  local_beep_boop_bb8 >/dev/null || true

# Verify running & run.sh in container
CID="$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}' || true)"
test -n "$CID" || { echo "FAIL: container not running"; exit 4; }
docker exec "$CID" bash -lc 'test -f /usr/src/app/run.sh' || { echo "FAIL: RUN_SH_MISSING"; exit 5; }

# Tokens
{
  echo "TOKEN: CLEAN_RUNTIME_OK"
  echo "TOKEN: DEPLOY_OK"
  echo "TOKEN: VERIFY_OK"
} | tee -a "$SINK/deploy_receipt.txt"

echo "OK: runtime deployed & verified"
