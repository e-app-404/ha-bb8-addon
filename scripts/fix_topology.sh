echo "== Remove incorrect addon subdirs =="
git rm -r --cached addon/scripts addon/reports addon/docs 2>/dev/null || true
rm -rf addon/scripts addon/reports addon/docs || true

echo "== Ensure workspace-level dirs exist =="
mkdir -p reports scripts ops docs .githooks .github _backups
touch reports/.gitkeep scripts/.gitkeep

echo "== Backup policy: enforce _backups (rename from _backup if present) =="
if [ -d _backup ] && [ ! -d _backups ]; then
  mkdir -p _backups
  find _backup -maxdepth 1 -type f -name '*.tar.gz' -exec mv -n {} _backups/ \;
fi
find . -maxdepth 1 -type d -name '_backup_*' -exec rm -rf {} +

echo "== .gitignore hardening =="
touch .gitignore
add_ignore() { grep -qxF "$1" .gitignore || echo "$1" >> .gitignore; }

add_ignore ".DS_Store"
add_ignore "docs/.DS_Store"

add_ignore "_backups/*.tar.gz"

add_ignore "addon/scripts/"
add_ignore "addon/reports/"
add_ignore "addon/docs/"

grep -qxF "!reports/.gitkeep" .gitignore || echo "!reports/.gitkeep" >> .gitignore
grep -qxF "!scripts/.gitkeep" .gitignore || echo "!scripts/.gitkeep" >> .gitignore

echo "== Stage and commit =="
git add -A .gitignore reports/.gitkeep scripts/.gitkeep
git commit -m "ADR-0001 addendum v2: move scripts/reports to workspace root; enforce _backups/; purge invalid addon/*" || true
git push
echo "WS_PUSH_OK:$(git branch --show-current)"
#!/usr/bin/env bash
set -euo pipefail

if [ -d _backup ]; then
  mkdir -p _backups
  find _backup -maxdepth 1 -type f -name '*.tar.gz' -exec mv -n {} _backups/ \;
  git rm -r --cached _backup 2>/dev/null || true
  rm -rf _backup
fi

git add \
  .githooks/pre-push \
  .github/workflows/adr-structure.yml \
  docs/ADR/ADR-0001-workspace-topology.md \
  .gitignore \
  reports/.gitkeep \
  scripts/.gitkeep

git add scripts/fix_topology.sh

git commit -m "ADR-0001 addendum v2: remove legacy _backup; align guard & workflow; workspace scripts/reports at root" || true
git push
echo "WS_PUSH_OK:$(git branch --show-current)"
