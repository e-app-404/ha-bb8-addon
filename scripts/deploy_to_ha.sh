#!/usr/bin/env bash
set -euo pipefail
WS="/Users/evertappels/Projects/HA-BB8"
RUNTIME="/Volumes/addons/local/beep_boop_bb8"

# 1) Push workspace addon (submodule) to remote
cd "$WS/addon"
git rev-parse --is-inside-work-tree >/dev/null
BR=$(git rev-parse --abbrev-ref HEAD)
git push origin "$BR"

# 2) Pull/reset runtime to that branch
cd "$RUNTIME"
git fetch --all
git reset --hard "origin/$BR"
echo "[deploy] runtime now at $(git rev-parse --short HEAD) on $BR"
