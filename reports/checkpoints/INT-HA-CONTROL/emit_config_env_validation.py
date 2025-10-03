#!/usr/bin/env python3
"""
Config Environment Validation for INT-HA-CONTROL
Validates default configuration values as per acceptance criteria
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

def validate_config_defaults():
    """Validate required config defaults"""
    
    # Expected defaults per INT-HA-CONTROL acceptance criteria
    expected_defaults = {
        "MQTT_BASE": "bb8",
        "REQUIRE_DEVICE_ECHO": "1", 
        "PUBLISH_LED_DISCOVERY": "0"
    }
    
    validation_results = {
        "validation_metadata": {
            "timestamp": datetime.now().isoformat(),
            "validator": "emit_config_env_validation.py",
            "acceptance_criteria": "MQTT_BASE=bb8, REQUIRE_DEVICE_ECHO=1, PUBLISH_LED_DISCOVERY=0"
        },
        "environment_validation": {},
        "compliance_status": {
            "all_defaults_correct": True,
            "violations": []
        }
    }
    
    # Check environment variables
    for key, expected_value in expected_defaults.items():
        actual_value = os.environ.get(key, "NOT_SET")
        is_correct = actual_value == expected_value
        
        validation_results["environment_validation"][key] = {
            "expected": expected_value,
            "actual": actual_value,
            "correct": is_correct
        }
        
        if not is_correct:
            validation_results["compliance_status"]["all_defaults_correct"] = False
            validation_results["compliance_status"]["violations"].append({
                "variable": key,
                "expected": expected_value,
                "actual": actual_value
            })
    
    # Overall pass/fail
    validation_results["overall_pass"] = validation_results["compliance_status"]["all_defaults_correct"]
    
    return validation_results

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate config environment defaults")
    parser.add_argument("--out", required=True, help="Output JSON file path")
    args = parser.parse_args()
    
    print("[2025-10-03T19:45:00] CONFIG_VALIDATION_START: Validating environment defaults")
    
    try:
        results = validate_config_defaults()
        
        # Write results
        with open(args.out, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"[2025-10-03T19:45:01] VALIDATION_COMPLETE: Results written to {args.out}")
        
        # Print summary
        print("\n=== Config Environment Validation Summary ===")
        for key, result in results["environment_validation"].items():
            status = "✓" if result["correct"] else "✗"
            print(f"{status} {key}: {result['actual']} (expected: {result['expected']})")
        
        print(f"Overall PASS: {results['overall_pass']}")
        
        # Exit with appropriate code
        sys.exit(0 if results["overall_pass"] else 1)
        
    except Exception as e:
        print(f"[2025-10-03T19:45:01] ERROR: Config validation failed: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()