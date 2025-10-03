---
status: accepted
date: 2025-10-01
deciders: Copilot Claude, Strategos
consulted: QA Team, Operations
informed: Development Team, Stakeholders
---

# ADR-0038: Test Coverage Measurement Framework

## Context and Problem Statement

The project has been using inconsistent and misleading coverage measurements that don't reflect operational reality or deployment confidence. We need a consistent, future-proof measurement framework that:

1. Provides meaningful metrics tied to operational reliability
2. Avoids statistical manipulation (like artificial baseline amplification)
3. Guides effective development priorities
4. Supports mission success evaluation

**Current State Analysis (October 2025):**
- **Total Codebase**: 3,466 executable lines across 32 core modules
- **Actual Baseline**: 49.7% coverage (1,721/3,466 lines)
- **Critical Modules**: 47.8% coverage (513/1,073 lines) - bridge_controller, mqtt_dispatcher, facade, ble_bridge
- **Support Modules**: 100.0% coverage (129/129 lines) - utilities, types, common functions
- **Test Infrastructure**: 20+ test files with 200+ test cases

## Decision

### Coverage Measurement Framework

#### 1. **Baseline Definition**
**Current Operational Baseline: 49.7%** (October 2025)
- Based on comprehensive test suite execution against bb8_core modules
- Excludes failing tests that don't provide meaningful coverage
- Represents actual deployment-ready code coverage
- **NO artificial baseline manipulation** - this is our real starting point

#### 2. **Measurement Methodology**

**Coverage Command:**
```bash
PYTHONPATH="$PWD" python -m pytest addon/tests/ \
    --ignore=addon/tests/test_*_complete.py \  # Exclude failing integration attempts
    --cov=addon/bb8_core \
    --cov-report=json:coverage.json \
    --cov-report=term-missing
```

**Inclusion Criteria:**
- All `addon/bb8_core/*.py` modules (production code)
- Tests that execute successfully and provide meaningful coverage
- Both unit and integration tests that validate operational behavior

**Exclusion Criteria:**
- Test files themselves (`test_*.py`)
- Failing tests that don't execute code paths
- Mock/stub implementations without business logic
- Development/debugging utilities not used in production

#### 3. **Threshold Framework**

**Mission-Critical Thresholds:**

| Level | Coverage | Operational Confidence | Deployment Risk |
|-------|----------|----------------------|-----------------|
| **CRITICAL** | ≥80% | Production Ready | Low |
| **OPERATIONAL** | 60-79% | Staging Ready | Moderate |
| **DEVELOPMENT** | 40-59% | Feature Complete | High |
| **FOUNDATIONAL** | 20-39% | Basic Functionality | Very High |
| **EXPERIMENTAL** | <20% | Prototype Only | Unacceptable |

**Current Status**: DEVELOPMENT (49.7%)

#### 4. **Module Prioritization Strategy**

**Tier 1 - Critical Operational Modules (Target: 85%+)**
- `bridge_controller`: Main orchestration (304 lines, 41.1% → 85%)
- `mqtt_dispatcher`: MQTT communication (408 lines, 60.8% → 85%)
- `facade`: Public API (201 lines, 50.2% → 85%)  
- `ble_bridge`: Device interface (160 lines, 24.4% → 85%)

**Tier 2 - Supporting Modules (Target: 75%+)**
- `echo_responder`: Health monitoring (258 lines, 65.1% → 75%)
- `bb8_presence_scanner`: Device detection (428 lines, 65.0% → 75%)
- `auto_detect`: Device discovery (288 lines, 29.5% → 75%)

**Tier 3 - Utility Modules (Current: 100%)**
- Already achieved target coverage for utilities and types

#### 5. **Coverage Composition Requirements**

**Total Coverage Calculation:**
```
Coverage % = (Covered Lines in bb8_core) / (Total Lines in bb8_core) * 100
```

**Quality Gates:**
- **Line Coverage**: Primary metric for execution paths
- **Branch Coverage**: Secondary metric for decision logic (when available)
- **Function Coverage**: Tertiary metric for API surface area

**Anti-Patterns Prohibited:**
- Artificial baseline manipulation
- Excluding core modules to inflate percentages  
- Counting test files in coverage calculations
- Using failing tests to claim coverage progress

