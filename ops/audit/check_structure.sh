#!/usr/bin/env bash
set -Eeuo pipefail
WS="${WORKSPACE_ROOT:-__unset__}"
if [ "$WS" = "__unset__" ]; then echo "[fail] WORKSPACE_ROOT not set"; exit 2; fi
ADDON="${WS}/addon"
RUNTIME="/Volumes/addons/local/beep_boop_bb8"
REMOTE="git@github.com:e-app-404/ha-bb8-addon.git"
REPORTS="${WS}/reports"
OPS="${WS}/ops"
WRAP="${WS}/scripts"

fail=0
note(){ echo "$@"; }

[ -d "${ADDON}/.git" ] || { note "[fail] addon/ not a git repo"; fail=1; }
[ ! -L "${ADDON}" ] || { note "[fail] addon/ is a symlink"; fail=1; }

if [ -d "${RUNTIME}/.git" ]; then
  url="$(git -C "${RUNTIME}" remote get-url origin || true)"
  [ "$url" = "$REMOTE" ] || { note "[fail] runtime origin mismatch: $url"; fail=1; }
else
  note "[fail] runtime is not a git repo: ${RUNTIME}"; fail=1
fi

[ ! -d "${ADDON}/ops" ] || { note "[fail] addon/ops must not exist"; fail=1; }
[ -d "${OPS}" ] || { note "[fail] ops/ missing at WS root"; fail=1; }
if [ -d "${OPS}" ] && [ -z "$(ls -A "${OPS}")" ]; then
  note "[warn] ops/ exists but empty"
fi

if compgen -G "${WRAP}/run_*" > /dev/null || compgen -G "${WRAP}/*_wrapper.*" > /dev/null || [ -f "${WRAP}/verify_workspace.sh" ] || [ -f "${WRAP}/deploy_to_ha.sh" ]; then
  for f in "${WRAP}/"run_* "${WRAP}/"*"_wrapper."* "${WRAP}/verify_workspace.sh" "${WRAP}/deploy_to_ha.sh"; do
    [ -f "$f" ] || continue
    grep -q 'export REPORT_ROOT=' "$f" || { note "[fail] wrapper missing REPORT_ROOT export: $(basename "$f")"; fail=1; }
  done
fi

[ -d "${REPORTS}" ] || { note "[fail] reports/ missing"; fail=1; }
touch "${REPORTS}/.__writecheck" 2>/dev/null && rm -f "${REPORTS}/.__writecheck" || { note "[fail] reports/ not writable"; fail=1; }
[ ! -d "${WS}/bb8_core" ] || { note "[fail] WS-root bb8_core/ remains (must be removed)"; fail=1; }

if [ $fail -eq 0 ]; then
  echo "STRUCTURE_OK"
else
  exit 3
fi
