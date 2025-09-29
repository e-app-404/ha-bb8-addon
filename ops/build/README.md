# ops/build/

## Purpose
Compilation, testing, and CI/CD pipeline scripts for the HA-BB8 addon.

## Scripts

### compile_test_gate_bleep.sh (Planned)
**Purpose**: Hardened deterministic health check script  
**Usage**: `./compile_test_gate_bleep.sh`  
**Description**: Runs compile → test → coverage → gate → bleep → ADR check pipeline

### qa_pipeline.sh (Planned)
**Purpose**: Wrapper for complete QA pipeline  
**Usage**: `./qa_pipeline.sh [--strict]`  
**Description**: Orchestrates quality assurance checks in proper order

### coverage_check.sh (Planned)
**Purpose**: Test coverage validation and reporting  
**Usage**: `./coverage_check.sh [--threshold=80]`  
**Description**: Validates test coverage meets minimum thresholds

## Workflow Integration

These scripts are typically called by:
- Local development (`make qa`)
- CI/CD pipelines
- Pre-release validation
- Development workflow gates

## Dependencies

- Python virtual environment (`.venv/`)
- pytest and coverage tools
- Addon source code in `addon/`
- Test suite in `addon/tests/`

## Notes

- All scripts should be idempotent and safe to run multiple times
- Output should be deterministic for CI/CD consistency  
- Scripts should exit with appropriate codes (0=success, 1=failure, 2=error)