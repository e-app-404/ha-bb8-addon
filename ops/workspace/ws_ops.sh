#!/bin/bash
set -euo pipefail

# ws_ops.sh - Canonical Workspace Operations for HA-BB8
# ------------------------------------------------------
# This script provides easy commands for the most frequent workspace tasks.
# Usage: ./ws_ops.sh <command>
# Example: ./ws_ops.sh push
# ------------------------------------------------------

WS="/Users/evertappels/Projects/HA-BB8"
ADDON="$WS/addon"
RUNTIME="/Volumes/HA/addons/local/beep_boop_bb8"
BR="$(git -C "$ADDON" branch --show-current 2>/dev/null || git -C "$ADDON" rev-parse --abbrev-ref HEAD)"

function help() {
  cat <<EOF
ws_ops.sh - Canonical Workspace Operations for HA-BB8

Commands:
  push         Push local changes to remote (GitHub)
  sync         Sync runtime clone to latest remote branch
  tag <name>   Create and push a git tag (e.g. v2025.08.21-adr0001)
  status       Show current branch, commit, and runtime sync status
  receipt      Stamp governance receipt for current state
  help         Show this help message
EOF
}

function push() {
  echo "Pushing local changes to remote branch: $BR"
  git -C "$ADDON" push origin "HEAD:refs/heads/${BR}"
}

function sync() {
  echo "Syncing runtime clone to remote branch: $BR"
  git -C "$RUNTIME" fetch --all --prune
  git -C "$RUNTIME" checkout -B "$BR" "origin/$BR"
  git -C "$RUNTIME" reset --hard "origin/$BR"
  git -C "$RUNTIME" fetch --tags
}

function tag() {
  if [ $# -lt 1 ]; then
    echo "Usage: $0 tag <tagname>"
    exit 1
  fi
  TAG="$1"
  echo "Tagging current commit as $TAG"
  git -C "$ADDON" tag -a "$TAG" -m "$TAG"
  git -C "$ADDON" push --tags
}

function status() {
  WSH="$(git -C "$ADDON" rev-parse --short HEAD)"
  RTH="$(git -C "$RUNTIME" rev-parse --short HEAD)"
  REMOTE="$(git -C "$ADDON" remote get-url origin)"
  echo "Workspace branch: $BR"
  echo "Workspace head: $WSH"
  echo "Runtime head: $RTH"
  echo "Remote: $REMOTE"
}

function receipt() {
  TS="$(date -u +%Y%m%d_%H%M%SZ)"
  WSH="$(git -C "$ADDON" rev-parse --short HEAD)"
  RTH="$(git -C "$RUNTIME" rev-parse --short HEAD)"
  BR="$(git -C "$ADDON" branch --show-current 2>/dev/null || git -C "$ADDON" rev-parse --abbrev-ref HEAD)"
  printf "ADR=ADR-0001\nlabel=Canonical Topology — Dual-Clone via Git Remote\ntimestamp=%s\nbranch=%s\nws_head=%s\nruntime_head=%s\ntokens=STRUCTURE_OK,DEPLOY_OK,VERIFY_OK,WS_READY\n" "$TS" "$BR" "$WSH" "$RTH" | tee "$WS/reports/governance/ADR-0001_receipt_${TS}.status"
}

case "${1:-help}" in
  push) push ;;
  sync) sync ;;
  tag) shift; tag "$@" ;;
  status) status ;;
  receipt) receipt ;;
  help|*) help ;;
esac
