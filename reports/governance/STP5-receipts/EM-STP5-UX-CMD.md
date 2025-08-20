ACK: Copilot QA PASS for **DELTA-STP5-VARIOUS.patch**. Acting as **Strategos (dual-role)** per directive.

---

## 1) Receipt verification (no code changes) — **Copilot, run & paste outputs**

Run from **repo root** and paste everything it prints back here.

```bash
# verify-and-extract-receipts[DELTA-STP5-VARIOUS]
set -euo pipefail

TS="20250819_185143Z"
declare -a NAMES=(
  "pythagoras_receipt_${TS}.status"
  "summary_${TS}.md"
  "project_status.log"
  "verify_no_led.log"
  "verify_led.log"
)

echo "[strategos] locating receipt files…"
found_paths=()

# search tracked files first
for n in "${NAMES[@]}"; do
  p="$(git ls-files | grep -E "/${n}$" || true)"
  if [ -z "$p" ]; then
    # fallback to working tree search
    p="$(find . -type f -name "$n" | head -n1 || true)"
  fi
  if [ -z "$p" ]; then
    echo "[ERROR] missing $n"; exit 2
  fi
  found_paths+=("$p")
done

printf "[strategos] receipts found:\n- %s\n" "${found_paths[@]}"

# choose the status file as anchor for baseline commit
STATUS_PATH="${found_paths[0]}"

# derive baseline sha from the commit that last touched the status file
BASE_SHA="$(git log -n1 --follow --format=%H -- "$STATUS_PATH")"
[ -n "$BASE_SHA" ] || { echo "[ERROR] could not determine baseline sha"; exit 3; }

echo "=== BASELINE_SHA ==="
echo "$BASE_SHA"

echo "=== RECEIPT_CONTENTS ==="
for p in "${found_paths[@]}"; do
  echo "<<<FILE:$p>>>"
  sed -n '1,2000p' "$p"
  echo "<<<END:$p>>>"
done
```

> Paste back: the `BASELINE_SHA` plus each `<<<FILE:…>>> … <<<END:…>>>` text block.

---

## 2) Baseline artifacts request — **Copilot, same baseline SHA**

Using the **exact** `$BASE_SHA` from step 1:

```bash
# derive BoM + unified diff + runtime delta notes
set -euo pipefail
BASE_SHA="${BASE_SHA:?missing}"

mkdir -p reports/checkpoints reports/patches

# Bill of Materials (files added/changed/removed in that commit)
git show --name-status --format=%H "$BASE_SHA" | tee "reports/checkpoints/BOM_${BASE_SHA}.txt"

# Full unified diff for the single commit
git diff --no-color "${BASE_SHA}^!" | tee "reports/patches/DELTA-STP5-VARIOUS_${BASE_SHA}.patch"

echo "=== RUNTIME_TOUCHPOINTS ==="
# Heuristic scan for MQTT/discovery/retain/topic changes in diff content
grep -E "homeassistant/|bb8/|stat_t|cmd(_t)?|state|availability|retain" -n "reports/patches/DELTA-STP5-VARIOUS_${BASE_SHA}.patch" || true

echo "=== BOM ==="
sed -n '1,2000p' "reports/checkpoints/BOM_${BASE_SHA}.txt"

echo "=== PATCH ==="
sed -n '1,2000p' "reports/patches/DELTA-STP5-VARIOUS_${BASE_SHA}.patch"
```

> Paste back: `=== RUNTIME_TOUCHPOINTS ===`, `=== BOM ===`, and `=== PATCH ===` sections.

---

## 3) VCS actions on that validated commit — **Copilot, execute**

````bash
# rebaseline tag/branch/PR
set -euo pipefail
BASE_SHA="${BASE_SHA:?missing}"
TAG="RE-BASELINE_2025-08-19T18:51:43Z"
BRANCH="rebaseline/stp5-various-pass"
PR_TITLE="RE-BASELINE: STP5 VARIOUS (QA PASS)"
PR_BODY_FILE="reports/checkpoints/PR_BODY_${TAG}.md"

# Prepare PR body with BoM + inline patch reference
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

# Create tag and branch at baseline
git tag -a "$TAG" "$BASE_SHA" -m "$PR_TITLE"
git branch -f "$BRANCH" "$BASE_SHA"

