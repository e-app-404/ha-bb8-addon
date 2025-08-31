#!/usr/bin/env bash
# Toggle addon/config.yaml between LOCAL_DEV (no image) and PUBLISH (image present).
set -euo pipefail
CFG="addon/config.yaml"
MODE="${1:-}"
if [ ! -f "$CFG" ]; then echo "missing $CFG"; exit 2; fi

if [ "$MODE" = "local" ]; then
  # comment out image
  sed -i.bak -E 's/^(\s*)image:(.*)$/\1# image:\2/' "$CFG"
  echo "MODE: LOCAL_DEV → image commented"
elif [ "$MODE" = "publish" ]; then
  IMG="${2:-ghcr.io/your-org/ha-bb8-{arch}}"
  if rg -n '^\s*image:\s*' "$CFG" >/dev/null; then
    sed -i.bak -E "s#^(\s*)#?image:.*#\1image: "$IMG"#" "$CFG" || true
  else
    printf '\nimage: "%s"\n' "$IMG" >> "$CFG"
  fi
  echo "MODE: PUBLISH → image set to $IMG"
else
  echo "usage: $0 <local|publish> [image]"
  exit 1
fi
