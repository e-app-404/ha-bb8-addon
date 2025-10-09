# BB-8 BLE Charging Cradle Analysis Report

**Date**: 2025-10-09
**Test Environment**: macOS development environment
**BLE Scanner**: bleak v0.22.3 + spherov2 v0.12.1
**Objective**: Understand BB-8 BLE advertising behavior in various charging cradle states

## Test Scenarios

### Completed Scenarios

#### Scenario 1: BB-8 Outside Cradle, Cradle Connected to Power

**Status**: ✅ COMPLETED
**Setup**: BB-8 removed from charging cradle, cradle plugged into power
**Results**:

- **BB-B54A Device Found**:
  - Address: `259ED00E-3026-2568-C410-4590C9A9297C`
  - RSSI: -44 dBm (very strong signal)
  - Status: Active
- **S33 BB84 LE Device Found**:
  - Address: `09C6CEBB-2743-A94A-73FC-A7B36E5F5864`
  - RSSI: -68 dBm (moderate signal)
  - Status: Active
- **Other Sphero Devices**: 6 additional S-series devices detected
- **Total BLE Devices**: 37 devices scanned

#### Scenario 2: BB-8 Outside Cradle, Cradle Disconnected from Power

**Status**: ✅ COMPLETED
**Setup**: BB-8 removed from charging cradle, cradle unplugged from power
**Results**:

- **BB-B54A Device**: ❌ NOT FOUND (disappeared)
- **S33 BB84 LE Device Found**:
  - Address: `09C6CEBB-2743-A94A-73FC-A7B36E5F5864`
  - RSSI: -61 dBm (improved signal vs Scenario 1)
  - Status: Active
- **Other Sphero Devices**: 6 additional S-series devices detected
- **Total BLE Devices**: 24 devices scanned (13 fewer than Scenario 1)

**Key Finding**: BB-B54A appears to be the charging cradle's BLE interface, only active when cradle has power.

### Completed Scenarios (Continued)

#### Scenario 3: BB-8 Inside Cradle, Cradle Connected to Power

**Status**: ✅ COMPLETED
**Setup**: BB-8 docked in charging cradle, cradle plugged into power
**Results**:

- **BB-B54A Device Found**:
  - Address: `259ED00E-3026-2568-C410-4590C9A9297C`
  - RSSI: -57 dBm (good signal)
  - Status: Active
- **S33 BB84 LE Device Found**:
  - Address: `09C6CEBB-2743-A94A-73FC-A7B36E5F5864`
  - RSSI: -64 dBm (moderate signal)
  - Status: Active
- **Other Sphero Devices**: 6 additional S-series devices detected
- **Total BLE Devices**: 32 devices scanned

#### Scenario 4: BB-8 Inside Cradle, Cradle Disconnected from Power

**Status**: ✅ COMPLETED
**Setup**: BB-8 docked in charging cradle, cradle unplugged from power
**Results**:

- **BB-B54A Device Found**: ⚠️ STILL PRESENT (unexpected!)
  - Address: `259ED00E-3026-2568-C410-4590C9A9297C`
  - RSSI: -52 dBm (improved signal vs Scenario 3)
  - Status: Active
- **S33 BB84 LE Device Found**:
  - Address: `09C6CEBB-2743-A94A-73FC-A7B36E5F5864`
  - RSSI: -66 dBm (slightly weaker signal)
  - Status: Active
- **Other Sphero Devices**: 6 additional S-series devices detected
- **Total BLE Devices**: 34 devices scanned

**Key Finding**: BB-B54A persists without cradle power - hypothesis revision needed!

#### Scenario 5: BB-8 Inside Cradle, Cradle Connected + Wake Button Pressed

**Status**: ✅ COMPLETED
**Setup**: BB-8 docked, cradle powered, wake-up button pressed during scan
**Results**:

- **BB-B54A Device Found**:
  - Address: `259ED00E-3026-2568-C410-4590C9A9297C`
  - RSSI: -48 dBm (strongest signal yet!)
  - Status: Active, enhanced by wake-up
- **S33 BB84 LE Device Found**:
  - Address: `09C6CEBB-2743-A94A-73FC-A7B36E5F5864`
  - RSSI: -64 dBm (consistent signal)
  - Status: Active
- **Other Sphero Devices**: 6 additional S-series devices detected
- **Total BLE Devices**: 31 devices scanned
- **Wake-up Effect**: BB-B54A signal strengthened by 9 dBm (-57 to -48)

#### Scenario 6: BB-8 Outside Cradle, Cradle Connected + Wake Button Pressed

**Status**: ✅ COMPLETED
**Setup**: BB-8 removed, cradle powered, wake-up button pressed during scan
**Results**:

- **BB-B54A Device Found**:
  - Address: `259ED00E-3026-2568-C410-4590C9A9297C`
  - RSSI: -49 dBm (strong signal)
  - Status: Active, cradle responds to wake button
- **S33 BB84 LE Device Found**:
  - Address: `09C6CEBB-2743-A94A-73FC-A7B36E5F5864`
  - RSSI: -67 dBm (weaker when separated)
  - Status: Active
- **Other Sphero Devices**: 6 additional S-series devices detected
- **Total BLE Devices**: 32 devices scanned
- **Wake-up Effect**: Cradle responds to wake button even without BB-8 docked

## Device Analysis

### BB-B54A (Charging Cradle Interface)

- **Hypothesis**: BLE interface for charging cradle
- **Power Dependency**: Only appears when cradle has power
- **Signal Strength**: Very strong (-44 to -47 dBm) - likely due to close proximity
- **Behavior**: Disappears immediately when cradle power removed

### S33 BB84 LE (BB-8 Droid)

- **Hypothesis**: The actual BB-8 droid's BLE interface
- **Power Independence**: Present regardless of cradle power state
- **Signal Strength**: Moderate (-61 to -68 dBm) - varies with interference
- **Behavior**: Signal improves when cradle power interference removed

### Other S-Series Devices

- **Count**: 6 additional devices (S31, S36, S39 variants, S54)
- **Hypothesis**: Other Sphero devices in vicinity or legacy advertising modes
- **Consistency**: Present in both scenarios

## Technical Observations

### Signal Interference

- Powered charging cradle may cause BLE interference
- S33 BB84 LE signal improved from -68 to -61 dBm when cradle powered down
- Suggests electromagnetic interference from cradle power supply

### Device Discovery Changes

- 37 total devices with cradle powered → 24 devices with cradle unpowered
- Reduction of 13 devices suggests cradle or power supply affects local BLE environment

### Advertising Patterns

- BB-B54A: Appears to be a pure charging cradle interface
- S33 BB84 LE: Consistent with BB-8 droid naming pattern (BB84 = BB-8 variant 4?)

## Next Steps

Execute remaining scenarios 3-6 to complete the analysis and determine:

1. How docking affects BLE advertising
2. Impact of wake-up button on signal characteristics
3. Optimal connection target for HA-BB8 addon configuration

---

_Report will be updated as scenarios are completed_
