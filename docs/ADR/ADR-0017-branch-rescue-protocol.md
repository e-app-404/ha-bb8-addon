---
id: ADR-0017
title: "Branch & Rescue Protocol"
date: 2025-09-13
status: Accepted
author:
  - "Promachos Governance"
related:
  - ADR-0018
  - ADR-0009
  - ADR-0033
  - ADR-0008
supersedes: []
last_updated: 2025-10-04
evidence_sessions:
  - 2025-10-04: "Active workspace content merge strategy implementation and branch canonicalization"
---

# ADR-0017: Branch & Rescue Protocol

## Table of Contents
1. Context
2. Decision
3. Rationale
4. Consequences
5. Enforcement
6. Machine-Parseable Blocks
7. Token Blocks
8. Last Updated

## 1. Context
Branch rescue is required after mass-deletion, merge conflicts, or accidental history divergence. Clean recovery and history hygiene are essential for governance and CI.

## 2. Decision
- Always create rescue branches off `origin/main`.
- Use cherry-pick for selective recovery; forbid unrelated histories.
- Document all rescue operations in `reports/branch_rescue_receipt.txt`.
- CI and hooks must block pushes with unrelated histories or unreviewed mass recovery.
- **Active Workspace Content Priority**: When merging development branches to main, prioritize operator-edited workspace content using `-X theirs` strategy.
- **Non-Destructive Merge Policy**: Require explicit approval for any merge involving mass deletions (>10 files).

## 3. Rationale
- Ensures traceable, auditable recovery.
- Prevents accidental history divergence and merge confusion.

## 4. Consequences
- All rescue branches are clean, auditable, and CI-compliant.
- History hygiene is enforced.

## 5. Enforcement
- Pre-push hook blocks unrelated histories.
- CI checks for rescue receipts and branch hygiene.

## 6. Machine-Parseable Blocks
```yaml
MACHINE_BLOCK:
  type: branch-rescue
  branch: rescue/20250913_mass_deletion
  source: origin/main
  cherry_picks:
    - commit: abcdef1
    - commit: 1234567
  receipt: reports/branch_rescue_receipt.txt
```

## 7. Active Workspace Content Merge Strategy (2025-10-04)

### Context

During the canonicalization of `development/production-ready-20250928` to `main`, we implemented an **active workspace content priority** merge strategy to ensure operator-edited content takes precedence over potentially stale main branch content.

### Strategy Implementation

**Pre-Merge Analysis:**
```bash
# Verified merge safety metrics
- 244 files changed: 47,215 insertions, 556 deletions
- 175 files added (new operational infrastructure)
- 1 file deleted (legitimate move: collect_ha_bb8_diagnostics.sh → ops/diag/)
- No mass deletions detected
- 9 commits ahead with clean development history
```

**Merge Command:**
```bash
git merge development/production-ready-20250928 -X theirs --no-edit
```

**Strategy Rationale:**
- **`-X theirs`**: Automatically resolve conflicts in favor of development branch (active workspace)
- **`--no-edit`**: Accept automated merge commit message to maintain audit trail
- **Fast-forward result**: No conflicts occurred, indicating clean development practices

### Decision Criteria

**Use Active Workspace Priority When:**
1. **Operator as Active Editor**: Development branch contains operator-driven changes
2. **Clean Development History**: No merge conflicts or tangled histories
3. **Safety Verified**: No mass deletions (>10 files) or unexpected file operations
4. **Workspace Integrity**: Key directories and files maintain expected structure

**Pre-Merge Safety Checks:**
```bash
# Directory structure validation
echo "--- KEY DIRECTORIES ---"; ls -la | grep '^d.*' | wc -l  # 17
echo "--- ADR COUNT ---"; ls docs/ADR/ADR-*.md | wc -l        # 42
echo "--- ADDON FILES ---"; ls addon/bb8_core/*.py | wc -l     # 35
echo "--- OPS STRUCTURE ---"; find ops -name "*.sh" | wc -l    # 36
```

**Post-Merge Verification:**
- ✅ All operational scripts maintain executable permissions
- ✅ Configuration files (VERSION, config.yaml) integrity preserved
- ✅ ADR documentation complete and properly formatted
- ✅ No unexpected file system changes or missing critical files

### Merge Strategy Matrix

| Scenario | Strategy | Rationale | Verification Required |
|----------|----------|-----------|----------------------|
| **Development → Main** | `-X theirs` | Operator workspace priority | Mass deletion check, structure validation |
| **Feature → Development** | Standard merge | Collaborative integration | Conflict resolution, code review |
| **Hotfix → Main** | Fast-forward preferred | Minimize history complexity | Emergency deployment validation |
| **Release → Production** | `--ff-only` | Ensure clean release history | Full integration testing |

### Governance Integration

**ADR Cross-References:**
- **ADR-0008**: Deployment flow supports workspace-priority merges
- **ADR-0033**: Dual-clone topology enables clean workspace isolation
- **ADR-0018**: Mass deletion guards prevent destructive operations

**Operational Evidence:**
- **Commit**: `95728de` - Successful active workspace merge with 244 files updated
- **Result**: Fast-forward merge with zero conflicts
- **Verification**: All critical infrastructure maintained and enhanced

## 8. Token Blocks
```yaml
TOKEN_BLOCK:
  accepted:
    - BRANCH_RESCUE_OK
    - HISTORY_CLEAN_OK
    - ACTIVE_WORKSPACE_MERGE_OK
    - NON_DESTRUCTIVE_MERGE_OK
    - WORKSPACE_INTEGRITY_OK
  produces:
    - CANONICAL_MAIN_BRANCH
    - OPERATOR_PRIORITY_INTEGRATION
    - CLEAN_MERGE_HISTORY
  requires:
    - MASS_DELETION_CHECK_PASS
    - WORKSPACE_STRUCTURE_VALIDATION
    - DEVELOPMENT_HISTORY_CLEAN
  drift:
    - DRIFT: unrelated_history
    - DRIFT: rescue_without_receipt
    - DRIFT: mass_deletion_detected
    - DRIFT: workspace_structure_corrupted
```

