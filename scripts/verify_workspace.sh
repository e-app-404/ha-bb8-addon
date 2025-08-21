#!/usr/bin/env bash
set -euo pipefail
WS="/Users/evertappels/Projects/HA-BB8"
RUNTIME="/Volumes/addons/local/beep_boop_bb8"

echo "workspace addon is git clone?"; git -C "$WS/addon" rev-parse --is-inside-work-tree
echo "runtime addon is git clone?";   git -C "$RUNTIME"  rev-parse --is-inside-work-tree

echo "workspace HEAD: $(git -C "$WS/addon" rev-parse --short HEAD)"
echo "runtime   HEAD: $(git -C "$RUNTIME"  rev-parse --short HEAD)"

echo "remote (workspace): $(git -C "$WS/addon" remote get-url origin)"
echo "remote (runtime)  : $(git -C "$RUNTIME"  remote get-url origin)"
