---
id: "QG-TEST-80-PLAN-0001"
title: "Coverage with Honesty Plan"
authors: "HA-BB8 Engineering Team"
source: ""
slug: "qg-test-80-coverage-honesty-plan"
tags: ["coverage", "testing", "ha-bb8", "quality-gates"]
date: "2025-10-07"
last_updated: "2024-06-11"
url: ""
related: ""
adr: ""
---

# Coverage with Honesty Plan

**Created**: 2025-10-07
**Branch**: `qg-test-80/coverage-honest-2025-10-07`
**Baseline**: INT-HA-CONTROL_ACCEPTED_2025-10-07

## Executive Summary

Honest coverage assessment and incremental improvement plan for the HA-BB8 add-on. Focus on integration-first testing with realistic coverage targets and documented omissions.

## Current Baseline (Honest Assessment)

### Coverage Reality Check

- **Current Estimated**: ~45–50% (with realistic measurement)
- **Target Initial**: 60% (`fail_under` in `pytest.ini`)
- **Target Final**: 75–80% (achievable with integration focus)
- **Excluded**: Hardware-dependent BLE operations, container startup

### Key Omissions (Documented)

```text
addon/bb8_core/ble_gateway.py  # Hardware BLE operations - requires physical device
addon/run.py                   # Container entry point - minimal logic
*/tests/*                      # Test files themselves
*/test_*.py                    # Test utilities
```

## Phase 1: Integration Foundation (Weeks 1–2)

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

- Mock external dependencies: MQTT broker, BLE hardware
- Focus on interfaces between core components
- State validation: persistence, recovery, ownership
- Policy enforcement: LED gating, discovery rules

## Phase 2: Coverage Expansion (Weeks 3–4)

### Target Delta: +15% Coverage

- Bridge Controller: orchestration logic
- Echo Responder: MQTT roundtrip validation
- Logging Setup: structured logging, redaction
- Error Handling: exception paths, recovery

### Test Infrastructure

- Fixtures: common mock patterns
- Harnesses: MQTT test utilities (reuse existing)
- Assertions: state validation helpers
- Mocking: hardware abstraction layers

## Phase 3: Quality Gates (Week 5)

### Coverage Validation

- **Threshold**: 75% minimum with honest measurement
- **Documentation**: all omissions explained inline
- **CI Integration**: fail on regression
- **Reports**: HTML coverage with gap analysis

### Quality Checks

- Integration tests: all critical paths covered
- Unit tests: logic validation without hardware
- Performance: no regression in test execution time
- Maintainability: test code quality standards

## Implementation Strategy

### Test Organization

```text
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

- `.coveragerc`: honest omissions, documented exceptions
- `pytest.ini`: fail under 60%, ratchet up incrementally
- CI integration: coverage reports in pull requests

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

- Mock complexity: keep integration mocks simple
- Hardware dependencies: clear abstraction boundaries
- Test maintenance: avoid brittle coupling to implementation
- Coverage gaming: focus on meaningful test scenarios

### Monitoring

- Coverage trends: track over time, identify gaps
- Test performance: execution time budgets
- Flaky tests: isolation and reliability patterns
- Documentation: keep coverage rationale current

## Next Steps

1. **Branch Setup**: ✅ Complete – coverage policy applied
2. **Integration Tests**: ✅ Started – MQTT discovery ownership
3. **CI Integration**: Add coverage reporting to pipeline
4. **Documentation**: Maintain coverage exception rationale
5. **Monitoring**: Establish coverage trend tracking

---

**Phase**: Planning Complete
**Ready For**: Implementation Sprint
**Baseline Tag**: INT-HA-CONTROL_ACCEPTED_2025-10-07
