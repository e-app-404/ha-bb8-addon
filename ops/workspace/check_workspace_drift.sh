#!/usr/bin/env bash
# ops/check_workspace_drift.sh
# Validates ADR-0001 structure and detects drift between:
#  - workspace addon/ (source of truth)
#  - remote add-on repo (optional subtree check)
#  - HA runtime folder (optional, if mounted)
# Emits greppable TOKENS and a machine-readable JSON report.

set -Eeuo pipefail

WS_ROOT="${WS_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
ADDON_DIR="${ADDON_DIR:-$WS_ROOT/addon}"
RUNTIME_DIR="${RUNTIME_DIR:-/Volumes/addons/local/beep_boop_bb8}"  # adjust or leave missing
REPORTS="${REPORTS:-$WS_ROOT/reports}"
REMOTE_REPO="${REMOTE_REPO:-git@github.com:e-app-404/ha-bb8-addon.git}"
REMOTE_BRANCH="${REMOTE_BRANCH:-main}"

mkdir -p "$REPORTS"

token() { echo "TOKEN:$1"; }
fail()  { echo "DRIFT:$1"; }
info()  { echo "[info] $*"; }

json_escape() {
  echo "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))'
}

# ---------- 1) Structure checks (ADR-0001) ----------
STRUCT_OK=1
if [ ! -d "$ADDON_DIR" ]; then STRUCT_OK=0; fail "addon_missing"; fi
if [ -d "$ADDON_DIR/.git" ]; then STRUCT_OK=0; fail "addon_nested_git"; fi
DF="$ADDON_DIR/Dockerfile"
# forbidden workspace-only dirs inside addon subtree (always)
for d in .github docs ops reports addon; do
  if [ -e "$ADDON_DIR/$d" ]; then STRUCT_OK=0; fail "forbidden_in_addon:$d"; fi
done
# CRTP: tools/ and scripts/ are conditionally allowed
if [ -d "$ADDON_DIR/tools" ]; then
  if ! grep -Ei '\b(COPY|ADD|RUN|ENTRYPOINT|CMD)\b.*tools/' "$DF" >/dev/null 2>&1 \
     && [ ! -f "$ADDON_DIR/.allow_runtime_tools" ]; then
    STRUCT_OK=0; fail "tools_unreferenced_in_dockerfile"
  else
    token "TOOLS_ALLOWED"
  fi
fi
if [ -d "$ADDON_DIR/scripts" ]; then
  if ! grep -Ei '\b(COPY|ADD|RUN|ENTRYPOINT|CMD)\b.*scripts/' "$DF" >/dev/null 2>&1 \
     && [ ! -f "$ADDON_DIR/.allow_runtime_scripts" ]; then
    STRUCT_OK=0; fail "scripts_unreferenced_in_dockerfile"
  else
    token "SCRIPTS_ALLOWED"
  fi
fi
# required build context files

[ -f "$ADDON_DIR/config.yaml" ] || { STRUCT_OK=0; fail "missing_config_yaml"; }
if rg -n '^\s*image:\s*' "$ADDON_DIR/config.yaml" >/dev/null; then
  echo "MODE: PUBLISH"
  rg -n '^\s*version:\s*' "$ADDON_DIR/config.yaml" >/dev/null || { STRUCT_OK=0; fail "version_missing_in_publish_mode"; }
else
  echo "MODE: LOCAL_DEV"
  [ -f "$ADDON_DIR/Dockerfile" ] || { STRUCT_OK=0; fail "dockerfile_missing_in_local_dev"; }
  token "DEV_LOCAL_BUILD_FORCED"
fi

if [ $STRUCT_OK -eq 1 ]; then token "STRUCTURE_OK"; else token "STRUCTURE_DRIFT"; fi

# ---------- 2) Version drift (workspace vs runtime) ----------
WS_VER="$(sed -n 's/^version:[[:space:]]*\"\?\(.*\)\"*/\1/p' "$ADDON_DIR/config.yaml" | head -1 || true)"
RT_VER=""
if [ -f "$RUNTIME_DIR/config.yaml" ]; then
  RT_VER="$(sed -n 's/^version:[[:space:]]*\"\?\(.*\)\"*/\1/p' "$RUNTIME_DIR/config.yaml" | head -1 || true)"
fi

if [ -n "$RT_VER" ]; then
  if [ "$WS_VER" != "$RT_VER" ]; then
    fail "version_mismatch:workspace=$WS_VER runtime=$RT_VER"
  else
    token "VERSION_SYNC_OK:$WS_VER"
  fi
else
  info "Runtime config not found (skipping version sync check): $RUNTIME_DIR/config.yaml"
fi

