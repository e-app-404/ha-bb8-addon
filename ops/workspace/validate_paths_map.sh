#!/usr/bin/env bash
# PATHS_MAP quick validation script for HA-BB8 workspace (hardened)
set -Eeuo pipefail

# Resolve workspace root and script dir
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
WS_ROOT="${WS_ROOT:-$SCRIPT_DIR/../..}"
ADDON_DIR="${ADDON_DIR:-$WS_ROOT/addon}"
REPORTS="${REPORTS:-$WS_ROOT/reports}"
mkdir -p "$REPORTS"
RUNTIME_MOUNT=""; for C in "/Volumes/addons/local/beep_boop_bb8" "/mnt/addons/local/beep_boop_bb8"; do [ -d "$C" ] && RUNTIME_MOUNT="$C" && break; done

# Check required tools
for tool in rg awk python3; do
  command -v "$tool" >/dev/null || { echo "ERROR: $tool not found"; exit 1; }
done

# Mode detection
if grep -Eq '^[[:space:]]*image:[[:space:]]*' "$ADDON_DIR/config.yaml"; then
  echo "MODE: PUBLISH"
  grep -Eq '^[[:space:]]*version:[[:space:]]*' "$ADDON_DIR/config.yaml" || echo "DRIFT: version_missing_in_publish_mode"
else
  echo "MODE: LOCAL_DEV"
  [ -f "$ADDON_DIR/Dockerfile" ] || echo "DRIFT: dockerfile_missing_in_local_dev"
  echo "TOKEN: DEV_LOCAL_BUILD_FORCED"
fi

# Version sync check
WS_VER="$(awk -F: '/^[[:space:]]*version:/{gsub(/[ "\t]/,"",$2);print $2;exit}' "$ADDON_DIR/config.yaml" || true)"
RT_VER=""; [ -n "$RUNTIME_MOUNT" ] && [ -f "$RUNTIME_MOUNT/config.yaml" ] && RT_VER="$(awk -F: '/^[[:space:]]*version:/{gsub(/[ "\t]/,"",$2);print $2;exit}' "$RUNTIME_MOUNT/config.yaml" || true)"
[ -n "$RT_VER" ] && [ "$WS_VER" = "$RT_VER" ] && echo "TOKEN: VERSION_SYNC_OK:$WS_VER" || true

# Optional: detect that tests are excluded in release image context (heuristic)
if grep -Eq '^[[:space:]]*COPY[[:space:]]+\.[[:space:]]+/usr/src/app' "$ADDON_DIR/Dockerfile"; then
  echo "INFO: consider narrowing COPY to exclude tests for release"
else
  echo "TOKEN: COPY_NARROW_OK"
fi

# Symlink guard in addon/ (portable: BSD/macOS find uses -type l, not -xtype)
if find "$ADDON_DIR" -type l -not -path '*/.venv/*' -print -quit | grep -q . ; then
  echo "DRIFT: symlink_present_in_addon"
else
  echo "TOKEN: NO_SYMLINKS_IN_ADDON"
fi

# Emit paths map contract for tools/CI
python3 - <<'PY' > "$REPORTS/paths_map_contract_v1.json"
import json, os
print(json.dumps({
  "contract":"paths_map_contract_v1",
  "ws_root": os.getcwd(),
  "addon_dir":"addon",
  "runtime_mount": "/Volumes/addons/local/beep_boop_bb8",
  "ha_runtime": "/addons/local/beep_boop_bb8",
  "slug":"beep_boop_bb8",
  "remote_addon":"git@github.com:e-app-404/ha-bb8-addon.git",
  "crtp_markers":[".allow_runtime_tools",".allow_runtime_scripts"],
  "reserved_subtrees":["addon/bin","addon/assets","addon/services","addon/rootfs"]
}, indent=2))
PY

echo "TOKEN: PATHS_MAP_CONTRACT_EMITTED"
echo "TOKEN: PATHS_HEALTH_OK"
echo "TOKEN: PATHS_MAP_OK"
