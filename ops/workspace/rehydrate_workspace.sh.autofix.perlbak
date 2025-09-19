#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "[ERR] line:$LINENO cmd:$BASH_COMMAND" >&2' ERR
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -o BatchMode=yes}"
export GIT_TERMINAL_PROMPT=0

WS="/Users/evertappels/Projects/HA-BB8"
ADDON="${WS}/addon"
RUNTIME="/Volumes/HA/addons/local/beep_boop_bb8"
REMOTE="git@github.com:e-app-404/ha-bb8-addon.git"
WRAP="${WS}/scripts"
OPS="${WS}/ops"
REPORTS="${WS}/reports"
DOCS="${WS}/docs"
BK="${WS}/_backup_$(date -u +%Y%m%d_%H%M%S)Z"

# ---------- P0: Preflight & safety snapshot ----------
echo "[info] WS=${WS}"
echo "[info] ADDON=${ADDON}"
echo "[info] RUNTIME=${RUNTIME}"
echo "[info] REMOTE=${REMOTE}"
echo "[info] BACKUP_DIR=${BK}"

mkdir -p "${BK}"
( cd "${WS}" && ls -la > "${BK}/_ws_listing.txt" )
if [ -d "${WS}/.git" ]; then
  mv "${WS}/.git" "${BK}/_ws_git_backup"
  echo "[preflight] archived WS/.git -> ${BK}/_ws_git_backup"
fi

mkdir -p "${REPORTS}"
touch "${REPORTS}/.writetest" && rm -f "${REPORTS}/.writetest" || { echo "[fail] reports not writable: ${REPORTS}"; exit 10; }

# ---------- P1: addon/ as a clean git clone ----------
if [ -e "${ADDON}" ] && [ ! -d "${ADDON}/.git" ]; then
  mv "${ADDON}" "${BK}/addon_non_git_$(date +%H%M%S)"
  echo "[p1] archived non-git addon/ -> ${BK}"
fi
if [ ! -d "${ADDON}/.git" ]; then
  git clone --origin origin "${REMOTE}" "${ADDON}"
  echo "[p1] cloned ${REMOTE} -> addon/"
else
  ( cd "${ADDON}" && git remote set-url origin "${REMOTE}" && git fetch --all --prune )
  echo "[p1] normalized existing addon/ git remote & fetched"
fi
test ! -L "${ADDON}" || { echo "[fail] addon/ is a symlink (forbidden)"; exit 11; }
if git -C "${WS}" rev-parse 2>/dev/null 1>/dev/null; then
  if git -C "${WS}" ls-files --stage -- addon 2>/dev/null | grep -q " 160000 "; then
    echo "[fail] addon/ registered as submodule in WS repo (forbidden)"; exit 12
  fi
fi

# ---------- P2: runtime clone (HA mount) ----------
if [ -d "${RUNTIME}/.git" ]; then
  git -C "${RUNTIME}" remote set-url origin "${REMOTE}"
  git -C "${RUNTIME}" fetch --all --prune
  echo "[p2] normalized runtime git remote & fetched"
else
  if [ -e "${RUNTIME}" ] && [ ! -d "${RUNTIME}/.git" ]; then
    mv "${RUNTIME}" "${BK}/runtime_non_git_$(date +%H%M%S)"
    echo "[p2] archived non-git runtime dir -> ${BK}"
  fi
  mkdir -p "$(dirname "${RUNTIME}")"
  git clone --origin origin "${REMOTE}" "${RUNTIME}"
  echo "[p2] cloned ${REMOTE} -> runtime"
fi
test ! -L "${RUNTIME}" || { echo "[fail] runtime path is a symlink (forbidden)"; exit 13; }

# ---------- P3: bb8_core consolidation (skip if no sources) ----------
if [ -d "${WS}/bb8_core" ]; then
  if find "${WS}/bb8_core" -type f -name '*.py' | grep -q . ; then
    mkdir -p "${ADDON}/bb8_core"
    rsync -a --ignore-existing --include='*.py' --exclude='*' "${WS}/bb8_core/" "${ADDON}/bb8_core/"
    echo "[p3] merged WS/bb8_core/*.py -> addon/bb8_core/"
  else
    echo "[p3] no source .py files in WS/bb8_core (compiled/empty); skipping merge per ADR"
  fi
  mv "${WS}/bb8_core" "${BK}/bb8_core_ws_$(date +%H%M%S)"
  echo "[p3] archived and removed WS/bb8_core -> ${BK}"
fi

