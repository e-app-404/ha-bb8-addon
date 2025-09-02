
#!/usr/bin/env bash
# Validates PATHS_MAP invariants + emits a contract JSON. (hardened)
set -Eeuo pipefail

# Resolve workspace root and script dir
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
WS_ROOT="${WS_ROOT:-$SCRIPT_DIR/../..}"
ADDON_DIR="${ADDON_DIR:-$WS_ROOT/addon}"
RUNTIME_MOUNT="${RUNTIME_MOUNT:-/Volumes/addons/local/beep_boop_bb8}"
[ -d "$RUNTIME_MOUNT" ] || RUNTIME_MOUNT="/mnt/addons/local/beep_boop_bb8"
[ -d "$RUNTIME_MOUNT" ] || RUNTIME_MOUNT=""
HA_RUNTIME="${HA_RUNTIME:-/addons/local/beep_boop_bb8}"
ADDON_SLUG="${ADDON_SLUG:-beep_boop_bb8}"
REMOTE_ADDON="${REMOTE_ADDON:-git@github.com:e-app-404/ha-bb8-addon.git}"
REPORTS="${REPORTS:-$WS_ROOT/reports}"
mkdir -p "$REPORTS"

# Check required tools
for tool in rg awk python3; do
  command -v "$tool" >/dev/null || { echo "ERROR: $tool not found"; exit 1; }
done

DRIFT=0
say(){ echo "$@"; }
tok(){ echo "TOKEN: $1"; }

# S1 structure: addon exists, no nested .git
[ -d "$ADDON_DIR" ] || { say "DRIFT:addon_missing:$ADDON_DIR"; DRIFT=1; }
[ -d "$ADDON_DIR/.git" ] && { say "DRIFT:addon_nested_git"; DRIFT=1; }

# S2 forbidden dirs
for d in .github docs ops reports addon; do
  [ -e "$ADDON_DIR/$d" ] && { say "DRIFT:forbidden_in_addon:$d"; DRIFT=1; }
done

# S3 buildability

[ -f "$ADDON_DIR/config.yaml" ] || { say "DRIFT:missing_config_yaml"; DRIFT=1; }
if rg -n '^\s*image:\s*' "$ADDON_DIR/config.yaml" >/dev/null; then
  say "MODE: PUBLISH"
  rg -n '^\s*version:\s*' "$ADDON_DIR/config.yaml" >/dev/null || { say "DRIFT:version_missing_in_publish_mode"; DRIFT=1; }
else
  say "MODE: LOCAL_DEV"
  [ -f "$ADDON_DIR/Dockerfile" ] || { say "DRIFT:dockerfile_missing_in_local_dev"; DRIFT=1; }
  tok "DEV_LOCAL_BUILD_FORCED"
fi

# S4 symlink guard (portable: BSD/macOS find uses -type l, not -xtype)
if find "$ADDON_DIR" -type l -not -path '*/.venv/*' -print -quit | grep -q .; then
  say "DRIFT:symlink_present_in_addon"
  DRIFT=1
else
  tok "NO_SYMLINKS_IN_ADDON"
fi

# CRTP (tools/scripts) + reserved subtrees tokens
DF="$ADDON_DIR/Dockerfile"
crtp_ok() {
  local path="$1" marker="$2" key="$3"
  if [ -d "$path" ]; then
    if grep -Ei '(COPY|ADD|RUN|ENTRYPOINT|CMD).*'"$(basename "$path")"'/?' "$DF" >/dev/null 2>&1 || [ -f "$marker" ]; then
      tok "${key}_ALLOWED"
    else
      say "DRIFT:${key,,}_unreferenced_in_dockerfile"
      DRIFT=1
    fi
  fi
}
crtp_ok "$ADDON_DIR/tools"    "$ADDON_DIR/.allow_runtime_tools"    "TOOLS"
crtp_ok "$ADDON_DIR/scripts"  "$ADDON_DIR/.allow_runtime_scripts"  "SCRIPTS"

# Reserved (optional): bin, assets, services, rootfs → tokens on pass if present
reserve_ok() {
  local sub="$1" key="$2"
  [ -d "$ADDON_DIR/$sub" ] || return 0
  if [ "$sub" = "rootfs" ]; then
    grep -Eq '\bCOPY\b\s+rootfs/\s+/' "$DF" >/dev/null 2>&1 || { say "DRIFT:rootfs_unreferenced_in_dockerfile"; DRIFT=1; return 0; }
    tok "ROOTFS_ALLOWED"
  else
    if grep -Ei '(COPY|ADD|RUN|ENTRYPOINT|CMD).*'"$sub"'/?' "$DF" >/dev/null 2>&1; then
      tok "${key}_ALLOWED"
    else
      say "DRIFT:${key,,}_unreferenced_in_dockerfile"
      DRIFT=1
    fi
  fi
}
reserve_ok "bin"      "BIN"
reserve_ok "assets"   "ASSETS"
reserve_ok "services" "SERVICES"
reserve_ok "rootfs"   "ROOTFS"

# Optional runtime diff (skip if mount absent)
if [ -d "$RUNTIME_MOUNT" ]; then
  if diff -ruN --exclude='__pycache__' --exclude='*.pyc' "$ADDON_DIR" "$RUNTIME_MOUNT" >"$REPORTS/runtime_diff.txt" 2>/dev/null; then
    tok "RUNTIME_SYNC_OK"
  else
    say "DRIFT:runtime_content_drift_detected"
  fi
fi

# Emit contract JSON
python3 - "$REPORTS/paths_map_contract_v1.json" <<PY
import json, os, sys, pathlib
out = {
  "contract":"paths_map_contract_v1",
  "ws_root": os.environ.get("WS_ROOT"),
  "addon_dir": os.environ.get("ADDON_DIR"),
  "runtime_mount": os.environ.get("RUNTIME_MOUNT"),
  "ha_runtime": os.environ.get("HA_RUNTIME"),
  "slug": os.environ.get("ADDON_SLUG"),
  "remote_addon": os.environ.get("REMOTE_ADDON"),
  "crtp_markers": [".allow_runtime_tools",".allow_runtime_scripts"],
  "reserved_subtrees": ["addon/bin","addon/assets","addon/services","addon/rootfs"]
}
pathlib.Path(sys.argv[1]).write_text(json.dumps(out, indent=2))
PY
tok "PATHS_MAP_CONTRACT_EMITTED"


# Base image detector (Dockerfile parsing)
if rg -q 'ARG BUILD_FROM=.*-base-debian' "$ADDON_DIR/Dockerfile"; then
  tok "BASE=debian"
elif rg -q 'ARG BUILD_FROM=.*-base-alpine' "$ADDON_DIR/Dockerfile"; then
  tok "BASE=alpine"
else
  echo "DRIFT: base_image_unknown"
fi

# Final token / exit
if [ "$DRIFT" -eq 0 ]; then
  tok "PATHS_HEALTH_OK"
  exit 0
else
  exit 3
fi
