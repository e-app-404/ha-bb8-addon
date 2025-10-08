#!/usr/bin/env python3
"""
QG-TEST-80 Phase-4: Targeted Unit Test Generation
Generate high-yield unit tests to reach 60% coverage threshold.
"""

import json
import sys
from pathlib import Path

def load_coverage_data(coverage_json_path: Path):
    """Load and analyze coverage data."""
    try:
        with open(coverage_json_path, 'r') as f:
            data = json.load(f)
        
        print(f"✓ Loaded coverage data from {coverage_json_path}")
        
        # Extract summary
        summary = data.get('totals', {})
        current_percent = summary.get('percent_covered', 0)
        covered_lines = summary.get('covered_lines', 0)
        missing_lines = summary.get('missing_lines', 0)
        total_lines = covered_lines + missing_lines
        
        print(f"📊 Current Coverage: {current_percent:.1f}% ({covered_lines}/{total_lines} lines)")
        
        return data, current_percent, total_lines
        
    except FileNotFoundError:
        print(f"❌ Coverage data not found at {coverage_json_path}")
        return None, 0, 0
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in coverage data: {e}")
        return None, 0, 0

def identify_high_yield_targets(coverage_data, target_percent=60.0):
    """Identify files with best coverage ROI for testing."""
    files = coverage_data.get('files', {})
    targets = []
    
    for file_path, file_data in files.items():
        if 'addon/bb8_core' not in file_path:
            continue  # Focus on core addon modules
            
        summary = file_data.get('summary', {})
        covered = summary.get('covered_lines', 0)
        missing = summary.get('missing_lines', 0)
        total = covered + missing
        
        if total == 0:
            continue
            
        current_percent = (covered / total) * 100
        potential_gain = missing  # Lines we could potentially cover
        
        # Calculate ROI: prefer files with good potential and reasonable complexity
        if potential_gain > 5 and current_percent < 80:  # Don't over-optimize already good files
            roi_score = potential_gain * (1 + (current_percent / 100))  # Favor partially covered files
            
            targets.append({
                'file': file_path,
                'current_percent': current_percent,
                'potential_gain': potential_gain,
                'roi_score': roi_score,
                'missing_lines': file_data.get('missing_lines', [])
            })
    
    # Sort by ROI score
    targets.sort(key=lambda x: x['roi_score'], reverse=True)
    
    print(f"\n🎯 High-Yield Test Targets (Top 8):")
    print("=" * 60)
    for i, target in enumerate(targets[:8]):
        file_name = Path(target['file']).name
        print(f"{i+1:2d}. {file_name:<25} {target['current_percent']:5.1f}% (+{target['potential_gain']:2d} lines, ROI:{target['roi_score']:5.1f})")
    
    return targets[:8]  # Return top 8 targets

def generate_test_templates(targets):
    """Generate test file templates for high-yield targets."""
    test_templates = []
    
    for target in targets:
        file_path = target['file']
        module_name = Path(file_path).stem
        missing_lines = target['missing_lines']
        
        # Generate test template
        template = f"""
# Test template for {module_name}.py
# Target: +{target['potential_gain']} lines coverage
# Missing lines: {missing_lines}

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add addon to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent))

from addon.bb8_core.{module_name} import *

class Test{module_name.title().replace('_', '')}:
    \"\"\"Unit tests for {module_name} module.\"\"\"
    
    def test_{module_name}_basic_functionality(self):
        \"\"\"Test basic functionality.\"\"\"
        # TODO: Add specific tests for missing lines: {missing_lines[:5]}
        pass
    
    def test_{module_name}_error_handling(self):
        \"\"\"Test error handling paths.\"\"\"
        # TODO: Target error handling lines
        pass
    
    def test_{module_name}_edge_cases(self):
        \"\"\"Test edge cases and boundary conditions.\"\"\"
        # TODO: Target edge case lines
        pass

# Additional test methods would be generated based on missing_lines analysis
"""
        
        test_templates.append({
            'module': module_name,
            'template': template,
            'target_lines': missing_lines
        })
    
    return test_templates

def main():
    """Execute Phase-4 targeted unit test generation."""
    print("�� QG-TEST-80 Phase-4: Targeted Unit Test Generation")
    print("=" * 60)
    
    # Step 1: Load coverage data
    coverage_json = Path("reports/checkpoints/QG-TEST-80/coverage.json")
    coverage_data, current_percent, total_lines = load_coverage_data(coverage_json)
    
    if not coverage_data:
        print("❌ Cannot proceed without coverage data")
        return 1
    
    # Step 2: Calculate coverage gap
    target_percent = 60.0
    gap_percent = target_percent - current_percent
    gap_lines = int((gap_percent / 100) * total_lines)
    
    print(f"📈 Coverage Gap: {gap_percent:.1f}% (~{gap_lines} lines needed)")
    
    if current_percent >= target_percent:
        print(f"✅ Already at target! Current: {current_percent:.1f}% >= {target_percent}%")
        return 0
    
    # Step 3: Identify high-yield targets
    targets = identify_high_yield_targets(coverage_data, target_percent)
    
    if not targets:
        print("❌ No suitable test targets found")
        return 1
    
    # Step 4: Generate test templates
    print(f"\n📝 Generating Test Templates...")
    templates = generate_test_templates(targets)
    
    # Step 5: Create test files (preview mode)
    print(f"\n🎨 Test Template Preview:")
    print("=" * 60)
    
    for template in templates[:3]:  # Show first 3 templates
        print(f"\n## {template['module']}.py test template:")
        print(template['template'][:300] + "...")
    
    # Step 6: Calculate potential coverage gain
    total_potential = sum(t['potential_gain'] for t in targets)
    estimated_percent = current_percent + (total_potential / total_lines * 100)
    
    print(f"\n📊 Estimated Coverage After Tests:")
    print(f"   Current: {current_percent:.1f}%")
    print(f"   Potential: +{total_potential} lines ({total_potential/total_lines*100:.1f}%)")
    print(f"   Estimated: {estimated_percent:.1f}%")
    
    if estimated_percent >= target_percent:
        print(f"✅ Should reach {target_percent}% target!")
    else:
        print(f"⚠️  May not reach {target_percent}% target - need more coverage strategies")
    
    print(f"\n🎯 Phase-4 Analysis Complete!")
    print("Next: Implement actual unit tests for high-yield targets")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
