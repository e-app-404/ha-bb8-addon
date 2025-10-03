# ADR Workspace Organization Formalization Patch

## Overview
This patch formalizes the comprehensive workspace reorganization completed on 2025-09-30 through amendments to existing ADRs, establishing canonical file placement and the logs/ vs reports/ separation principle.

## Changes Applied

### 1. ADR-0024 Amendment A: Workspace Organization (Primary)

**Added comprehensive Amendment A** covering:
- **A1**: logs/ vs reports/ separation with clear purposes and git tracking rules
- **A2**: Canonical file placements for operational scripts, testing, and validation
- **A3**: Script output path requirements (mandatory `logs/` usage)
- **A4**: Extended enforcement beyond base hygiene gates
- **A5**: Migration compliance documentation

**Key additions:**
- Formalized `logs/` (git-ignored) vs `reports/` (selectively tracked) distinction
- Established canonical locations for coverage files, diagnostics, evidence collection
- Added enforcement tokens for workspace organization compliance
- Updated .gitignore specification as part of ADR governance

### 2. ADR-0019 Consistency Updates (Supporting)

**Updated canonical roots** to include:
- `logs/`: Temporary outputs and automated artifacts (git-ignored)  
- `reports/`: Important documentation for long-term retention (git-tracked selective)

**Updated assignation rules** for:
- Temporary outputs → `logs/` (git-ignored)
- Important documentation → `reports/` (git-tracked)
- Coverage and addon-specific configs → `addon/`

## Implementation Evidence

### Files Moved/Organized:
- ✅ Coverage files: `.coverage*` → `addon/`
- ✅ Diagnostic outputs: `ha_bb8_diagnostics_*` → `logs/`
- ✅ Status scripts: INT-HA-CONTROL framework → `reports/checkpoints/`
- ✅ Temporary artifacts: STP4 evidence, receipts, logs → `logs/`

### Configuration Updates:
- ✅ Diagnostics script: Modified to output to `logs/` directory
- ✅ .gitignore: Updated with logs/ vs reports/ separation rules
- ✅ Status script: Updated with workspace organization information

### Documentation Created:
- ✅ `reports/WORKSPACE_ORGANIZATION.md` - Implementation guidelines
- ✅ `reports/WORKSPACE_ORGANIZATION_COMPLETION.md` - Change summary

## Token Compliance

### ADR-0024 New Tokens:
```yaml
accepted:
  - WORKSPACE_ORGANIZATION_OK
  - CANONICAL_PLACEMENT_OK  
  - LOGS_REPORTS_SEPARATION_OK
  - SCRIPT_OUTPUT_PATHS_OK
drift:
  - DRIFT: misplaced_outputs
  - DRIFT: coverage_file_pollution
  - DRIFT: reports_contamination
  - DRIFT: canonical_violation
```

## Enforcement Implications

### Automated Validation:
- Scripts outputting to repo root instead of `logs/` = violation
- Coverage files at repo root instead of `addon/` = violation  
- Temporary files in `reports/` instead of `logs/` = violation
- Diagnostic tools not using canonical paths = violation

### CI/CD Integration:
- Hygiene gates extended to check canonical file placement
- Pre-commit hooks validate workspace organization compliance
- Branch protection requires workspace organization adherence

## Cross-ADR Relationships

This patch maintains consistency across the ADR ecosystem:
- **ADR-0001**: Workspace topology (dual-clone, canonical paths)
- **ADR-0019**: Folder taxonomy (updated canonical roots and assignation rules)
- **ADR-0024**: Workspace hygiene (base policy + Amendment A organization)

## Migration Status

**COMPLETE**: All workspace reorganization changes have been:
1. ✅ **Implemented** (files moved, scripts updated, configs applied)
2. ✅ **Documented** (organizational guidelines created)  
3. ✅ **Formalized** (ADR amendments with governance tokens)
4. ✅ **Enforced** (.gitignore rules, canonical path requirements)

## Validation Commands

Verify compliance:
```bash
# Check logs/ vs reports/ separation
ls logs/ reports/ 

# Verify coverage files location  
ls addon/.coverage*

# Confirm script output paths
./ops/diag/collect_ha_bb8_diagnostics.sh --dry-run

# Validate framework location
ls reports/checkpoints/INT-HA-CONTROL/
```

**Status**: PATCH COMPLETE - Workspace organization fully formalized in ADR governance framework.