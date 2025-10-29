---
status: supersedes
decision: '### Functional Coverage Framework.'
date: 2025-10-01
deciders: Copilot Claude, User Feedback
consulted: QA Team, Operations
informed: Development Team, Stakeholders
supersedes: ADR-0038
---

# ADR-0039: Functional Coverage Framework (Supersedes Line-Based Metrics)

## Context and Problem Statement

**CRITICAL FLAW IDENTIFIED**: Line-based coverage is a perverse metric easily manipulated through:

- **Docstring verbosity**: Terse vs. verbose documentation (25x line inflation possible)
- **Code formatting**: Single-line vs. multi-line expressions 
- **Comment density**: Adding/removing explanatory comments
- **Style choices**: Compact vs. expanded syntax patterns

**Real Example**:
```python
# Compact: 1 line
def validate_mac(mac): return bool(mac and len(mac)==17 and all(c in '0123456789ABCDEFabcdef:' for c in mac))

# Verbose: 25 lines (identical functionality)
def validate_mac(mac):
    """Validate MAC address format..."""  # +15 docstring lines
    if not mac: return False              # +5 explicit condition lines  
    if len(mac) != 17: return False       # +3 validation lines
    for char in mac:                      # +2 loop lines
        if char not in valid_chars: return False
    return True
```

**Both have identical**:
- Functional complexity (1 function)
- Decision points (same logic branches)  
- Test coverage requirements (same edge cases)
- Operational risk (identical behavior)

**But line coverage shows 25x "improvement" through cosmetic changes!**

## Decision

### Functional Coverage Framework

#### 1. **Primary Metrics: Functional Units**

**Function Coverage**: Functions and methods executed
```
Coverage % = (Executed Functions) / (Total Functions) * 100
```

**Current Analysis**:
- bridge_controller: 22 functions, 27 conditionals, 17 try blocks = **66 functional units**
- mqtt_dispatcher: 38 functions, 41 conditionals, 12 try blocks = **91 functional units**  
- facade: 21 functions, 24 conditionals, 5 try blocks = **50 functional units**
- ble_bridge: 30 functions, 41 conditionals, 26 try blocks = **97 functional units**

#### 2. **Branch Coverage**: Decision Path Validation

**Conditional Coverage**: If/else, try/except paths exercised
```
Branch Coverage % = (Executed Branches) / (Total Branches) * 100
```

**Implementation**: Use `pytest-cov` with `--cov-branch` flag
```bash
pytest --cov=addon/bb8_core --cov-branch --cov-report=term-missing
```

#### 3. **Behavioral Coverage**: Use Case Validation

**Scenario Coverage**: Real-world usage patterns tested
- **Happy Path**: Normal operational flows
- **Error Conditions**: Exception handling and recovery
- **Edge Cases**: Boundary conditions and invalid inputs  
- **Integration**: Cross-module interactions and state management

#### 4. **API Surface Coverage**: Public Interface Validation

**Interface Coverage**: Public methods and classes tested
```
API Coverage % = (Tested Public Methods) / (Total Public Methods) * 100
```

### Measurement Framework

#### **Primary Command** (Functional + Branch):
```bash
PYTHONPATH="$PWD" python -m pytest addon/tests/ \
    --cov=addon/bb8_core \
    --cov-branch \
    --cov-report=json:functional_coverage.json \
    --cov-report=term-missing
```

#### **Coverage Composition**:
- **Function Coverage**: 70% weight (most important)
- **Branch Coverage**: 20% weight (decision paths)  
- **Integration Scenarios**: 10% weight (end-to-end flows)

#### **Anti-Gaming Measures**:
- ✅ **Function counting**: Immune to formatting changes
- ✅ **Branch analysis**: Measures logic, not lines
- ✅ **Behavioral validation**: Tests actual use cases  
- ✅ **Integration focus**: Real operational scenarios

### Operational Confidence Thresholds

| Function Coverage | Branch Coverage | Confidence Level | Deployment Readiness |
|-------------------|-----------------|------------------|---------------------|
| **≥85%** | **≥80%** | 🟢 **PRODUCTION** | Full confidence |
| **70-84%** | **65-79%** | 🟡 **STAGING** | Limited production |
| **50-69%** | **50-64%** | 🟠 **DEVELOPMENT** | Feature complete |
| **30-49%** | **30-49%** | 🔴 **FOUNDATIONAL** | Basic functionality |
| **<30%** | **<30%** | ⚫ **EXPERIMENTAL** | Prototype only |

### Module-Specific Targets

#### **Critical Modules (Target: 85% Function + 80% Branch)**:

