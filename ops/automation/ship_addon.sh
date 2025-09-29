#!/usr/bin/env bash
# ops/automation/ship_addon.sh
set -euo pipefail

CMD="${1:-publish}"
WS_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
ADDON_DIR="$WS_ROOT/addon"
REMOTE="${REMOTE:-git@github.com:e-app-404/ha-bb8-addon.git}"
BRANCH="${BRANCH:-main}"
RECEIPT="$WS_ROOT/reports/publish_receipt.txt"
mkdir -p "$WS_ROOT/reports"

# Guard: addon/ must not be a git repo; must contain config.yaml + Dockerfile (or image: for PUBLISH mode)
test -d "$ADDON_DIR" || { echo "DRIFT:addon_missing" >&2; exit 2; }
test ! -d "$ADDON_DIR/.git" || { echo "DRIFT:addon_nested_git" >&2; exit 3; }
test -f "$ADDON_DIR/config.yaml" || { echo "DRIFT:missing_config_yaml" >&2; exit 4; }

if ! grep -Eq '^[[:space:]]*image:[[:space:]]*' "$ADDON_DIR/config.yaml"; then
  test -f "$ADDON_DIR/Dockerfile" || { echo "DRIFT:dockerfile_missing_in_local_dev" >&2; exit 5; }
  echo "MODE: LOCAL_DEV"
else
  echo "MODE: PUBLISH"
fi

case "$CMD" in
  publish)
    TMP_BRANCH="__addon_pub_tmp_$(date +%s)"
    git subtree split -P addon -b "$TMP_BRANCH"
    git push -f "$REMOTE" "$TMP_BRANCH:refs/heads/$BRANCH"
    git branch -D "$TMP_BRANCH"
  echo "TOKEN: SUBTREE_PUBLISH_OK $(date -Iseconds) $REMOTE#$BRANCH" | tee -a "$RECEIPT"
    ;;
  *)
    echo "usage: $0 publish" >&2; exit 64;;
esac
