# Unit Test Import Path Failures
**Date**: 2025-10-04  
**Status**: Test Discovery Broken  
**Priority**: P2 (Development/QA Impact)

## Issue Summary
Unit tests failing to run due to import path configuration issues. Tests cannot locate `addon` module when running from different working directories.

## Error Details
```
ModuleNotFoundError: No module named 'addon'
ImportError while importing test module '/Users/.../addon/tests/test_addon_config_complete.py'
```

## Root Cause Analysis

### Path Context Issues
1. **Working Directory Dependency**: Tests expect to be run from specific directory
2. **Module Path Configuration**: `addon` module not in Python path when running tests
3. **Import Structure**: Tests using `from addon.bb8_core import ...` but `addon` not resolvable

### Current Import Pattern
```python
# In test files
from addon.bb8_core import mqtt_dispatcher  # ❌ Fails when addon not in path
```

## Investigation Required

### 1. Test Environment Setup
- [ ] Check pytest configuration in `addon/pytest.ini`
- [ ] Verify PYTHONPATH setup in test execution
- [ ] Compare working vs failing execution contexts

### 2. Import Structure Analysis
- [ ] Review test import patterns across all test files
- [ ] Compare with working imports in main code
- [ ] Identify inconsistent import structures

### 3. Virtual Environment Context
- [ ] Verify addon installation in virtual environment
- [ ] Check if `pip install -e addon` was run properly
- [ ] Test import resolution from different directories

## Test Execution Context

### Current Failure (from addon/ directory)
```bash
cd addon/
pytest tests/test_addon_config_complete.py
# ❌ ModuleNotFoundError: No module named 'addon'
```

### Expected Working Pattern
```bash
cd project_root/
pip install -e addon/
pytest addon/tests/
# ✅ Should work with proper addon installation
```

## Potential Solutions

### 1. Development Installation Fix
```bash
# From project root
pip install -e addon/
# This makes 'addon' importable from anywhere
```

### 2. PYTHONPATH Configuration
```bash
# Add addon directory to Python path
export PYTHONPATH="$PWD/addon:$PYTHONPATH"
pytest addon/tests/
```

### 3. Pytest Configuration Update
```ini
# addon/pytest.ini
[tool:pytest]
testpaths = tests
pythonpath = .
addopts = --import-mode=importlib
```

### 4. Import Pattern Standardization
```python
# Option A: Relative imports within addon
from bb8_core import mqtt_dispatcher

# Option B: Absolute imports with proper installation
from addon.bb8_core import mqtt_dispatcher  
```

## Files to Investigate
- `addon/pytest.ini` - Test configuration
- `addon/setup.py` or `addon/pyproject.toml` - Package configuration
- `addon/tests/test_*.py` - Import patterns in test files
- Root-level pytest configuration

## Impact Assessment
- **QA Pipeline**: Unit tests not running in CI/CD
- **Development**: Local testing broken
- **Coverage**: Cannot measure test coverage accurately
- **INT-HA-CONTROL**: Test validation steps failing

## Success Criteria
- All unit tests can be discovered and run successfully
- Tests pass from both project root and addon/ directories  
- Import errors resolved across all test files
- QA pipeline (`make testcov`) works without path issues

---
**Session Context**: INT-HA-CONTROL validation revealed test discovery problems  
**Next Action**: Review pytest configuration and addon installation setup