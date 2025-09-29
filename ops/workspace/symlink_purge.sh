#!/usr/bin/env bash
set -Eeuo pipefail

WS="/Users/evertappels/Projects/HA-BB8"
ADDON="$WS/addon"
RUNTIME="/Volumes/HA/addons/local/beep_boop_bb8"
REMOTE="git@github.com:e-app-404/ha-bb8-addon.git"

git -C "$ADDON" remote set-url origin "$REMOTE" || true
git -C "$ADDON" fetch origin --prune || true
BR="$(git -C "$ADDON" branch --show-current 2>/dev/null || true)"
if [ -z "$BR" ] || [ "$BR" = "HEAD" ]; then
  BR="$(git -C "$ADDON" ls-remote --symref origin HEAD | awk '/^ref:/ {sub("refs/heads/","",$2); print $2; exit}')"
  [ -z "$BR" ] && BR="main"
fi


SYMLINKS_PURGED=0
find "$WS" -maxdepth 3 -type l -print 2>/dev/null | awk '!/(\/python($|3($|\.13$)))/' | while IFS= read -r p; do
  case "$p" in
    "$ADDON"/*)
      rel="${p#$ADDON/}"
      if git -C "$ADDON" ls-files --error-unmatch "$rel" >/dev/null 2>&1; then
        git -C "$ADDON" rm -q "$rel" || rm -f "$p"
        git -C "$ADDON" commit -m "cleanup: remove non-python symlink $rel" || true
      else
        rm -f "$p"
      fi
      ;;
    *)
      rm -f "$p"
      ;;
  esac
  SYMLINKS_PURGED=$((SYMLINKS_PURGED+1))
done
GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND='ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15' git -C "$ADDON" push origin "HEAD:refs/heads/${BR}" || true
git -C "$RUNTIME" fetch --all --prune
git -C "$RUNTIME" checkout -B "$BR" "origin/$BR"
git -C "$RUNTIME" reset --hard "origin/$BR"
echo "SYMLINKS_PURGED=$SYMLINKS_PURGED"