| Module | Functions | Conditionals | Try Blocks | Total Units | Current Priority |
|--------|-----------|--------------|------------|-------------|------------------|
| bridge_controller | 22 | 27 | 17 | 66 | **P0** |
| mqtt_dispatcher | 38 | 41 | 12 | 91 | **P1** |
| ble_bridge | 30 | 41 | 26 | 97 | **P0** |
| facade | 21 | 24 | 5 | 50 | **P0** |

#### **Target Validation**:
- **bridge_controller**: 22 functions × 85% = 19 functions must be tested
- **mqtt_dispatcher**: 38 functions × 85% = 33 functions must be tested
- **facade**: 21 functions × 85% = 18 functions must be tested
- **ble_bridge**: 30 functions × 85% = 26 functions must be tested

### Implementation Strategy

#### **Phase 1: Function Coverage Baseline**
1. **Audit current function coverage** using function-level analysis
2. **Identify untested functions** in critical modules  
3. **Prioritize high-impact functions** (public APIs, error handlers)
4. **Target quick wins** in well-structured modules

#### **Phase 2: Branch Coverage Enhancement**
1. **Enable branch coverage** measurement in CI/CD
2. **Focus on conditional logic** and exception handling
3. **Test error paths** and edge conditions
4. **Validate state transitions** and async flows

#### **Phase 3: Behavioral Scenario Completion**
1. **End-to-end integration** scenarios
2. **Real operational workflows** (MQTT + BLE coordination)
3. **Fault injection** and recovery testing
4. **Performance and reliability** validation

### Quality Assurance

#### **Function Coverage Validation**:
```python
# Example: Validate all public methods tested
def test_function_coverage_audit():
    from addon.bb8_core import bridge_controller
    
    public_functions = [f for f in dir(bridge_controller) if not f.startswith('_')]
    
    # Each public function must have at least one test
    for func_name in public_functions:
        assert f"test_{func_name}" in test_registry, f"Missing test for {func_name}"
```

#### **Branch Coverage Validation**:
```python  
# Example: Ensure error paths tested
def test_error_path_coverage():
    with pytest.raises(ConnectionError):
        bridge_controller.connect_invalid_device()
        
    with pytest.raises(ValueError):
        bridge_controller.send_invalid_command()
```

### Tooling Requirements

#### **Coverage Analysis Tools**:
- **pytest-cov** with branch coverage enabled
- **Function coverage** analysis scripts
- **API coverage** validation
- **Integration scenario** tracking

#### **Reporting Dashboard**:
- **Function coverage** by module
- **Branch coverage** heatmaps  
- **Untested function** lists
- **Missing scenario** identification

## Consequences

### Positive
- **Gaming Resistance**: Function/branch metrics immune to formatting manipulation
- **Operational Focus**: Coverage directly correlates with tested functionality  
- **Quality Emphasis**: Measures actual test effectiveness, not cosmetic metrics
- **Clear Priorities**: Untested functions clearly identified for improvement

### Negative
- **Tooling Complexity**: Requires more sophisticated analysis than line counting
- **Initial Assessment**: Need to re-baseline all coverage measurements
- **Learning Curve**: Team must understand functional vs. line-based metrics

### Migration from Line-Based Framework
- **Immediate**: Replace line coverage with function coverage as primary metric
- **Transition**: Maintain branch coverage as secondary validation
- **Sunset**: Phase out line-based coverage reporting entirely

## Implementation

### Immediate Actions
1. **Update CI/CD** to use function + branch coverage
2. **Audit current** function coverage across critical modules  
3. **Communicate change** to development team with examples
4. **Establish baseline** using functional metrics

### Measurement Commands
```bash
# Primary functional coverage assessment
./ops/qa/functional_coverage_assessment.sh

# Detailed function-level analysis  
./ops/qa/untested_functions_audit.sh

# Branch coverage heatmap
./ops/qa/branch_coverage_analysis.sh
```

## Compliance

This framework **supersedes ADR-0038** and establishes **mandatory functional coverage standards**.

**Anti-Gaming Policy**: Any attempt to inflate coverage through cosmetic code changes (formatting, comments, docstrings) without adding functional test value is explicitly prohibited.

**Review Cycle**: Functional coverage effectiveness monitored through correlation with production issues and deployment confidence.

TOKEN_BLOCK_BEGIN_DO_NOT_EDIT
ADR-0039-functional-coverage-framework:supersedes-ADR-0038:function-branch-metrics:anti-line-gaming:behavioral-validation:operational-confidence
TOKEN_BLOCK_END_DO_NOT_EDIT