# ---------- P4: ops/ consolidation ----------
mkdir -p "${OPS}"
if [ -d "${WS}/tools" ]; then
  shopt -s dotglob nullglob
  for f in "${WS}/tools"/*; do
    mv "$f" "${OPS}/"
  done
  rmdir "${WS}/tools" 2>/dev/null || true
  echo "[p4] moved tools/* -> ops/"
fi
if [ -d "${ADDON}/ops" ]; then
  shopt -s dotglob nullglob
  for f in "${ADDON}/ops"/*; do
    mv "$f" "${OPS}/"
  done
  rmdir "${ADDON}/ops" 2>/dev/null || true
  echo "[p4] moved addon/ops/* -> ops/ and removed addon/ops"
fi
WRAPPER_PAT='(^run_.*)|(_wrapper\.)|(verify_workspace\.sh$)|(deploy_to_ha\.sh$)|(restore_addon\.sh$)|(ws\.env$)|(bootstrap_evidence_env\.sh$)'
if [ -d "${WRAP}" ]; then
  shopt -s nullglob
  for f in "${WRAP}"/*; do
    base="$(basename "$f")"
    if [[ -f "$f" && ! "$base" =~ $WRAPPER_PAT ]]; then
      mv "$f" "${OPS}/"
      echo "[p4] moved scripts/${base} -> ops/"
    fi
  done
fi

# ---------- P5: wrappers export WORKSPACE_ROOT & REPORT_ROOT ----------
mkdir -p "${WRAP}"
prepend_export() {
  local file="$1"
  local tmp="${file}.tmp.$$"
  local ws="${WS}"
  local rr="${REPORTS}"
  if ! grep -q 'export WORKSPACE_ROOT=' "$file" 2>/dev/null; then
    {
      echo "export WORKSPACE_ROOT=\"${ws}\""
      echo "export REPORT_ROOT=\"${rr}\""
      cat "$file"
    } > "$tmp" && mv "$tmp" "$file"
    echo "[p5] injected exports into $(basename "$file")"
  else
    if ! grep -q 'export REPORT_ROOT=' "$file"; then
      { echo "export REPORT_ROOT=\"${rr}\""; cat "$file"; } > "$tmp" && mv "$tmp" "$file"
      echo "[p5] injected REPORT_ROOT into $(basename "$file")"
    fi
  fi
}
for w in "${WRAP}/"run_* "${WRAP}/"*"_wrapper."* "${WRAP}/verify_workspace.sh" "${WRAP}/deploy_to_ha.sh"; do
  [ -f "$w" ] && prepend_export "$w" || true
done

# ---------- P6: helper scripts + ADR doc ----------
mkdir -p "${WS}/tools" "${WRAP}" "${DOCS}/adr"

cat > "${WS}/tools/check_structure.sh" <<'EOS'
#!/usr/bin/env bash
set -Eeuo pipefail
WS="${WORKSPACE_ROOT:-__unset__}"
if [ "$WS" = "__unset__" ]; then echo "[fail] WORKSPACE_ROOT not set"; exit 2; fi
ADDON="${WS}/addon"
RUNTIME="/Volumes/HA/addons/local/beep_boop_bb8"
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
EOS
chmod +x "${WS}/tools/check_structure.sh"

cat > "${WRAP}/deploy_to_ha.sh" <<'EOS'
#!/usr/bin/env bash
set -Eeuo pipefail
export GIT_TERMINAL_PROMPT=0
WS="${WORKSPACE_ROOT:-/Users/evertappels/Projects/HA-BB8}"
ADDON="${WS}/addon"
RUNTIME="/Volumes/HA/addons/local/beep_boop_bb8"
REMOTE="git@github.com:e-app-404/ha-bb8-addon.git"

test -d "${ADDON}/.git" || { echo "[fail] addon not a git repo"; exit 1; }
git -C "${ADDON}" remote set-url origin "${REMOTE}"

BR="$(git -C "${ADDON}" rev-parse --abbrev-ref HEAD)"
git -C "${ADDON}" fetch --all
git -C "${ADDON}" push origin "${BR}"

if [ ! -d "${RUNTIME}/.git" ]; then echo "[fail] runtime not a git repo: ${RUNTIME}"; exit 2; fi
git -C "${RUNTIME}" remote set-url origin "${REMOTE}"
git -C "${RUNTIME}" fetch --all --prune
git -C "${RUNTIME}" checkout -B "${BR}" "origin/${BR}"
git -C "${RUNTIME}" reset --hard "origin/${BR}"

RHEAD="$(git -C "${RUNTIME}" rev-parse --short HEAD)"
echo "DEPLOY_OK runtime_head=${RHEAD} branch=${BR}"
EOS
chmod +x "${WRAP}/deploy_to_ha.sh"

cat > "${WRAP}/verify_workspace.sh" <<'EOS'
#!/usr/bin/env bash
set -Eeuo pipefail
export GIT_TERMINAL_PROMPT=0
WS="${WORKSPACE_ROOT:-/Users/evertappels/Projects/HA-BB8}"
ADDON="${WS}/addon"
RUNTIME="/Volumes/HA/addons/local/beep_boop_bb8"
REMOTE="git@github.com:e-app-404/ha-bb8-addon.git"

test -d "${ADDON}/.git" || { echo "[fail] addon not a git repo"; exit 1; }
test -d "${RUNTIME}/.git" || { echo "[fail] runtime not a git repo"; exit 2; }

WSH="$(git -C "${ADDON}" rev-parse --short HEAD)"
RH="$(git -C "${RUNTIME}" rev-parse --short HEAD)"
URL_WS="$(git -C "${ADDON}" remote get-url origin || true)"

echo "VERIFY_OK ws_head=${WSH} runtime_head=${RH} remote=${URL_WS}"
EOS
chmod +x "${WRAP}/verify_workspace.sh"

cat > "${DOCS}/adr/ADR-0001-workspace-topology.md" <<'EOS'
# ADR-0001: Canonical Topology — Dual-Clone via Git Remote (Short)

**Decision (2025-08-21):**
- Workspace clone at `HA-BB8/addon/` (no symlinks, no submodules)
- Runtime clone at `/Volumes/HA/addons/local/beep_boop_bb8`
- Deploy = push (workspace) → fetch+hard-reset (runtime), then restart add-on in HA
- Single report sink via `REPORT_ROOT` exported by wrappers
- Operational tools live under `HA-BB8/ops/` (not inside `addon/`)

**Status:** Approved. Supersedes symlink proposals.

**Notes:** Acceptance tokens: `WS_READY …`, `DEPLOY_OK …`, `VERIFY_OK …`, `STRUCTURE_OK`.
EOS

# ---------- Final: run structure check and emit WS_READY ----------
export WORKSPACE_ROOT="${WS}"
export REPORT_ROOT="${REPORTS}"

"${WS}/tools/check_structure.sh"
echo "WS_READY addon_ws=git_clone_ok runtime=git_clone_ok reports=ok wrappers=ok ops=ok"
