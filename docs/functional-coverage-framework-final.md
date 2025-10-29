---
id: "FRAMEWORK-COVERAGE-01"
title: "HA-BB8 Functional Coverage Framework: Gaming-Resistant Metrics"
authors: "HA-BB8 Engineering Team"
source: ""
slug: "functional-coverage-framework"
type: "guide"
tags: ["coverage", "testing", "metrics", "ci", "ha-bb8"]
date: "2025-10-01"
last_updated: "2024-06-09"
url: ""
related: ""
adr: "ADR-0039"
---

## Executive Summary: The Line Coverage Problem

Traditional coverage measurement suffers from a fundamental flaw: **line-based coverage is easily gamed through cosmetic changes** that do not improve test quality or operational confidence.

### The Gaming Problem Demonstrated

**Example:**

```python
# Compact Version (1 line)
def check_status(device): return device.connected and device.battery > 10

# Verbose Version (12 lines - IDENTICAL FUNCTIONALITY)
def check_status(device):
    """
    Check device operational status with comprehensive documentation
    explaining the validation logic for device connectivity and
    battery level assessment according to operational requirements.
    """
    # First check connection status
    if not device.connected:
        return False
    # Then validate battery level
    return device.battery > 10
```

- **Line Coverage Impact:** 1200% increase (1 → 12 lines)
- **Actual Functional Difference:** **None** (identical logic and test requirements)

### Current State Analysis

**Line vs Branch Coverage Comparison:**

- **Line Coverage:** 14.7% (easily manipulated by formatting/docstrings)
- **Branch Coverage:** 5.5% (measures actual decision paths tested)

| Module           | Line Coverage | Branch Coverage | Gaming Vulnerability         |
|------------------|--------------|-----------------|-----------------------------|
| mqtt_dispatcher  | 12.0%        | 0.0%            | ⚠️ Highly gameable           |
| facade           | 14.3%        | 0.0%            | ⚠️ Highly gameable           |
| ble_bridge       | 21.2%        | 0.0%            | ⚠️ Highly gameable           |
| common           | 100.0%       | 100.0%          | ✅ Consistent                |

**Key Finding:** Most modules show significant discrepancy between line and branch coverage, indicating that **line coverage can be artificially inflated** without testing actual logic paths.

## ADR-0039: Gaming-Resistant Framework

### Primary Metrics (Supersedes Line Coverage)

#### 1. Function Coverage (70% weight)

```text
Function Coverage % = (Executed Functions) / (Total Functions) × 100
```

- Immune to code formatting, docstring verbosity, comment density
- Measures actual API surface area tested
- Focuses on public methods and core business logic functions

#### 2. Branch Coverage (20% weight)

```text
Branch Coverage % = (Executed Decision Paths) / (Total Decision Paths) × 100
```

- Immune to line expansion, style changes, documentation additions
- Measures conditional logic, error handling, state transitions
- Focuses on if/else paths, try/except blocks, async flows

#### 3. Behavioral Coverage (10% weight)

- Integration scenarios: end-to-end operational workflows
- Error conditions: exception handling and recovery paths
- Edge cases: boundary conditions and invalid inputs
- State management: device lifecycle and connection states

### Anti-Gaming Enforcement

**Prohibited Practices (ADR-0039):**

- ❌ Docstring manipulation (verbose vs terse documentation)
- ❌ Code formatting games (single-line vs multi-line expressions)
- ❌ Comment padding (adding/removing explanatory comments)
- ❌ Style inflation (compact vs expanded syntax patterns)

**Gaming Detection:**

- Function count validation: must remain stable for equivalent logic
- Branch count verification: decision points cannot be artificially increased
- Test quality audits: coverage must correlate with operational confidence

### Operational Confidence Thresholds

| Function Coverage | Branch Coverage | Confidence Level   | Deployment Risk |
|-------------------|----------------|-------------------|----------------|
| ≥85%              | ≥80%           | 🟢 PRODUCTION      | Low            |
| 70–84%            | 65–79%         | 🟡 STAGING         | Moderate       |
| 50–69%            | 50–64%         | 🟠 DEVELOPMENT     | High           |
| 30–49%            | 30–49%         | 🔴 FOUNDATIONAL    | Very High      |
| <30%              | <30%           | ⚫ EXPERIMENTAL    | Unacceptable   |

**Current Status:** ⚫ EXPERIMENTAL (5.5% branch coverage)

### Implementation Strategy

#### Phase 1: Function Coverage Audit

- Identify untested functions in critical modules (e.g., bridge_controller: 22 functions)
- Prioritize public APIs and error handling functions
- Target quick wins in well-structured modules

#### Phase 2: Branch Coverage Enhancement

- Enable branch coverage in CI/CD pipeline (`--cov-branch`)
- Focus on decision logic and exception handling paths
- Test error scenarios and state transitions

#### Phase 3: Integration Scenarios

- End-to-end workflows (MQTT ↔ BLE coordination)
- Fault injection testing (network failures, device disconnections)
- Real operational patterns (device discovery, command execution)

### Measurement Commands

**Primary Assessment (ADR-0039):**

```bash
./ops/qa/functional_coverage_assessment.sh
```

**Detailed Analysis:**

```bash
PYTHONPATH="$PWD" python -m pytest addon/tests/ \
    --cov=addon/bb8_core \
    --cov-branch \
    --cov-report=json:functional_coverage.json \
    --cov-report=term-missing
```

### Success Metrics

**Current State (October 2025):**

- Function Coverage: ~10% (estimated from line coverage)
- Branch Coverage: 5.5% (37/668 decision paths)
- Testable Modules: 31 files with decision logic
- **Need:** +497 decision paths for 80% branch coverage

**Improvement Targets:**

1. Quick Wins: Test remaining branches in high-coverage modules (common, ble_gateway)
2. Critical Focus: bridge_controller, mqtt_dispatcher, facade, ble_bridge (0% branch coverage)
3. Integration: Cross-module scenarios and error recovery paths

### Framework Benefits

**Gaming Resistance:**

- ✅ Function metrics: immune to formatting manipulation
- ✅ Branch analysis: measures actual logic complexity
- ✅ Behavioral focus: tests real operational scenarios
- ✅ Quality correlation: links coverage to deployment confidence

**Operational Alignment:**

- Coverage improvements translate directly to reduced deployment risk
- Test requirements focus on actual business logic and error handling
- Progress measurement reflects genuine operational reliability gains
- Anti-gaming policies prevent statistical manipulation

## Conclusion

The **ADR-0039 Functional Coverage Framework** eliminates the perverse incentives of line-based measurement by focusing on:

1. Functions and methods executed (not lines of code)
2. Decision paths tested (not cosmetic formatting)
3. Operational scenarios validated (not documentation verbosity)
4. Deployment confidence correlation (not statistical manipulation)

This framework ensures that coverage improvements reflect **genuine increases in operational reliability** and **reduced deployment risk**, rather than cosmetic code changes that provide no real value.

**The line coverage gaming problem is solved.**

---

**Framework:** ADR-0039 Functional Coverage (Gaming-Resistant)
**Status:** Active (Supersedes ADR-0038 Line Coverage)
**Review:** Quarterly effectiveness assessment
**Compliance:** Mandatory for all coverage measurement
