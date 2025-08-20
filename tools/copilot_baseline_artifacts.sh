#!/bin/bash
set -euo pipefail

# Baseline SHA from your previous step
BASE_SHA="b5661c9c7c90418498790113d4d45915bd3eb5f8"

mkdir -p reports/checkpoints reports/patches

echo "[Copilot] Generating Bill of Materials (BoM)..."
git show --name-status --format=%H "$BASE_SHA" | tee "reports/checkpoints/BOM_${BASE_SHA}.txt"

echo "[Copilot] Generating unified diff..."
git diff --no-color "${BASE_SHA}^!" | tee "reports/patches/DELTA-STP5-VARIOUS_${BASE_SHA}.patch"

echo "=== RUNTIME_TOUCHPOINTS ==="
grep -E "homeassistant/|bb8/|stat_t|cmd(_t)?|state|availability|retain" -n "reports/patches/DELTA-STP5-VARIOUS_${BASE_SHA}.patch" || true

echo "=== BOM ==="
sed -n '1,2000p' "reports/checkpoints/BOM_${BASE_SHA}.txt"

echo "=== PATCH ==="
sed -n '1,2000p' "reports/patches/DELTA-STP5-VARIOUS_${BASE_SHA}.patch"

# Step 3: VCS actions (tag, branch, PR)
TAG="RE-BASELINE_20250819_185143Z"
BRANCH="rebaseline/stp5-various-pass"
PR_TITLE="RE-BASELINE: STP5 VARIOUS (QA PASS)"
PR_BODY_FILE="reports/checkpoints/PR_BODY_${TAG}.md"

{
	echo "# ${PR_TITLE}"
	echo ""
	echo "- Baseline SHA: ${BASE_SHA}"
	echo "- Tag: ${TAG}"
	echo ""
	echo "## Bill of Materials"
	sed -n '1,400p' "reports/checkpoints/BOM_${BASE_SHA}.txt"
	echo ""
	echo "## Unified Diff (DELTA-STP5-VARIOUS)"
	echo '```diff'
	sed -n '1,1000p' "reports/patches/DELTA-STP5-VARIOUS_${BASE_SHA}.patch"
	echo '```'
} > "$PR_BODY_FILE"

git tag -a "$TAG" "$BASE_SHA" -m "$PR_TITLE"
git branch -f "$BRANCH" "$BASE_SHA"
git push origin "$TAG"
git push -u origin "$BRANCH"
if command -v gh >/dev/null 2>&1; then
	PR_URL="$(gh pr create --title "$PR_TITLE" --body-file "$PR_BODY_FILE" --base main --head "$BRANCH")"
	echo "PR_URL=$PR_URL"
else
	echo "[WARN] gh not installed; open a PR from branch '$BRANCH' to 'main' with body from $PR_BODY_FILE"
fi

# Confirm tag and branch existence on origin
echo "=== TAGS ON ORIGIN ==="
git ls-remote --tags origin | grep "$TAG" || echo "Tag $TAG not found on origin."
echo "=== BRANCHES ON ORIGIN ==="
git ls-remote --heads origin | grep "$BRANCH" || echo "Branch $BRANCH not found on origin."
