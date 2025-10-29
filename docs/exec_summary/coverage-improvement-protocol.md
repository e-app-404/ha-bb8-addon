# Test Coverage Improvement Protocol (ADR-0038 Implementation)

## Current Status: 47.4% Coverage (DEVELOPMENT Level)

**Baseline Established**: 49.7% (October 2025) - No statistical manipulation  
**Current Measurement**: 47.4% coverage (1,643/3,466 lines)  
**Confidence Level**: 🟠 DEVELOPMENT (Feature Complete)  
**Phase Progress**: Phase 1 in progress (17.6% remaining to reach staging ready)

## Critical Modules Analysis

| Module | Current | Target | Lines Needed | Priority |
|--------|---------|--------|--------------|----------|
| bridge_controller | 30.6% | 85% | +165 lines | **P0** |
| mqtt_dispatcher | 61.3% | 85% | +96 lines | **P1** |
| facade | 37.3% | 85% | +95 lines | **P0** |
| ble_bridge | 24.4% | 85% | +97 lines | **P0** |

## Phase-Based Improvement Framework

### Phase 1: Quick Wins (47.4% → 65%)
**Target**: +610 lines total coverage  
**Timeline**: 4-6 weeks  
**Focus**: Modules already above 50% coverage

**Immediate Opportunities (+136 lines):**
1. mqtt_dispatcher: 61.3% → 80% (+76 lines)
2. bb8_presence_scanner: 65.0% → 80% (+64 lines)  
3. echo_responder: 65.1% → 80% (+38 lines)
4. addon_config: 65.8% → 80% (+16 lines)
5. ble_link: 66.9% → 80% (+16 lines)

**Implementation Strategy:**
- Focus on existing test expansion vs. new test creation
- Target edge cases and error paths in well-tested modules
- Leverage existing mocking infrastructure

### Phase 2: Critical Infrastructure (65% → 75%)
**Target**: +347 lines in critical modules  
**Timeline**: 6-8 weeks  
**Focus**: Core operational modules

**Priority Order:**
1. **bridge_controller** (30.6% → 75%): +135 lines
   - Main orchestration logic
   - BLE initialization and management
   - MQTT client lifecycle
   
2. **facade** (37.3% → 75%): +76 lines
   - Public API surface coverage
   - Command handling paths
   - State management scenarios

3. **ble_bridge** (24.4% → 75%): +81 lines
   - Device communication protocols
   - Connection management
   - Command execution paths

4. **auto_detect** (29.5% → 75%): +131 lines
   - Device discovery logic
   - MAC address validation
   - Cache management

### Phase 3: Production Ready (75% → 85%)
**Target**: +347 lines completing critical modules  
**Timeline**: 4-6 weeks  
**Focus**: Comprehensive integration testing

**Final Targets:**
- All Tier 1 modules: 85% coverage
- All Tier 2 modules: 75% coverage  
- Integration scenarios: End-to-end flows
- Error handling: Comprehensive fault injection

## Implementation Guidelines

### Test Development Priorities

**High-Impact Areas:**
1. **Error Handling**: Exception paths, network failures, device disconnections
2. **Edge Cases**: Boundary conditions, invalid inputs, race conditions
3. **Integration Flows**: Cross-module communication, state synchronization
4. **Configuration Scenarios**: Different deployment environments, option combinations

**Testing Strategy:**
- **Unit Tests**: Core business logic, algorithms, data transformations
- **Integration Tests**: Module interactions, MQTT/BLE coordination  
- **Mock-Heavy Tests**: External dependency simulation (paho-mqtt, bleak, asyncio)
- **Scenario Tests**: Real-world usage patterns, failure recovery

### Development Workflow

**Per Feature/Fix:**
```bash
# 1. Run baseline assessment
./ops/qa/coverage_assessment.sh phase1

# 2. Develop with test-first approach
pytest addon/tests/test_new_feature.py --cov=addon/bb8_core --cov-report=term-missing

# 3. Validate no regression
./ops/qa/coverage_assessment.sh phase1  # Must be ≥47.4%

# 4. Target improvement  
# New code must achieve ≥80% coverage
```

**Weekly Reviews:**
- Module-level progress tracking
- Phase milestone evaluation
- Test quality assessment (not just quantity)

### Coverage Quality Metrics

**Beyond Line Coverage:**
1. **Branch Coverage**: Decision path testing (when tooling supports)
2. **Function Coverage**: Public API surface validation
3. **Integration Coverage**: Cross-module interaction testing
4. **Scenario Coverage**: Real-world usage pattern validation

**Anti-Patterns to Avoid:**
- Tests that only execute code without meaningful assertions
- Overly complex mocks that don't reflect real behavior
- Tests that require extensive setup for minimal coverage gain
- Duplicate test scenarios across different test files

### Tooling and Infrastructure

**Required Tools:**
```bash
# Coverage measurement (standardized)
./ops/qa/coverage_assessment.sh [phase1|phase2|phase3]

# Module-specific testing
pytest addon/tests/test_bridge_controller.py --cov=addon/bb8_core/bridge_controller

# Progress tracking
git log --oneline --grep="coverage" --since="1 week ago"
```

**CI/CD Integration:**
- Coverage regression prevention (≥47.4% threshold)
- New code coverage requirements (≥80%)
- Module-level coverage tracking
- Phase milestone validation

### Success Metrics

**Phase Completion Criteria:**

**Phase 1 Complete** (65% coverage):
- Quick win modules all at 80%+
- Overall coverage at 65%+
- No critical module below 40%
- Staging deployment confidence achieved

**Phase 2 Complete** (75% coverage):
- All critical modules at 75%+
- Overall coverage at 75%+
- Limited production deployment confidence
- Integration test infrastructure complete

**Phase 3 Complete** (85% coverage):
- All Tier 1 modules at 85%+
- All Tier 2 modules at 75%+
- Overall coverage at 85%+
- Full production deployment confidence

### Risk Mitigation

**Development Velocity Impact:**
- Implement coverage improvements in parallel with feature development
- Focus on high-value tests that catch real bugs
- Use existing test patterns and infrastructure

**Test Maintenance Overhead:**
- Prefer simple, focused tests over complex scenarios
- Maintain clear test documentation and naming
- Regular test suite cleanup and refactoring

**Quality vs. Quantity Balance:**
- Measure test effectiveness through bug detection
- Review failed tests in production for coverage gaps
- Prefer fewer high-quality tests over many low-value tests

## Measurement and Reporting

**Standardized Coverage Command** (ADR-0038):
```bash
PYTHONPATH="$PWD" python -m pytest addon/tests/ \
    --ignore=addon/tests/test_*_complete.py \
    --cov=addon/bb8_core \
    --cov-report=json:coverage.json \
    --cov-report=term-missing
```

**Progress Tracking:**
- Weekly coverage reports with module breakdown
- Phase milestone progress indicators
- Critical module improvement trends
- Deployment confidence level assessment

This framework provides a realistic, achievable path from 47.4% to 85% coverage while maintaining development velocity and ensuring test quality aligns with operational requirements.