# ---------- 3) Content drift (workspace addon/ vs runtime folder) ----------
CONTENT_DRIFT=""
if [ -d "$RUNTIME_DIR" ]; then
  # robust diff ignoring .pyc and __pycache__
  DIFF_OUT="$(diff -ruN --exclude='__pycache__' --exclude='*.pyc' "$ADDON_DIR" "$RUNTIME_DIR" || true)"
  if [ -n "$DIFF_OUT" ]; then
    CONTENT_DRIFT="yes"
    fail "runtime_content_drift_detected"
    echo "$DIFF_OUT" > "$REPORTS/runtime_diff.txt"
  else
    token "RUNTIME_SYNC_OK"
  fi
else
  info "Runtime dir not present or not mounted, skipping content diff: $RUNTIME_DIR"
fi

# ---------- 4) Subtree publish drift (optional) ----------
SUBTREE_SHA=""
REMOTE_SHA=""
SUBTREE_STATUS="skipped"

if git -C "$WS_ROOT" rev-parse HEAD >/dev/null 2>&1; then
  info "Computing subtree SHA for addon/"
  git -C "$WS_ROOT" subtree split -P addon -b __addon_pub_tmp > /dev/null 2>&1 || true
  if git -C "$WS_ROOT" rev-parse __addon_pub_tmp >/dev/null 2>&1; then
    SUBTREE_SHA="$(git -C "$WS_ROOT" rev-parse __addon_pub_tmp || true)"
    git -C "$WS_ROOT" ls-remote --heads "$REMOTE_REPO" "$REMOTE_BRANCH" > "$REPORTS/remote_heads.txt" 2>/dev/null || true
    REMOTE_SHA="$(awk '{print $1}' "$REPORTS/remote_heads.txt" | head -1)"
    if [ -n "$REMOTE_SHA" ] && [ -n "$SUBTREE_SHA" ] && [ "$REMOTE_SHA" = "$SUBTREE_SHA" ]; then
      token "SUBTREE_PUBLISH_OK:$REMOTE_BRANCH@$REMOTE_SHA"
      SUBTREE_STATUS="in_sync"
    else
      fail "subtree_publish_drift:local_subtree=$SUBTREE_SHA remote=$REMOTE_BRANCH@$REMOTE_SHA"
      SUBTREE_STATUS="drift"
    fi
    git -C "$WS_ROOT" branch -D __addon_pub_tmp >/dev/null 2>&1 || true
  fi
else
  info "Not in a Git workspace; skipping subtree check"
fi

# ---------- 5) JSON report ----------
REPORT_JSON="$REPORTS/workspace_drift_report.json"
python3 - "$REPORT_JSON" <<PY
import json, os, re, sys, hashlib, pathlib
ws_root = os.environ.get("WS_ROOT")
addon_dir = os.environ.get("ADDON_DIR")
runtime_dir = os.environ.get("RUNTIME_DIR")
reports = os.environ.get("REPORTS") or "."
ws_ver = os.environ.get("WS_VER", "")
rt_ver = os.environ.get("RT_VER", "")
subtree_status = os.environ.get("SUBTREE_STATUS", "skipped")
subtree_sha = os.environ.get("SUBTREE_SHA", "")
remote_sha = os.environ.get("REMOTE_SHA", "")
runtime_diff = pathlib.Path(reports) / "runtime_diff.txt"
out = {
    "contract": "workspace_drift_report_v1",
    "structure_ok": ${STRUCT_OK},
    "versions": {"workspace": ws_ver, "runtime": rt_ver or None},
    "runtime_diff_present": runtime_diff.exists(),
    "subtree": {"status": subtree_status, "local_subtree_sha": subtree_sha or None, "remote_head_sha": remote_sha or None},
    "paths": {"workspace": ws_root, "addon": addon_dir, "runtime": runtime_dir},
}
print(json.dumps(out, indent=2))
pathlib.Path(sys.argv[1]).write_text(json.dumps(out, indent=2))
PY

# ---------- 6) Exit code ----------
if grep -q '^DRIFT:' <(cat <<EOF
$(typeset -f)  # noop
EOF
); then true; fi # placeholder to keep heredoc quiet

# Evaluate drift presence
DRIFT_FOUND=0
if grep -q '^DRIFT:' "$REPORTS/workspace_drift_report.json" 2>/dev/null; then DRIFT_FOUND=1; fi
# Also infer drift from tokens/flags
if [ $STRUCT_OK -ne 1 ] || [ "$CONTENT_DRIFT" = "yes" ] || [ "$SUBTREE_STATUS" = "drift" ]; then
  DRIFT_FOUND=1
fi

if [ $DRIFT_FOUND -eq 1 ]; then
  token "WORKSPACE_DRIFT_FOUND"
  exit 3
else
  token "WORKSPACE_DRIFT_OK"
  exit 0
fi
