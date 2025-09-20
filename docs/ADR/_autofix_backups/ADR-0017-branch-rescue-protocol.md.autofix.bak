---
title: "ADR-0017: Branch & Rescue Protocol"
date: 2025-09-13
status: Draft
author:
  - Promachos Governance
related:
  - ADR-0018
  - ADR-0009
supersedes: []
last_updated: 2025-09-13
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

## 7. Token Blocks
```yaml
TOKEN_BLOCK:
  accepted:
    - BRANCH_RESCUE_OK
    - HISTORY_CLEAN_OK
  drift:
    - DRIFT: unrelated_history
    - DRIFT: rescue_without_receipt
```

