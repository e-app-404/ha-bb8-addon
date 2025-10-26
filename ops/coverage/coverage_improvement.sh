#!/bin/bash
# HA-BB8 Coverage Improvement Script (ADR-0038 Implementation)
# Based on clean baseline: 19.6% coverage (682/3471 lines)

set -euo pipefail

cd "$(dirname "$0")/../.."
source .venv/bin/activate

BASELINE_COVERAGE=19.6
BASELINE_LINES=682
TOTAL_LINES=3471

# Working test files (exclude broken ones)
WORKING_TESTS=(
    "addon/tests/test_ble_gateway.py"
    "addon/tests/test_ble_link.py" 
    "addon/tests/test_ble_utils.py"
    "addon/tests/test_common.py"
    "addon/tests/test_types.py"
    "addon/tests/test_verify_discovery.py"
)

echo "🎯 HA-BB8 Coverage Improvement Protocol"
echo "========================================"
echo "📊 Clean Baseline: ${BASELINE_COVERAGE}% (${BASELINE_LINES}/${TOTAL_LINES} lines)"
echo "🔧 Working Tests: ${#WORKING_TESTS[@]} files"
echo

# Function to run coverage with working tests only
run_coverage_assessment() {
    echo "🔍 Running coverage assessment..."
    PYTHONPATH="$PWD" python -m pytest "${WORKING_TESTS[@]}" \
        --cov=addon/bb8_core \
        --cov-report=json:coverage.json \
        --cov-report=term-missing \
        --quiet
}

# Function to analyze coverage data
analyze_coverage() {
    python3 -c "
import json
with open('coverage.json', 'r') as f:
    data = json.load(f)
    
covered = data['totals']['covered_lines'] 
total = data['totals']['num_statements']
percent = (covered / total * 100) if total > 0 else 0

print(f'📈 Current Coverage: {covered}/{total} lines = {percent:.1f}%')

# Confidence levels
if percent >= 60:
    level = '🟢 OPERATIONAL'
elif percent >= 45:
    level = '🟡 DEVELOPMENT' 
elif percent >= 30:
    level = '🟠 FOUNDATIONAL'
else:
    level = '⚫ EXPERIMENTAL'
    
print(f'📊 Confidence Level: {level}')
print()

# Phase 1 quick wins (high-coverage modules)
print('🚀 Phase 1 Quick Wins (>50% coverage):')
quick_wins = []
for file, stats in data['files'].items():
    if 'bb8_core' in file:
        module = file.split('/')[-1].replace('.py', '')
        covered = stats['summary']['covered_lines']
        total = stats['summary']['num_statements'] 
        percent = (covered / total * 100) if total > 0 else 0
        
        if percent > 50:
            target = min(95, percent + 15)  # Aim for +15% or max 95%
            gap = int((target - percent) * total / 100)
            quick_wins.append((module, percent, target, gap, total))
            print(f'  ✅ {module:25} {percent:5.1f}% → {target:5.1f}% (+{gap} lines)')

total_quick_wins = sum(item[3] for item in quick_wins)
print(f'\\n📊 Phase 1 Total: +{total_quick_wins} lines for quick wins')

# Medium-coverage modules for Phase 2
print('\\n🎯 Phase 2 Targets (20-50% coverage):')
for file, stats in data['files'].items():
    if 'bb8_core' in file:
        module = file.split('/')[-1].replace('.py', '')
        covered = stats['summary']['covered_lines']
        total = stats['summary']['num_statements'] 
        percent = (covered / total * 100) if total > 0 else 0
        
        if 20 <= percent <= 50:
            target = 60  # Standard target for medium modules
            gap = int((target - percent) * total / 100)
            print(f'  🟡 {module:25} {percent:5.1f}% → {target:5.1f}% (+{gap} lines)')
"
}

# Function to show improvement opportunities
show_improvement_plan() {
    echo "📋 Phase-Based Improvement Plan"
    echo "================================"
    echo
    echo "🚀 Phase 1: Quick Wins (19.6% → 30%)"
    echo "   Target: High-coverage modules to 80%+"
    echo "   Timeline: 2-3 weeks"
    echo "   Strategy: Expand existing tests, add edge cases"
    echo
    echo "🎯 Phase 2: Medium Coverage (30% → 45%)" 
    echo "   Target: Medium-coverage modules to 60%"
    echo "   Timeline: 3-4 weeks"
    echo "   Strategy: Add integration scenarios, error paths"
    echo
    echo "🏆 Phase 3: Foundation (45% → 60%)"
    echo "   Target: Fix broken tests, add core module coverage"
    echo "   Timeline: 4-6 weeks"
    echo "   Strategy: Systematic test repair, new test suites"
}

# Function to run specific phase
run_phase() {
    local phase=$1
    case $phase in
        "1"|"phase1")
            echo "🚀 Executing Phase 1: Quick Wins"
            run_coverage_assessment
            analyze_coverage
            echo
            echo "💡 Phase 1 Actions:"
            echo "   1. Improve addon_config: Add edge cases, error handling"
            echo "   2. Improve ble_link: Add connection scenarios, timeouts"
            echo "   3. Improve logging_setup: Add configuration tests"
            echo "   4. Complete verify_discovery: Add validation scenarios"
            ;;
        "2"|"phase2")
            echo "🎯 Executing Phase 2: Medium Coverage"
            echo "   Focus: bb8_presence_scanner, ble_bridge, core modules"
            ;;
        "3"|"phase3")
            echo "🏆 Executing Phase 3: Foundation Building"
            echo "   Focus: Fix broken tests, add core module coverage"
            ;;
        *)
            echo "❌ Unknown phase: $phase"
            echo "   Usage: $0 [1|2|3|phase1|phase2|phase3|assess|plan]"
            exit 1
            ;;
    esac
}

# Main command handling
case "${1:-assess}" in
    "assess"|"baseline"|"status")
        run_coverage_assessment
        analyze_coverage
        ;;
    "plan"|"roadmap")
        show_improvement_plan
        ;;
    "1"|"phase1")
        run_phase "1"
        ;;
    "2"|"phase2") 
        run_phase "2"
        ;;
    "3"|"phase3")
        run_phase "3"
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  assess    - Run coverage assessment (default)"
        echo "  plan      - Show improvement roadmap"
        echo "  phase1    - Execute Phase 1 improvements" 
        echo "  phase2    - Execute Phase 2 improvements"
        echo "  phase3    - Execute Phase 3 improvements"
        echo "  help      - Show this help"
        echo
        echo "Current Status:"
        echo "  Baseline: 19.6% coverage (EXPERIMENTAL level)"
        echo "  Target: 60% coverage (OPERATIONAL level)"
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo "   Use '$0 help' for usage information"
        exit 1
        ;;
esac