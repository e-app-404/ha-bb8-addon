#!/usr/bin/env bash
set -euo pipefail

WS="/Users/evertappels/Projects/HA-BB8"
RUNTIME="/Volumes/HA/addons/local/beep_boop_bb8"
REMOTE="git@github.com:e-app-404/ha-bb8-addon.git"

echo "[setup] Workspace=${WS}"
echo "[setup] Runtime=${RUNTIME}"
echo "[setup] Remote=${REMOTE}"

# Backup any old workspace addon folder/symlink
TS="$(date -u +%Y%m%d_%H%M%S)"
BK="${WS}/_backup_${TS}"
mkdir -p "${BK}"
if [ -e "${WS}/addon" ] && [ ! -d "${WS}/addon/.git" ]; then
  echo "[setup] Backing up existing workspace addon/ to ${BK}"
  tar -C "${WS}" -cf "${BK}/addon.tar" addon || true
  rm -rf "${WS}/addon"
fi

# Ensure .gitignore covers local-only artifacts
cd "${WS}"
{ grep -qxF "/_backup_*/" .gitignore || echo "/_backup_*/"; } >> .gitignore
{ grep -qxF ".venv*/"     .gitignore || echo ".venv*/"; }     >> .gitignore
{ grep -qxF "/reports/"   .gitignore || echo "/reports/"; }   >> .gitignore
{ grep -qxF ".evidence.env" .gitignore || echo ".evidence.env"; } >> .gitignore
git add .gitignore || true
git commit -m "gitignore: backups, venv, reports, evidence env" || true

# Initialize/refresh submodule at addon/
if [ -f .gitmodules ] && grep -q "path = addon" .gitmodules; then
  echo "[setup] Updating existing submodule origin"
  git submodule deinit -f addon || true
  git rm -f addon || true
  rm -rf .git/modules/addon || true
fi
git submodule add "${REMOTE}" addon
git commit -m "Track add-on as submodule (ha-bb8-addon)" || true

# Ensure runtime clone matches remote
if [ -d "${RUNTIME}/.git" ]; then
  echo "[setup] Updating runtime clone"
  cd "${RUNTIME}"
  git remote set-url origin "${REMOTE}"
  git fetch --all
  git reset --hard origin/main
else
  echo "[setup] Creating runtime clone at ${RUNTIME}"
  mkdir -p "$(dirname "${RUNTIME}")"
  git clone "${REMOTE}" "${RUNTIME}"
fi

# Create deploy + verify helpers
mkdir -p "${WS}/scripts"

cat > "${WS}/scripts/deploy_to_ha.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
WS="/Users/evertappels/Projects/HA-BB8"
RUNTIME="/Volumes/HA/addons/local/beep_boop_bb8"

cd "$WS/addon"
git rev-parse --is-inside-work-tree >/dev/null
BR=$(git rev-parse --abbrev-ref HEAD)
git push origin "$BR"

cd "$RUNTIME"
git fetch --all
git reset --hard "origin/$BR"
echo "[deploy] runtime now at $(git rev-parse --short HEAD) on $BR"
EOF
chmod +x "${WS}/scripts/deploy_to_ha.sh"

cat > "${WS}/scripts/verify_workspace.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
WS="/Users/evertappels/Projects/HA-BB8"
RUNTIME="/Volumes/HA/addons/local/beep_boop_bb8"

echo "workspace addon is git clone?"; git -C "$WS/addon" rev-parse --is-inside-work-tree
echo "runtime addon is git clone?";   git -C "$RUNTIME"  rev-parse --is-inside-work-tree

echo "workspace HEAD: $(git -C "$WS/addon" rev-parse --short HEAD)"
echo "runtime   HEAD: $(git -C "$RUNTIME"  rev-parse --short HEAD)"

echo "remote (workspace): $(git -C "$WS/addon" remote get-url origin)"
echo "remote (runtime)  : $(git -C "$RUNTIME"  remote get-url origin)"
EOF
chmod +x "${WS}/scripts/verify_workspace.sh"

# VS Code tasks to force bash for our scripts
mkdir -p "${WS}/.vscode"
cat > "${WS}/.vscode/tasks.json" <<'EOF'
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Deploy add-on to HA (bash)",
      "type": "shell",
      "command": "bash",
      "args": ["scripts/deploy_to_ha.sh"],
      "options": { "cwd": "${workspaceFolder}" },
      "problemMatcher": []
    },
    {
      "label": "Verify workspace/runtime (bash)",
      "type": "shell",
      "command": "bash",
      "args": ["scripts/verify_workspace.sh"],
      "options": { "cwd": "${workspaceFolder}" },
      "problemMatcher": []
    }
  ]
}
EOF

# Stage helpers in workspace repo
cd "${WS}"
git add scripts/deploy_to_ha.sh scripts/verify_workspace.sh .vscode/tasks.json
git commit -m "Add bash tasks + deploy/verify helpers for ha-bb8-addon" || true

echo "[setup] DONE. Next steps:"
echo "1) Run: bash scripts/one_shot_setup.sh  (this script)"
echo "2) Then: bash scripts/verify_workspace.sh"
echo "3) Develop in HA-BB8/addon (submodule), commit+push, then: bash scripts/deploy_to_ha.sh"
