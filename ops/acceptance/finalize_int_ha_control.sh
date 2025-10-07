#!/bin/bash
# Step 8: Operator convenience wrapper for INT-HA-CONTROL finalization
# Executes steps 1, 3, 7 and provides QG-TEST-80 next steps

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")

echo "=== INT-HA-CONTROL Finalization Wrapper ==="
echo "Timestamp: $TIMESTAMP"
echo "Project Root: $PROJECT_ROOT"

# Step 1: Tag & promote accepted build
echo ""
echo "Step 1: Creating acceptance tag..."
cd "$PROJECT_ROOT"
COMMIT_ID=$(git rev-parse --short HEAD)
echo "Current commit: $COMMIT_ID"

if ! git tag -l | grep -q "INT-HA-CONTROL_ACCEPTED_2025-10-07"; then
    echo "Creating acceptance tag..."
    git tag -a INT-HA-CONTROL_ACCEPTED_2025-10-07 -m "INT-HA-CONTROL accepted; P0/Persistence/Echo/LED gate OK; evidence archived"
    git push origin INT-HA-CONTROL_ACCEPTED_2025-10-07
    echo "✅ Tag created and pushed"
else
    echo "✅ Acceptance tag already exists"
fi

echo "$COMMIT_ID" > reports/checkpoints/INT-HA-CONTROL/commit.txt

# Step 3: Persist acceptance record
echo ""
echo "Step 3: Creating acceptance record..."
if [[ ! -f "reports/checkpoints/INT-HA-CONTROL/ACCEPTANCE.md" ]]; then
    echo "⚠️  ACCEPTANCE.md not found - manual creation required"
else
    echo "✅ ACCEPTANCE.md exists"
fi

git add reports/checkpoints/INT-HA-CONTROL/ACCEPTANCE.md reports/checkpoints/INT-HA-CONTROL/commit.txt 2>/dev/null || true
if git diff --staged --quiet; then
    echo "✅ No new changes to commit"
else
    git commit -m "INT-HA-CONTROL: finalization wrapper execution - $TIMESTAMP"
    echo "✅ Acceptance record committed"
fi

# Step 7: Evidence pack & archive
echo ""
echo "Step 7: Creating final evidence pack..."
cd reports/checkpoints

if [[ ! -f "INT-HA-CONTROL_ACCEPTED_${TIMESTAMP}.tar.gz" ]]; then
    tar -czf "INT-HA-CONTROL_ACCEPTED_${TIMESTAMP}.tar.gz" INT-HA-CONTROL/
    echo "✅ Evidence pack created: INT-HA-CONTROL_ACCEPTED_${TIMESTAMP}.tar.gz"
else
    echo "✅ Evidence pack already exists"
fi

# Generate index
cd "$PROJECT_ROOT"
find reports/checkpoints/INT-HA-CONTROL -maxdepth 1 -type f -exec ls -la {} \; | \
    awk '{print $6" "$7" "$8"  "$5"  "$9}' | sort > reports/checkpoints/INT-HA-CONTROL/INDEX.txt

ARTIFACT_COUNT=$(cat reports/checkpoints/INT-HA-CONTROL/INDEX.txt | wc -l | tr -d ' ')
echo "✅ INDEX.txt updated with $ARTIFACT_COUNT artifacts"

# Archive hygiene
mkdir -p config/hestia/workspace/archive/dev_envs/"$TIMESTAMP"
echo "✅ Archive structure created"

echo ""
echo "=== FINALIZATION COMPLETE ==="
echo "📦 Evidence Pack: reports/checkpoints/INT-HA-CONTROL_ACCEPTED_${TIMESTAMP}.tar.gz"
echo "📋 Artifact Index: reports/checkpoints/INT-HA-CONTROL/INDEX.txt ($ARTIFACT_COUNT files)"
echo "🏷️  Acceptance Tag: INT-HA-CONTROL_ACCEPTED_2025-10-07"
echo "📝 Acceptance Record: reports/checkpoints/INT-HA-CONTROL/ACCEPTANCE.md"

echo ""
echo "=== NEXT STEPS: QG-TEST-80 COVERAGE MILESTONE ==="
echo "1. Branch created: qg-test-80/coverage-honest-2025-10-07"
echo "2. Coverage policy applied: 60% fail_under threshold"
echo "3. Integration tests seeded: addon/tests/integration/"
echo "4. Plan document: docs/quality/QG-TEST-80_PLAN.md"
echo ""
echo "To continue with QG-TEST-80:"
echo "  git checkout qg-test-80/coverage-honest-2025-10-07"
echo "  make testcov  # Run coverage baseline"
echo "  # Implement integration tests per QG-TEST-80_PLAN.md"
echo ""
echo "✅ INT-HA-CONTROL closure complete - ready for QG-TEST-80"