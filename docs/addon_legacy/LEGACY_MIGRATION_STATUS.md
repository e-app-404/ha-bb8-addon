# LEGACY_MIGRATION_STATUS.md

This document tracks the migration of legacy CLI/config-dependent modules to Home Assistant-compatible core modules.

| Original File | New Module | SHA256 (Original) | SHA256 (Migrated) | Component Type |
|--------------|------------|-------------------|-------------------|---------------|
| ha-sphero-bb8/legacy/launch_bb8.py | local.ha-bb8-addon/core/ble_bridge.py | fa491de718a61d76380b5b222989910f913e640c785e97897f7e8be61bc2969b | cbe95ebc19645e3a8ed733464f621f4d94f3534c5bdb533f06d782eb716be304 | ble |
| ha-sphero-bb8/legacy/run_mqtt.py | local.ha-bb8-addon/core/mqtt_dispatcher.py | d2a837c4a0f0a93dd9b18856a7409deec029878c2a932f75563075d896c38125 | a52524e3985f2e7ba76acd9f1f264d8959cde328c34917d1e51627adb6f00922 | mqtt |
| ha-sphero-bb8/legacy/mqtt_handler.py | local.ha-bb8-addon/core/bridge_controller.py | 19596c6dc2a1791501422473619150657086fb6fd3638a2bc7389c870bec1b5a | d633effe45225df1a6b5ed6864be03fa733ede3f83658c632e14177290399191 | bridge |

## Deprecated Interfaces Removed

- argparse, sys.argv, input(), click
- if __name__ == "__main__"
- YAML/JSON config file dependencies
- All CLI/manual config flags and command-line argument parsing

## Test Validation Status

- import_success: true (all new core modules can be imported in the add-on runtime)
- callable_main_functions: false (no CLI entrypoints remain; all logic is now service/module-based)
- configuration_free: true (all runtime customization is via function arguments or environment variables, not config files or CLI)
