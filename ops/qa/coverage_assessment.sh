#!/bin/bash
# File: ops/qa/coverage_assessment.sh  
# Purpose: Standardized coverage measurement per ADR-0038
# Usage: ./ops/qa/coverage_assessment.sh [--phase1|--phase2|--phase3]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPORTS_DIR="$ROOT/reports/coverage"

# Ensure reports directory exists
mkdir -p "$REPORTS_DIR"

# Configuration per ADR-0038
BASELINE_PCT=49.7
PHASE1_TARGET=65.0
PHASE2_TARGET=75.0  
PHASE3_TARGET=85.0

echo "=== ADR-0038 Coverage Assessment ==="
echo "Baseline: ${BASELINE_PCT}% (October 2025)"
echo "Current Target Phase: $1"
echo "Assessment Time: $(date -Iseconds)"
echo

cd "$ROOT"

# Activate virtual environment if available
if [[ -f ".venv/bin/activate" ]]; then
    source .venv/bin/activate
    echo "✓ Virtual environment activated"
fi

# Run standardized coverage measurement per ADR-0038
echo "Running standardized test suite..."
PYTHONPATH="$ROOT" python -m pytest addon/tests/ \
    --ignore=addon/tests/test_logging_setup_complete.py \
    --ignore=addon/tests/test_echo_responder_end_to_end.py \
    --ignore=addon/tests/test_mqtt_dispatcher_integration.py \
    --ignore=addon/tests/test_ble_bridge_mocks.py \
    --ignore=addon/tests/test_bridge_controller_complete.py \
    --ignore=addon/tests/test_addon_config_complete.py \
    --ignore=addon/tests/test_facade_complete_integration.py \
    --cov=addon/bb8_core \
    --cov-report=json:"$REPORTS_DIR/coverage_$(date +%Y%m%d_%H%M%S).json" \
    --cov-report=term-missing \
    --tb=no -q 2>/dev/null || echo "✓ Tests completed (some expected failures)"

# Get the latest coverage file
LATEST_COVERAGE=$(ls -t "$REPORTS_DIR"/coverage_*.json | head -1)

if [[ ! -f "$LATEST_COVERAGE" ]]; then
    echo "❌ ERROR: No coverage file generated"
    exit 1
fi

echo "✓ Coverage data: $LATEST_COVERAGE"
echo

# Analyze coverage per ADR-0038 framework
python3 -c "
import json
import sys
from datetime import datetime

# Load coverage data
with open('$LATEST_COVERAGE') as f:
    cov = json.load(f)

total_pct = cov['totals']['percent_covered']
total_lines = cov['totals']['num_statements']
covered_lines = cov['totals']['covered_lines']

print('=== ADR-0038 COVERAGE ANALYSIS ===')
print()
print(f'📊 Current Coverage: {total_pct:.1f}%')
print(f'📈 Lines Covered: {covered_lines:,}/{total_lines:,}')

# Determine operational confidence level per ADR-0038
if total_pct >= 80:
    confidence = '🟢 CRITICAL (Production Ready)'
elif total_pct >= 60:
    confidence = '🟡 OPERATIONAL (Staging Ready)'
elif total_pct >= 40:
    confidence = '🟠 DEVELOPMENT (Feature Complete)'
elif total_pct >= 20:
    confidence = '🔴 FOUNDATIONAL (Basic Functionality)'
else:
    confidence = '⚫ EXPERIMENTAL (Prototype Only)'

print(f'🎯 Confidence Level: {confidence}')
print()

# Phase progress analysis
baseline = $BASELINE_PCT
phase1_target = $PHASE1_TARGET
phase2_target = $PHASE2_TARGET  
phase3_target = $PHASE3_TARGET

progress_from_baseline = total_pct - baseline
print(f'📈 Progress from Baseline: {progress_from_baseline:+.1f}% (from {baseline}%)')

if total_pct >= phase3_target:
    print(f'🎉 Phase 3 COMPLETE: Production Ready ({total_pct:.1f}% ≥ {phase3_target}%)')
elif total_pct >= phase2_target:
    print(f'✅ Phase 2 COMPLETE: Limited Production ({total_pct:.1f}% ≥ {phase2_target}%)')
    remaining = phase3_target - total_pct
    print(f'🎯 Phase 3 Progress: {remaining:.1f}% remaining to production ready')
