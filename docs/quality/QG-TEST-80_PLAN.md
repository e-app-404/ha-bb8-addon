# QG-TEST-80: Coverage with Honesty Plan

**Created**: 2025-10-07  
**Branch**: `qg-test-80/coverage-honest-2025-10-07`  
**Baseline**: INT-HA-CONTROL_ACCEPTED_2025-10-07  

## Executive Summary

Honest coverage assessment and incremental improvement plan for HA-BB8 addon. Focus on integration-first testing with realistic coverage targets and documented omissions.

## Current Baseline (Honest Assessment)

### Coverage Reality Check
- **Current Estimated**: ~45-50% (with realistic measurement)
- **Target Initial**: 60% (fail_under in pytest.ini)
- **Target Final**: 75-80% (achievable with integration focus)
- **Excluded**: Hardware-dependent BLE operations, container startup

### Key Omissions (Documented)
```
addon/bb8_core/ble_gateway.py  # Hardware BLE operations - requires physical device
addon/run.py                   # Container entry point - minimal logic
*/tests/*                      # Test files themselves
*/test_*.py                    # Test utilities
```

## Phase 1: Integration Foundation (Weeks 1-2)

### Priority Areas
1. **MQTT Dispatcher** (`mqtt_dispatcher.py`)
   - Discovery ownership validation
   - State persistence through reconnection
   - LED gating enforcement
   - Error handling patterns

2. **BB8 Facade** (`facade.py`) 
   - BLE/MQTT bridge coordination
   - State synchronization
   - Command routing

3. **Configuration** (`addon_config.py`)
   - Provenance tracking
   - Environment variable resolution
   - Fallback mechanism validation

### Integration Test Patterns
- **Mock External Dependencies**: MQTT broker, BLE hardware
- **Focus on Interfaces**: Between core components
- **State Validation**: Persistence, recovery, ownership
- **Policy Enforcement**: LED gating, discovery rules

## Phase 2: Coverage Expansion (Weeks 3-4)

### Target Delta: +15% Coverage
- **Bridge Controller**: Orchestration logic
- **Echo Responder**: MQTT roundtrip validation  
- **Logging Setup**: Structured logging, redaction
- **Error Handling**: Exception paths, recovery

### Test Infrastructure
- **Fixtures**: Common mock patterns
- **Harnesses**: MQTT test utilities (reuse existing)
- **Assertions**: State validation helpers
- **Mocking**: Hardware abstraction layers

## Phase 3: Quality Gates (Week 5)

### Coverage Validation
- **Threshold**: 75% minimum with honest measurement
- **Documentation**: All omissions explained inline
- **CI Integration**: Fail on regression
- **Reports**: HTML coverage with gap analysis

### Quality Checks
- **Integration Tests**: All critical paths covered
- **Unit Tests**: Logic validation without hardware
- **Performance**: No regression in test execution time
- **Maintainability**: Test code quality standards

## Implementation Strategy

### Test Organization
```
addon/tests/
├── unit/                    # Pure logic tests
│   ├── test_config.py
│   ├── test_facade.py
│   └── test_dispatcher.py
├── integration/             # Component interaction
│   ├── test_mqtt_discovery_ownership.py  # ✅ Created
│   ├── test_restart_persistence.py
│   └── test_led_gating.py
└── fixtures/                # Common test utilities
    ├── mock_broker.py
    └── mock_ble.py
```

### Coverage Configuration
- **`.coveragerc`**: Honest omissions, documented exceptions
- **`pytest.ini`**: Fail under 60%, ratchet up incrementally
- **CI Integration**: Coverage reports in pull requests

## Success Criteria

### Quantitative
- [ ] 60% coverage threshold (Phase 1)
- [ ] 75% coverage target (Phase 3)
- [ ] 0 undocumented omissions
- [ ] <10% coverage regression tolerance

### Qualitative
- [ ] All integration scenarios tested
- [ ] Discovery ownership validated
- [ ] State persistence confirmed
- [ ] LED gating enforced
- [ ] Error paths covered

## Risk Mitigation

### Common Pitfalls
- **Mock Complexity**: Keep integration mocks simple
- **Hardware Dependencies**: Clear abstraction boundaries
- **Test Maintenance**: Avoid brittle coupling to implementation
- **Coverage Gaming**: Focus on meaningful test scenarios

### Monitoring
- **Coverage Trends**: Track over time, identify gaps
- **Test Performance**: Execution time budgets
- **Flaky Tests**: Isolation and reliability patterns
- **Documentation**: Keep coverage rationale current

## Next Steps

1. **Branch Setup**: ✅ Complete - coverage policy applied
2. **Integration Tests**: ✅ Started - MQTT discovery ownership
3. **CI Integration**: Add coverage reporting to pipeline
4. **Documentation**: Maintain coverage exception rationale
5. **Monitoring**: Establish coverage trend tracking

---

**Phase**: Planning Complete  
**Ready For**: Implementation Sprint  
**Baseline Tag**: INT-HA-CONTROL_ACCEPTED_2025-10-07