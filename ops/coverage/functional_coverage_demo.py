import json

print("=== FUNCTIONAL vs LINE COVERAGE DEMONSTRATION ===")
print("ADR-0039: Gaming-Resistant Metrics")
print()

# Load the functional coverage data with branches
with open("reports/functional_coverage/functional_demo.json") as f:
    cov = json.load(f)

print("📊 COVERAGE COMPARISON:")
line_coverage = cov["totals"]["percent_covered"]
total_branches = cov["totals"]["num_branches"]
covered_branches = cov["totals"]["covered_branches"]
branch_coverage = (covered_branches / total_branches * 100) if total_branches > 0 else 0

print(f"   📏 Line Coverage: {line_coverage:.1f}% (manipulable by formatting)")
print(f"   🌳 Branch Coverage: {branch_coverage:.1f}% (measures actual logic paths)")
print()

print("🎯 CRITICAL INSIGHT:")
print(
    f"   • Branch coverage ({branch_coverage:.1f}%) ≠ Line coverage ({line_coverage:.1f}%)"
)
print("   • Branch coverage measures ACTUAL decision paths tested")
print("   • Line coverage can be inflated by docstrings/formatting")
print()

print("=== MODULE ANALYSIS: Branch vs Line ===")

# Analyze key modules showing branch vs line coverage
key_modules = [
    "bridge_controller",
    "mqtt_dispatcher",
    "facade",
    "ble_bridge",
    "common",
    "ble_gateway",
]

for module_name in key_modules:
    module_key = None
    for file_path in cov["files"].keys():
        if module_name in file_path and "bb8_core" in file_path:
            module_key = file_path
            break

    if module_key:
        data = cov["files"][module_key]["summary"]
        line_pct = data["percent_covered"]

        # Branch data
        if "num_branches" in data and data["num_branches"] > 0:
            branch_pct = data["covered_branches"] / data["num_branches"] * 100
            branch_info = f"{branch_pct:.1f}%"

            # Highlight discrepancies
            if abs(line_pct - branch_pct) > 10:
                status = "⚠️"  # Significant difference
            elif line_pct > 0 and branch_pct > 0:
                status = "✅"  # Both have some coverage
            else:
                status = "🔴"  # No meaningful coverage
        else:
            branch_info = "No branches"
            status = "📝"  # Simple module

        print(
            f"{status} {module_name:20} Line: {line_pct:5.1f}% | Branch: {branch_info:>8}"
        )

print()
print("=== GAMING RESISTANCE DEMONSTRATION ===")
print()

print("EXAMPLE: How line coverage can be gamed:")
print()
print("# BEFORE: Compact (1 line)")
print("def check_status(device): return device.connected and device.battery > 10")
print()
print("# AFTER: Verbose (12 lines - identical logic!)")
print("def check_status(device):")
print('    """Check device status with detailed docs..."""  # +8 doc lines')
print("    # Check connection first")
print("    if not device.connected: return False")
print("    # Check battery level")
print("    return device.battery > 10")
print()

print("📈 Line coverage gaming: 1200% increase (1→12 lines)")
print("🛡️ Branch coverage: IDENTICAL (2 decision points in both)")
print()

print("=== ADR-0039 PROTECTION ===")
print("✅ Function count: Same (1 function)")
print("✅ Branch count: Same (2 decision points)")
print("✅ Test requirements: Identical")
print("❌ Line count: Artificially inflated")
print()

print("=== FUNCTIONAL COVERAGE TARGETS ===")

# Calculate current state
total_files_with_branches = sum(
    1 for f in cov["files"].values() if f["summary"].get("num_branches", 0) > 0
)

print("📈 Current State (Gaming-Resistant):")
print(
    f"   🌳 Branch Coverage: {branch_coverage:.1f}% ({covered_branches}/{total_branches} paths)"
)
print(f"   📁 Testable Modules: {total_files_with_branches} files with decision logic")
print()

print("🎯 Production Readiness Targets:")
print("   🟢 Production: ≥85% function + ≥80% branch coverage")
print("   🟡 Staging: ≥70% function + ≥65% branch coverage")
print("   🟠 Development: ≥50% function + ≥50% branch coverage")
print()

# Improvement guidance
needed_branches = max(0, int(total_branches * 0.80) - covered_branches)
print(f"📊 For 80% branch coverage: Need +{needed_branches} decision paths tested")
print("🎯 Focus areas: Conditional logic, error handling, state validation")
print("🛡️ Immune to: Docstring changes, code formatting, comment density")