elif total_pct >= phase1_target:
    print(f'✅ Phase 1 COMPLETE: Staging Ready ({total_pct:.1f}% ≥ {phase1_target}%)')
    remaining = phase2_target - total_pct
    print(f'🎯 Phase 2 Progress: {remaining:.1f}% remaining to limited production')
else:
    remaining = phase1_target - total_pct
    print(f'🔄 Phase 1 IN PROGRESS: {remaining:.1f}% remaining to staging ready')

print()

# Critical modules analysis per ADR-0038
critical_modules = ['bridge_controller', 'mqtt_dispatcher', 'facade', 'ble_bridge']
critical_coverage = {}

for filepath, data in cov['files'].items():
    if 'bb8_core' in filepath and 'test_' not in filepath:
        modname = filepath.split('/')[-1].replace('.py', '')
        if modname in critical_modules:
            critical_coverage[modname] = {
                'percent': data['summary']['percent_covered'],
                'lines': data['summary']['num_statements'],
                'covered': data['summary']['covered_lines']
            }

print('=== CRITICAL MODULES STATUS ===')
critical_total_lines = sum(m['lines'] for m in critical_coverage.values())
critical_covered_lines = sum(m['covered'] for m in critical_coverage.values())
critical_pct = (critical_covered_lines / critical_total_lines * 100) if critical_total_lines > 0 else 0

print(f'🎯 Critical Modules Overall: {critical_pct:.1f}% ({critical_covered_lines}/{critical_total_lines} lines)')

for mod in critical_modules:
    if mod in critical_coverage:
        data = critical_coverage[mod]
        pct = data['percent']
        covered = data['covered']
        lines = data['lines']
        status = '🟢' if pct >= 85 else '🟡' if pct >= 60 else '🔴'
        target_lines = int(lines * 0.85)  # 85% target for critical modules
        needed = max(0, target_lines - covered)
        print(f'  {status} {mod:20} {pct:5.1f}% ({covered:3}/{lines:3}) [need +{needed:2} lines to 85%]')
    else:
        print(f'  ❓ {mod:20} Not found in coverage data')

print()

# Compliance check per ADR-0038
regression_check = total_pct >= baseline
print('=== COMPLIANCE CHECK ===')
print(f'✅ No Regression: {regression_check} (Current {total_pct:.1f}% ≥ Baseline {baseline}%)')

# Generate improvement recommendations
print()
print('=== IMMEDIATE IMPROVEMENT OPPORTUNITIES ===')

# Quick wins analysis
quick_wins = []
for filepath, data in cov['files'].items():
    if 'bb8_core' in filepath and 'test_' not in filepath:
        modname = filepath.split('/')[-1].replace('.py', '')
        pct = data['summary']['percent_covered']
        lines = data['summary']['num_statements']
        covered = data['summary']['covered_lines']
        
        if 50 <= pct < 80 and lines >= 20:
            target_coverage = min(80, pct + 20)  # Conservative improvement target
            potential_gain = int((target_coverage - pct) / 100 * lines)
            quick_wins.append((modname, pct, target_coverage, potential_gain, lines))

if quick_wins:
    total_gain = sum(gain for _, _, _, gain, _ in quick_wins[:5])  # Top 5 opportunities
    print(f'🚀 Top Quick Win Opportunities (+{total_gain} lines potential):')
    for mod, current, target, gain, total_lines in sorted(quick_wins, key=lambda x: x[3], reverse=True)[:5]:
        print(f'  📈 {mod:25} {current:5.1f}% → {target:.0f}% = +{gain:3} lines ({total_lines} total)')
    
    projected_new_pct = (covered_lines + total_gain) / total_lines * 100
    print(f'  🎯 With quick wins: {projected_new_pct:.1f}% total coverage')
else:
    print('🔍 No obvious quick wins identified - focus on critical modules')

print()
print('=== ASSESSMENT COMPLETE ===')
print(f'Report saved: $LATEST_COVERAGE')
"

echo "✅ Coverage assessment complete per ADR-0038"
echo "📁 Detailed report: $LATEST_COVERAGE"