# Push (origin must be configured)
git push origin "$TAG"
git push -u origin "$BRANCH"

# Create PR (requires GitHub CLI); fall back to message if gh not present
if command -v gh >/dev/null 2>&1; then
  PR_URL="$(gh pr create --title "$PR_TITLE" --body-file "$PR_BODY_FILE" --base main --head "$BRANCH")"
  echo "PR_URL=$PR_URL"
else
  echo "[WARN] gh not installed; open a PR from branch '$BRANCH' to 'main' with body from $PR_BODY_FILE"
fi

# Attach the 5 receipts to the PR if gh is available
if command -v gh >/dev/null 2>&1 && [ -n "${PR_URL:-}" ]; then
  for f in $(git ls-files | grep -E "/(pythagoras_receipt_${TS}\.status|summary_${TS}\.md|project_status\.log|verify_no_led\.log|verify_led\.log)$"); do
    gh pr comment "$PR_URL" --body "Attached: \`$f\`\n\n\`\`\`\n$(sed -n '1,2000p' "$f")\n\`\`\`" || true
  done
fi
````

> Paste back: the printed `PR_URL` (or confirm manual PR created) and confirmation that the tag + branch exist on origin.

---

## 4) SIM102 tidy (optional) — **Copilot, zero behavior change**

````bash
# chore: fix SIM102 warnings safely
set -euo pipefail
git checkout -b chore/ruff-sim102 "$BRANCH"

ruff --select SIM102 .
ruff --select SIM102 --fix .

# Show the minimal diff (expect tiny)
git diff --no-color | tee reports/patches/CHORE_SIM102_${TAG}.patch

# Re-run QA gates
ruff .
black --check .
mypy .
pytest -q
coverage run -m pytest -q && coverage report -m || true  # if coverage configured

git add -A
git commit -m "chore(lint): resolve ruff SIM102 (no behavior change)"
git push -u origin chore/ruff-sim102

# Comment QA results on the PR (if gh available)
if command -v gh >/dev/null 2>&1 && [ -n "${PR_URL:-}" ]; then
  gh pr comment "$PR_URL" --body "$(printf '**SIM102 patch applied. QA rerun:**\n\n```\n%s\n```\n' "$( { ruff .; echo; black --check .; echo; mypy .; echo; pytest -q; } 2>&1 )")" || true
fi
````

> Paste back: the tiny `CHORE_SIM102_*.patch` content and QA summary (PASS/FAIL).

---

## 5) Prepare strict **STP4 attestation** (post-merge or fast-forward to tag) — **Copilot**

```bash
# strict STP4 evidence
set -euo pipefail
git checkout main
git pull --ff-only
git merge --ff-only "$TAG" || true  # or ensure main is at the tag

export MQTT_BASE=bb8
export REQUIRE_DEVICE_ECHO=1
export ENABLE_BRIDGE_TELEMETRY=1

make evidence-stp4

# Return artifacts
echo "=== EVIDENCE: evidence_manifest.json ==="
sed -n '1,400p' reports/evidence/evidence_manifest.json

echo "=== EVIDENCE: ha_mqtt_trace_snapshot (first ~400 lines) ==="
sed -n '1,400p' reports/evidence/ha_mqtt_trace_snapshot.json 2>/dev/null || sed -n '1,400p' reports/evidence/ha_mqtt_trace_snapshot.jsonl 2>/dev/null || true

echo "=== LOG HEAD (first 150 lines) ==="
sed -n '1,150p' reports/evidence/run.log
```

> Paste back: the three evidence blocks above.

---

## Return format (fill after executing the above)

When you paste the outputs, also include this JSON filled with actual values:

```json
{
  "baseline_sha": "<BASELINE_SHA>",
  "tagged": true,
  "pr_url": "<PR_URL or 'manual'>",
  "qa_verdict": "PASS",
  "strict_evidence_ready": true
}
```

---

### Notes

* I cannot attach or read your repo files directly; the blocks above make the process deterministic and auditable.
* Keep commit prefixes per directive: `RE-BASELINE: <receipt_id>` for the PR title already encoded via tag/PR title; subsequent commits should follow that rule.
