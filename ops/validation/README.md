# ops/validation/

## Purpose
Code quality, structure validation, and compliance checking scripts.

## Scripts

### check_structure.sh (Planned)
**Purpose**: Repository and addon structure validation  
**Usage**: `./check_structure.sh`  
**Description**: Validates directory structure, required files, and layout compliance

### verify_addon.sh (Planned)
**Purpose**: Home Assistant addon verification  
**Usage**: `./verify_addon.sh`  
**Description**: Validates addon configuration and Home Assistant compatibility

### qa_harvest.py (Planned) 
**Purpose**: Quality assurance metrics collection  
**Usage**: `python qa_harvest.py [--output=report.json]`  
**Description**: Harvests QA metrics and generates compliance reports

### discovery_align_audit.py (Planned)
**Purpose**: MQTT discovery alignment audit  
**Usage**: `python discovery_align_audit.py`  
**Description**: Audits MQTT discovery message alignment and consistency

### shape_guard.py (Planned)
**Purpose**: Structural integrity validation  
**Usage**: `python shape_guard.py [--strict]`  
**Description**: Guards against structural violations and ensures shape compliance

## Validation Categories

### Structure Validation
- Directory layout compliance
- Required file presence  
- Configuration file validity
- Dependency consistency

### Code Quality
- Linting compliance (ruff, mypy)
- Test coverage thresholds
- Import cycle detection
- Security vulnerability scanning

### Addon Compliance
- Home Assistant addon requirements
- Configuration schema validation
- Service definition compliance
- Docker container requirements

### Protocol Compliance
- MQTT message format validation
- Home Assistant discovery protocol
- BLE communication standards
- API interface contracts

## Exit Codes

- `0`: All validations passed
- `1`: Validation failures found
- `2`: Script execution error
- `3`: Configuration error

## Integration

Used by:
- Pre-commit hooks
- CI/CD validation gates  
- Release quality gates
- Development workflow checks
- Manual quality assurance