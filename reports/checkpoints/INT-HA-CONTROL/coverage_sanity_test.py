#!/usr/bin/env python3
"""
Coverage Sanity Test for INT-HA-CONTROL v1.1.1
Validates import structure and basic coverage prerequisites
"""

import subprocess
import sys
from pathlib import Path


def test_import_structure():
    """Test that bb8_core modules can be imported correctly"""
    print("Testing import structure...")

    # Test core module imports
    core_modules = [
        "bb8_core.facade",
        "bb8_core.mqtt_dispatcher",
        "bb8_core.ble_bridge",
        "bb8_core.ble_gateway",
        "bb8_core.bridge_controller",
        "bb8_core.addon_config",
        "bb8_core.logging_setup",
    ]

    failed_imports = []

    for module in core_modules:
        try:
            result = subprocess.run(
                [sys.executable, "-c", f"import {module}; print(f'{module}: OK')"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent.parent / "addon",
            )

            if result.returncode != 0:
                print(f"✗ {module}: FAILED")
                print(f"  Error: {result.stderr.strip()}")
                failed_imports.append(module)
            else:
                print(f"✓ {module}: OK")

        except Exception as e:
            print(f"✗ {module}: EXCEPTION - {e}")
            failed_imports.append(module)

    return len(failed_imports) == 0, failed_imports


def test_pytest_discovery():
    """Test that pytest can discover tests correctly"""
    print("\nTesting pytest test discovery...")

    repo_root = Path(__file__).parent.parent.parent.parent

    # Check test discovery
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )

    if result.returncode != 0:
        print("✗ Pytest test discovery failed")
        print(f"Error: {result.stderr}")
        return False, result.stderr.strip()

    # Parse collection output
    lines = result.stdout.strip().split("\n")
    test_files = [
        line for line in lines if "test session starts" not in line and line.strip()
    ]

    if not test_files:
        print("✗ No tests discovered")
        return False, "No tests found"

    print("✓ Pytest discovered tests successfully")
    print(f"  Found {len(test_files)} test items")

    return True, None


def test_coverage_config():
    """Test coverage configuration"""
    print("\nTesting coverage configuration...")

    repo_root = Path(__file__).parent.parent.parent.parent
    coveragerc_path = repo_root / "addon" / ".coveragerc"

    if not coveragerc_path.exists():
        print(f"✗ Coverage config missing: {coveragerc_path}")
        return False, "Missing .coveragerc"

    try:
        with open(coveragerc_path) as f:
            config_content = f.read()

        if "fail_under = 80" not in config_content:
            print("✗ Coverage threshold not set to 80%")
            return False, "Coverage threshold not 80%"

        if "source = bb8_core" not in config_content:
            print("✗ Coverage source not configured for bb8_core")
            return False, "Coverage source misconfigured"

        print("✓ Coverage configuration valid")
        print("  - 80% threshold set")
        print("  - bb8_core source configured")

        return True, None

    except Exception as e:
        print(f"✗ Error reading coverage config: {e}")
        return False, str(e)


def main():
    """Execute coverage sanity tests"""
    print("INT-HA-CONTROL v1.1.1 Coverage Sanity Test")
    print("=" * 50)

    # Run all sanity checks
    tests = [
        ("Import Structure", test_import_structure),
        ("Pytest Discovery", test_pytest_discovery),
        ("Coverage Config", test_coverage_config),
    ]

    results = {}
    overall_pass = True

    for test_name, test_func in tests:
        try:
            success, error = test_func()
            results[test_name] = {"passed": success, "error": error}

            if not success:
                overall_pass = False

        except Exception as e:
            print(f"✗ {test_name}: EXCEPTION - {e}")
            results[test_name] = {"passed": False, "error": str(e)}
            overall_pass = False

    # Summary
    print("\n" + "=" * 50)
    print("Coverage Sanity Test Results:")

    for test_name, result in results.items():
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {test_name}: {status}")
        if not result["passed"] and result["error"]:
            print(f"    Error: {result['error']}")

    print(f"\nOverall Status: {'PASS' if overall_pass else 'FAIL'}")

    if overall_pass:
        print("✓ All sanity checks passed - coverage measurement ready")
        return 0
    else:
        print("✗ Sanity checks failed - fix issues before coverage analysis")
        return 1


if __name__ == "__main__":
    sys.exit(main())