### 6. **Improvement Framework**

**Phase 1: Quick Wins (49.7% → 65%)**
Target: +257 lines in high-coverage modules
- mqtt_dispatcher: 60.8% → 80% (+78 lines)
- bb8_presence_scanner: 65.0% → 80% (+64 lines)
- facade: 50.2% → 80% (+59 lines)
- echo_responder: 65.1% → 80% (+38 lines)
- ble_link: 66.9% → 80% (+16 lines)
- logging_setup: 78.0% → 80% (+2 lines)

**Phase 2: Critical Infrastructure (65% → 75%)**
Target: +347 lines in critical modules
- bridge_controller: 41.1% → 75% (+103 lines)
- ble_bridge: 24.4% → 75% (+81 lines)
- auto_detect: 29.5% → 75% (+131 lines)
- Zero-coverage modules: Basic test creation (+32 lines)

**Phase 3: Production Ready (75% → 85%)**
Target: +347 lines completing critical modules
- All Tier 1 modules to 85%
- All Tier 2 modules to 75%
- Integration test scenarios

### 7. **Measurement Cadence**

**Continuous (Per PR):**
- Coverage must not decrease below current baseline
- New code must have ≥80% coverage
- Critical module changes require coverage improvement

**Weekly (Sprint Reviews):**
- Progress tracking against phase targets
- Module-level coverage analysis
- Test quality assessment

**Monthly (Release Cycles):**
- Overall coverage trend analysis
- Phase completion evaluation  
- Framework effectiveness review

### 8. **Success Metrics**

**Primary KPIs:**
1. **Overall Coverage Trend**: Month-over-month improvement
2. **Critical Module Coverage**: Average coverage of Tier 1 modules
3. **Deployment Confidence**: Correlation between coverage and production issues
4. **Test Effectiveness**: Coverage quality vs. quantity

**Mission Success Correlation:**
- 49.7% (current): Development confidence
- 65% (Phase 1): Staging deployment confidence  
- 75% (Phase 2): Limited production confidence
- 85% (Phase 3): Full production confidence

## Consequences

### Positive
- **Realistic Progress Tracking**: No more statistical manipulation
- **Operational Focus**: Coverage aligns with deployment confidence
- **Clear Priorities**: Module-based improvement strategy
- **Sustainable Growth**: Achievable phase-based targets

### Negative
- **Lower Starting Point**: 49.7% vs. inflated baselines
- **Honest Assessment**: May reveal gaps in test infrastructure
- **Resource Requirements**: Significant testing effort needed for 85% target

### Risks
- **Development Velocity**: Coverage requirements may slow feature development
- **Test Quality vs. Quantity**: Risk of low-value tests to meet percentages
- **Maintenance Overhead**: Test suite maintenance complexity

## Implementation

### Immediate Actions (Week 1)
1. Update CI/CD pipelines with new coverage measurement
2. Establish coverage reporting dashboard
3. Communicate new framework to development team

### Phase 1 Execution (Weeks 2-6)
1. Focus on quick-win modules with existing high coverage
2. Improve test quality for modules at 60%+ coverage
3. Target 65% overall coverage milestone

### Tooling Requirements
- **Coverage Tool**: pytest-cov with JSON reporting
- **Reporting**: Coverage.py with HTML reports for analysis
- **CI Integration**: Fail builds on coverage regression
- **Dashboard**: Real-time coverage tracking by module

## Compliance and Governance

This ADR establishes **mandatory coverage measurement standards** for the HA-BB8 project. All future coverage discussions, reporting, and improvement efforts must use this framework.

**Deviation Approval**: Changes to this framework require explicit ADR amendment with technical leadership approval.

**Review Cycle**: Framework effectiveness reviewed quarterly with potential adjustments based on operational experience.

TOKEN_BLOCK_BEGIN_DO_NOT_EDIT
ADR-0038-test-coverage-measurement-framework:latest:49.7-baseline-operational-reality:mission-aligned-thresholds:phase-based-improvement:no-statistical-manipulation
TOKEN_BLOCK_END_DO_NOT_EDIT