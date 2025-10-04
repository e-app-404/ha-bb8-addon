# LED Toggle Compliance Failure
**Date**: 2025-10-04  
**Status**: Configuration Mismatch  
**Priority**: P3 (Feature Configuration)

## Issue Summary
LED entity alignment test failing due to `PUBLISH_LED_DISCOVERY` configuration mismatch. Expected LED discovery publishing but detected as disabled.

## Test Results
```
=== LED Entity Alignment Summary ===
PUBLISH_LED_DISCOVERY: 0
Toggle compliance: False
Schema compliance: True  
Device alignment: True
Overall PASS: False
```

## Root Cause Analysis

### Configuration Context
- **Expected**: `PUBLISH_LED_DISCOVERY=1` (LED discovery enabled)
- **Actual**: `PUBLISH_LED_DISCOVERY=0` (LED discovery disabled)
- **Impact**: Test expects LED discovery to be published but it's configured off

### Discovery Results
```
LED discovery topics found: 3
- homeassistant/light/bb8_bb8_led/config (empty device block)
- homeassistant/light/bb8_led/config (proper device block)
```

## Configuration Investigation

### 1. Addon Options Check
```json
// addon/options.json - Expected configuration
{
  "dispatcher_discovery_enabled": true,  // May control LED discovery
  "discovery_retain": false,
  // Other LED-related options?
}
```

### 2. Environment Variables
```bash
# Check INT-HA-CONTROL test environment
PUBLISH_LED_DISCOVERY=0  # Currently disabled
# Should be: PUBLISH_LED_DISCOVERY=1
```

### 3. Code Configuration
- LED discovery may be controlled by addon configuration option
- Test environment may override addon settings
- Feature flag may be disabled by default

## Investigation Required

### 1. Configuration Source Audit
- [ ] Check addon options for LED discovery control settings
- [ ] Verify test environment variable sourcing
- [ ] Review `mqtt_dispatcher.py` for LED discovery toggle logic

### 2. Feature Flag Analysis  
- [ ] Identify what controls `PUBLISH_LED_DISCOVERY` setting
- [ ] Check if this is test-only or addon-wide configuration
- [ ] Verify intended default state for LED discovery

### 3. Test Expectation Validation
- [ ] Confirm if LED discovery should be enabled by default
- [ ] Check if test expectation matches intended behavior
- [ ] Review ADR requirements for LED entity publishing

## Potential Solutions

### 1. Enable LED Discovery
```bash
# Set environment variable for tests
export PUBLISH_LED_DISCOVERY=1
```

### 2. Update Addon Configuration
```json
// In addon options
{
  "led_discovery_enabled": true,
  "dispatcher_discovery_enabled": true
}
```

### 3. Test Expectation Correction
```python
# If LED discovery should be disabled by default
# Update test to expect PUBLISH_LED_DISCOVERY=0
```

## Impact Assessment
- **User Experience**: LED entities may not auto-discover in HA
- **Testing**: LED validation tests failing in QA pipeline  
- **Feature Completeness**: LED control may require manual setup

## Related Device Block Issue
- One of the LED entities (`bb8_bb8_led`) has empty device block
- This may be related to the discovery publishing configuration
- See: `device_block_partial_fix_analysis_2025-10-04.md`

## Success Criteria
- LED toggle compliance test passes
- `PUBLISH_LED_DISCOVERY` setting matches expected behavior
- LED entities properly discoverable in Home Assistant
- All LED discovery messages have proper device blocks

---
**Session Context**: INT-HA-CONTROL validation showing LED configuration mismatch  
**Next Action**: Review addon LED discovery configuration and test expectations