#!/usr/bin/env python3
"""
QA Integration Suite for INT-HA-CONTROL v1.1.1
Executes comprehensive quality assurance pipeline with fail-fast behavior
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description, fail_fast=True):
    """Run command with error handling and fail-fast behavior"""
    print(f"Running: {description}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR: {description} failed (exit code: {result.returncode})")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

        if fail_fast:
            print("FAIL-FAST: Stopping QA pipeline due to failure")
            sys.exit(1)

        return False

    print(f"SUCCESS: {description}")
    if result.stdout.strip():
        print(f"Output: {result.stdout.strip()}")

    return True


def check_mandatory_artifacts():
    """Verify mandatory artifacts exist with fail-fast behavior"""
    print("\nMandatory Artifact Validation:")
    print("=" * 40)

    repo_root = Path(__file__).parent.parent.parent.parent

    mandatory_artifacts = [
        (repo_root / "addon" / "coverage.json", "Coverage report"),
        (repo_root / "reports" / "addon_restart.log", "Addon restart log"),
        (repo_root / "reports" / "mqtt_health_echo.log", "MQTT health log"),
        (repo_root / "reports" / "entity_audit_results.json", "Entity audit results"),
    ]

    missing_count = 0

    for artifact_path, description in mandatory_artifacts:
        if artifact_path.exists():
            print(f"✓ {description}: {artifact_path}")
        else:
            print(f"✗ MISSING: {description}: {artifact_path}")
            missing_count += 1

    if missing_count > 0:
        print(f"\nFAIL-FAST: {missing_count} mandatory artifacts missing")
        sys.exit(1)

    print(f"\n✓ All {len(mandatory_artifacts)} mandatory artifacts validated")


def main():
    """Execute QA integration pipeline with harmonized v1.1.1 requirements"""

    # Determine repository root
    repo_root = Path(__file__).parent.parent.parent.parent
    addon_dir = repo_root / "addon"

    if not addon_dir.exists():
        print(f"ERROR: addon directory not found at {addon_dir}")
        sys.exit(1)

    # Change to addon directory for proper path resolution
    os.chdir(addon_dir)

    print("INT-HA-CONTROL v1.1.1 QA Integration Suite")
    print("=" * 50)
    print(f"Repository root: {repo_root}")
    print(f"Working directory: {addon_dir}")
    print()

    # QA pipeline with fail-fast behavior
    qa_steps = [
        ("python -m pytest --version", "Verify pytest availability", True),
        (
            "python -c 'import bb8_core; print(\"bb8_core import successful\")'",
            "Import validation",
            True,
        ),
        ("PYTHONPATH=/Users/evertappels/actions-runner/Projects/HA-BB8 python -m pytest -xvs", "Unit test execution", True),
        (
            "PYTHONPATH=/Users/evertappels/actions-runner/Projects/HA-BB8 python -m pytest --cov=bb8_core --cov-report=json --cov-fail-under=80",
            "Coverage analysis (80% threshold)",
            True,
        ),
        (
            'python -c \'import json; c=json.load(open("coverage.json")); print(f"Coverage: {c.get("totals", {}).get("percent_covered", 0):.1f}%")\'',
            "Coverage verification",
            True,
        ),
    ]

    results = {}

    for cmd, desc, fail_fast in qa_steps:
        success = run_command(cmd, desc, fail_fast)
        results[desc] = {"success": success, "command": cmd, "fail_fast": fail_fast}

        if not success and fail_fast:
            # Should not reach here due to sys.exit(1) in run_command
            break

    # Check mandatory artifacts
    check_mandatory_artifacts()

    # Generate results summary
    results_dir = repo_root / "reports"
    results_dir.mkdir(exist_ok=True)
    results_file = results_dir / "qa_results.json"

    summary = {
        "int_ha_control_version": "v1.1.1",
        "execution_mode": "fail_fast",
        "total_steps": len(qa_steps),
        "passed_steps": sum(1 for r in results.values() if r["success"]),
        "steps": results,
        "mandatory_artifacts_validated": True,
    }

    with open(results_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nQA results saved to: {results_file}")

    # Final status
    all_passed = all(r["success"] for r in results.values())

    if all_passed:
        print("\n" + "=" * 50)
        print("QA Integration Suite: PASSED ✓")
        print("All quality gates satisfied with 80% coverage threshold")
        sys.exit(0)
    else:
        print("\n" + "=" * 50)
        print("QA Integration Suite: FAILED ✗")
        print("Quality gates not satisfied")
        sys.exit(1)


if __name__ == "__main__":
    main()

CHECKPOINT_DIR = "/Users/evertappels/Projects/HA-BB8/reports/checkpoints/INT-HA-CONTROL"
WORKSPACE_ROOT = "/Users/evertappels/Projects/HA-BB8"


def run_command(cmd, cwd=None):
    """Run shell command and return result"""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=300
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": cmd,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "Command timed out after 300 seconds",
            "command": cmd,
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -2,
            "stdout": "",
            "stderr": str(e),
            "command": cmd,
        }


def run_pytest_with_coverage():
    """Run pytest with coverage reporting"""
    print("=== Running pytest with coverage ===")

    # Activate venv and run pytest with coverage
    pytest_cmd = f"""
    source .venv/bin/activate && \\
    python -m pytest --cov=addon/bb8_core \\
                     --cov-report=json:{CHECKPOINT_DIR}/coverage.json \\
                     --cov-report=term-missing \\
                     --maxfail=3 \\
                     -v \\
                     addon/tests/
    """

    result = run_command(pytest_cmd, cwd=WORKSPACE_ROOT)

    # Parse coverage data - FAIL if missing or lacks totals
    coverage_data = {
        "coverage_percent": 0,
        "missing_lines": 0,
        "covered_lines": 0,
        "total_lines": 0,
    }
    coverage_file = f"{CHECKPOINT_DIR}/coverage.json"

    if not Path(coverage_file).exists():
        print("FAIL: Missing mandatory coverage.json file")
        return {
            "pytest_result": result,
            "coverage_data": coverage_data,
            "coverage_pass": False,
            "coverage_error": "coverage.json missing",
        }

    try:
        with open(coverage_file) as f:
            coverage_json = json.load(f)

        # Calculate overall coverage
        if "files" not in coverage_json:
            print("FAIL: coverage.json lacks 'files' section")
            return {
                "pytest_result": result,
                "coverage_data": coverage_data,
                "coverage_pass": False,
                "coverage_error": "invalid coverage.json format",
            }

        total_lines = sum(
            f["summary"]["num_statements"] for f in coverage_json["files"].values()
        )
        covered_lines = sum(
            f["summary"]["covered_lines"] for f in coverage_json["files"].values()
        )

        if total_lines > 0:
            coverage_percent = (covered_lines / total_lines) * 100
            coverage_data.update(
                {
                    "coverage_percent": round(coverage_percent, 2),
                    "missing_lines": total_lines - covered_lines,
                    "covered_lines": covered_lines,
                    "total_lines": total_lines,
                }
            )
        else:
            coverage_data["total_lines"] = 0
            print("WARNING: Zero total lines in coverage report")

    except Exception as e:
        print(f"FAIL: Error parsing coverage data: {e}")
        return {
            "pytest_result": result,
            "coverage_data": coverage_data,
            "coverage_pass": False,
            "coverage_error": str(e),
        }

    return {
        "pytest_result": result,
        "coverage_data": coverage_data,
        "coverage_pass": coverage_data["coverage_percent"] >= 80.0,
    }


def load_checkpoint_results():
    """Load results from previous checkpoint tests"""
    results = {}

    # Mandatory artifacts for PASS - updated list
    mandatory_artifacts = [
        "config_env_validation.json",
        "coverage.json",
        # Optional runtime artifacts (marked as pending if missing)
        "mqtt_roundtrip.log",
        "mqtt_persistence.log",
        "entity_persistence_test.log",
        "entity_audit.json",
        "discovery_ownership_check.txt",
        "discovery_ownership_audit.json",
        "led_entity_schema_validation.json",
        "device_block_audit.log",
        "addon_restart.log",  # From P0 stability window
    ]

    missing_mandatory = []

    for artifact_file in mandatory_artifacts:
        file_path = Path(CHECKPOINT_DIR) / artifact_file
        if file_path.exists():
            try:
                with open(file_path) as f:
                    if artifact_file.endswith(".json"):
                        results[artifact_file.replace(".json", "")] = json.load(f)
                    else:  # .log files that might contain JSON
                        content = f.read()
                        try:
                            results[artifact_file.replace(".log", "")] = json.loads(
                                content
                            )
                        except json.JSONDecodeError:
                            results[artifact_file.replace(".log", "")] = {
                                "raw_content": content
                            }
            except Exception as e:
                results[artifact_file] = {"error": str(e)}
        else:
            # Track missing artifacts
            missing_mandatory.append(artifact_file)
            results[artifact_file.replace(".json", "").replace(".log", "")] = {
                "missing": True
            }

    # Store missing artifacts info for reporting
    results["_missing_artifacts"] = missing_mandatory
    return results


def aggregate_integration_results():
    """Aggregate all integration test results"""
    checkpoint_results = load_checkpoint_results()

    # Define acceptance criteria mappings
    acceptance_criteria = {
        "p0_stability": {
            "description": "typeerror_count==0 && coroutine_error_count==0",
            "status": "PENDING_OPERATOR_EXECUTION",  # Requires manual addon restart
            "details": "P0 stability monitoring requires Home Assistant addon restart",
        },
        "mqtt_health_echo": {
            "description": "ping→echo ≤1s SLA",
            "status": "FRAMEWORK_READY",
            "details": "Health echo test framework created, requires runtime execution",
        },
        "broker_restart_persistence": {
            "description": "Entities restored ≤10s after broker and HA Core restart",
            "status": "PENDING_OPERATOR_EXECUTION",
            "details": "Requires broker restart in production environment",
        },
        "discovery_ownership": {
            "description": "duplicates_detected==0",
            "status": "UNKNOWN",
            "details": "Discovery ownership audit framework created",
        },
        "led_entity_alignment": {
            "description": "All toggle cases PASS and schema validation PASS",
            "status": "UNKNOWN",
            "details": "LED alignment test framework created",
        },
        "coverage_requirement": {
            "description": "total coverage ≥80%",
            "status": "UNKNOWN",
            "details": "Will be determined by pytest execution",
        },
    }

    # Update status from checkpoint results
    if "discovery_ownership_audit" in checkpoint_results:
        audit_data = checkpoint_results["discovery_ownership_audit"]
        if "compliance_status" in audit_data:
            compliance = audit_data["compliance_status"]
            acceptance_criteria["discovery_ownership"]["status"] = (
                "PASS" if compliance.get("overall_pass") else "FAIL"
            )

    if "led_entity_schema_validation" in checkpoint_results:
        led_data = checkpoint_results["led_entity_schema_validation"]
        if "compliance_status" in led_data:
            compliance = led_data["compliance_status"]
            acceptance_criteria["led_entity_alignment"]["status"] = (
                "PASS" if compliance.get("overall_pass") else "FAIL"
            )

    return {
        "integration_results": checkpoint_results,
        "acceptance_criteria": acceptance_criteria,
    }


def generate_qa_report():
    """Generate comprehensive QA report with binary verdicts"""
    print("=== Generating QA Report ===")

    # Run pytest with coverage
    pytest_results = run_pytest_with_coverage()

    # Aggregate integration results
    integration_data = aggregate_integration_results()

    # Update coverage acceptance criteria
    integration_data["acceptance_criteria"]["coverage_requirement"]["status"] = (
        "PASS" if pytest_results["coverage_pass"] else "FAIL"
    )
    integration_data["acceptance_criteria"]["coverage_requirement"][
        "details"
    ] = f"Coverage: {pytest_results['coverage_data']['coverage_percent']:.1f}%"

    # Generate binary verdicts with strict enforcement
    binary_verdicts = {}
    overall_pass = True
    missing_artifacts = integration_data["integration_results"].get(
        "_missing_artifacts", []
    )

    # Check for missing mandatory artifacts
    if missing_artifacts:
        print(f"FAIL: Missing mandatory artifacts: {missing_artifacts}")
        overall_pass = False

    for criterion_name, criterion_data in integration_data[
        "acceptance_criteria"
    ].items():
        status = criterion_data["status"]
        verdict = status == "PASS"

        binary_verdicts[criterion_name] = {
            "pass": verdict,
            "status": status,
            "description": criterion_data["description"],
            "details": criterion_data["details"],
        }

        # Strict enforcement: FAIL if any criterion is FAIL
        if status == "FAIL":
            overall_pass = False
        # Don't count pending executions as failures, but they prevent overall PASS
        elif status in ["PENDING_OPERATOR_EXECUTION", "FRAMEWORK_READY", "UNKNOWN"]:
            # These are not failures, but prevent overall PASS until executed
            pass

    # Only print "Overall Pass: true" when all acceptances are PASS
    strict_pass = all(
        v["status"] == "PASS" for v in integration_data["acceptance_criteria"].values()
    )
    if not strict_pass:
        overall_pass = False

    # Aggregate logs for MQTT operations
    log_files = ["mqtt_roundtrip.log", "mqtt_persistence.log"]
    mqtt_logs = {}
    for log_file in log_files:
        log_path = Path(CHECKPOINT_DIR) / log_file
        if log_path.exists():
            mqtt_logs[log_file] = log_path.read_text()
        else:
            mqtt_logs[log_file] = f"Log file not found: {log_file}"

    # Final QA report
    qa_report = {
        "qa_metadata": {
            "timestamp": datetime.now().isoformat(),
            "directive": "INT-HA-CONTROL v1.1",
            "workspace_root": WORKSPACE_ROOT,
            "checkpoint_dir": CHECKPOINT_DIR,
        },
        "pytest_execution": {
            "success": pytest_results["pytest_result"]["success"],
            "coverage_percent": pytest_results["coverage_data"]["coverage_percent"],
            "coverage_pass": pytest_results["coverage_pass"],
            "covered_lines": pytest_results["coverage_data"]["covered_lines"],
            "total_lines": pytest_results["coverage_data"]["total_lines"],
        },
        "integration_tests": integration_data["integration_results"],
        "binary_verdicts": binary_verdicts,
        "mqtt_logs": mqtt_logs,
        "summary": {
            "total_criteria": len(binary_verdicts),
            "passed_criteria": sum(1 for v in binary_verdicts.values() if v["pass"]),
            "failed_criteria": sum(
                1 for v in binary_verdicts.values() if v["status"] == "FAIL"
            ),
            "pending_criteria": sum(
                1
                for v in binary_verdicts.values()
                if v["status"]
                in ["PENDING_OPERATOR_EXECUTION", "FRAMEWORK_READY", "UNKNOWN"]
            ),
            "overall_pass": overall_pass,
            "coverage_threshold_met": pytest_results["coverage_pass"],
        },
        "escalation_required": not overall_pass or not pytest_results["coverage_pass"],
    }

    # Write QA report
    with open(f"{CHECKPOINT_DIR}/qa_report.json", "w") as f:
        f.write(json.dumps(qa_report, indent=2))

    return qa_report


def main():
    qa_report = generate_qa_report()

    # Summary output
    summary = qa_report["summary"]
    print("\n=== QA Report Summary ===")
    print(
        f"Coverage: {qa_report['pytest_execution']['coverage_percent']:.1f}% (≥80% required)"
    )
    print(f"Coverage PASS: {qa_report['pytest_execution']['coverage_pass']}")
    print(f"Criteria passed: {summary['passed_criteria']}/{summary['total_criteria']}")
    print(f"Criteria failed: {summary['failed_criteria']}")
    print(f"Criteria pending: {summary['pending_criteria']}")
    print(f"Overall PASS: {summary['overall_pass']}")
    print(f"Escalation required: {qa_report['escalation_required']}")

    print("\n=== Binary Verdicts ===")
    for criterion, verdict in qa_report["binary_verdicts"].items():
        status_symbol = (
            "✓" if verdict["pass"] else "✗" if verdict["status"] == "FAIL" else "⏳"
        )
        print(
            f"{status_symbol} {criterion}: {verdict['status']} - {verdict['details']}"
        )

    # Return appropriate exit code
    if qa_report["escalation_required"]:
        print("\n⚠️  ESCALATION REQUIRED: Coverage <80% or acceptance criteria failed")
        return 2
    elif summary["pending_criteria"] > 0:
        print(
            f"\n⏳ PENDING: {summary['pending_criteria']} criteria require operator execution"
        )
        return 1
    else:
        print("\n✅ ALL CRITERIA PASSED")
        return 0


if __name__ == "__main__":
    exit(main())
