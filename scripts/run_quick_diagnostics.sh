#!/usr/bin/env bash
set -euo pipefail
OUT="docs/meta/diagnostics_2025-09-25.txt"
rm -f "$OUT"
exec > "$OUT" 2>&1

echo "# Quick diagnostics output captured on: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "=== git remote -v"
git remote -v || true

echo
echo "=== git rev-parse --abbrev-ref HEAD"
git rev-parse --abbrev-ref HEAD || true

echo
echo "=== git config --get init.defaultBranch || true"
git config --get init.defaultBranch || true

echo
echo "=== git branch -r | sed -n '1,50p'"
git branch -r | sed -n '1,50p' || true

echo
echo "=== git lfs env 2>/dev/null | sed -n '1,80p' || echo 'no-git-lfs'"
if command -v git-lfs >/dev/null 2>&1; then
  git lfs env 2>/dev/null | sed -n '1,80p' || true
else
  echo "no-git-lfs"
fi

echo
echo "=== git submodule status 2>/dev/null || echo 'no-submodules'"
git submodule status 2>/dev/null || echo "no-submodules"

echo
echo "=== git config --list | grep -E 'user.signingkey|commit.gpgsign|tag.gpgsign' || true"
git config --list | grep -E 'user.signingkey|commit.gpgsign|tag.gpgsign' || true

echo
echo "=== top 20 largest files"
# handle filenames with spaces
git ls-files -z | xargs -0 -I{} sh -c 'test -f "{}" && wc -c < "{}" | awk -v f="{}" "{print \$1, f}"' | sort -nr | head -20 || true

echo
echo "=== symlinks"
find . -type l | sed -n '1,120p' || true

echo
echo "=== nested .git"
find . -type d -name .git -not -path "./.git" | sed -n '1,120p' || true

echo
echo "=== path probes"
grep -R -n --exclude-dir=".git" -E '/config|/data|/n/ha' . | sed -n '1,120p' || true

echo
echo "=== .github workflows"
ls -la .github/workflows 2>/dev/null || echo "no-ci"


echo

echo "# End of diagnostics"
