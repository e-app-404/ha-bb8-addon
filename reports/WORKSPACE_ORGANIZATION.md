# Reports vs Logs Organization

## reports/ (Git-tracked important documentation)
- **checkpoints/** - Milestone validation frameworks and important status reports
- **governance/** - Compliance and audit documentation  
- **Important .md files** - Development plans, assessments, documentation meant to be kept

## logs/ (Git-ignored temporary and automated output)
- **Diagnostic outputs** - ha_bb8_diagnostics_*.tar.gz files
- **STP4 evidence** - Timestamped evidence collection runs
- **Receipt files** - *_receipt.txt automated confirmations
- **Log files** - *.log automated execution logs  
- **Verification outputs** - Temporary validation results
- **JSON/XML artifacts** - Automated tool outputs

## Canonical Locations
- **INT-HA-CONTROL framework**: `reports/checkpoints/INT-HA-CONTROL/`
- **Diagnostics script**: `ops/diag/collect_ha_bb8_diagnostics.sh` 
- **Coverage files**: `addon/.coverage*` (with addon-specific tests)
- **Status scripts**: `reports/checkpoints/INT-HA-CONTROL/`

## .gitignore Configuration
```
# Workspace organization: logs/ (untracked) vs reports/ (tracked important docs)
logs/
logs/**
# Keep reports/ tracked for important documentation  
reports/**
!reports/
!reports/checkpoints/
!reports/checkpoints/**
!reports/*.md
```