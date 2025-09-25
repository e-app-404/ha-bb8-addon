#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$repo_root" ] || { echo "Not inside a Git repo."; exit 1; }
cd "$repo_root"

# Refuse if there are pre-existing staged changes (avoid committing unrelated files)
if ! git diff --cached --quiet; then
  echo "There are staged changes already. Please commit/stash them before running this setup." >&2
  exit 1
fi

BRANCH="chore/guard-size-symlinks"
if git show-ref --quiet "refs/heads/$BRANCH"; then
  git switch "$BRANCH"
else
  git switch -c "$BRANCH"
fi

# Backup any existing pre-commit hook (timestamped)
if [ -f .git/hooks/pre-commit ]; then
  ts="$(date +%Y%m%d-%H%M%S)"
  mv .git/hooks/pre-commit ".git/hooks/pre-commit.bak.$ts"
  echo "Backed up existing pre-commit to .git/hooks/pre-commit.bak.$ts"
fi

mkdir -p tools/validators .github/workflows

# Ensure validator exists (this setup does not overwrite if you already customized it)
if [ ! -f tools/validators/guard_size_symlinks.sh ]; then
  cat > tools/validators/guard_size_symlinks.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
thresh=$((50*1024*1024))
mode="local"; [ "${CI:-}" = "true" ] && mode="ci"
if git ls-files -s | awk '$1 ~ /^120/ {print $4}' | grep -q .; then
  echo "ERROR: symlinks tracked in Git:" >&2
  git ls-files -s | awk '$1 ~ /^120/ {print $4}' >&2
  exit 2
fi
DIFF_CMD=()
if [ "$mode" = "local" ]; then
  DIFF_CMD=(git diff --cached --name-only --diff-filter=AM -z)
else
  if [ -n "${GITHUB_BASE_REF:-}" ]; then
    base_ref="$GITHUB_BASE_REF"; git fetch origin "$base_ref" --depth=1 || true
    DIFF_CMD=(git diff --name-only "origin/${base_ref}...HEAD" -z)
  else
    git fetch origin main --depth=1 || true
    DIFF_CMD=(git diff --name-only origin/main...HEAD -z)
  fi
fi
tmpf="$(mktemp)"; trap 'rm -f "$tmpf"' EXIT
if ! "${DIFF_CMD[@]}" >"$tmpf" 2>/dev/null || [ ! -s "$tmpf" ]; then
  : > "$tmpf"; git ls-files -z >> "$tmpf"
fi
ok=1
while IFS= read -r -d '' f; do
  [ -f "$f" ] || continue
  sz=$(wc -c < "$f")
  if [ "$sz" -gt "$thresh" ]; then
    printf 'ERROR: Large file (>50MB): %s (%d bytes)\n' "$f" "$sz" >&2
    ok=0
  fi
done < "$tmpf"
[ "$ok" -eq 1 ] && echo "OK: size/symlink guard passed" || exit 3
SH
  chmod +x tools/validators/guard_size_symlinks.sh
fi

# Local pre-commit hook
cat > .git/hooks/pre-commit <<'H'
#!/usr/bin/env bash
set -e
bash tools/validators/guard_size_symlinks.sh
H
chmod +x .git/hooks/pre-commit

# CI workflow (idempotent overwrite)
cat > .github/workflows/guard-size-symlinks.yml <<'YML'
name: Guard: block large files & symlinks
on: [push, pull_request]
jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Run validator
        run: bash tools/validators/guard_size_symlinks.sh
YML

# Stage only the intended files
git add -- tools/validators/guard_size_symlinks.sh .github/workflows/guard-size-symlinks.yml

if git diff --cached --quiet; then
  echo "Nothing to commit (files already up to date)."
else
  git commit -m "guardrails(v2.1): filename-safe diff capture; clean tree guard; CI workflow"
fi

# Push branch (prefer 'github', else 'origin')
if git remote get-url github >/dev/null 2>&1; then
  git push -u github "$BRANCH"
else
  git push -u origin "$BRANCH"
fi

echo "Done. Open a PR for branch: $BRANCH"
