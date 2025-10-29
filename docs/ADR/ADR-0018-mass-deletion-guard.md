---
id: ADR-0018
title: Mass-Deletion Guard
date: 2025-09-13
status: Draft
decision: '- Pre-push hook blocks pushes if deletions exceed 30% of total changes
  (adds + dels). - Users must explicitly commit intentional deletions and document
  them in reports/mass_deletion_receipt.txt.'
author:
- Promachos Governance
related:
- ADR-0017
- ADR-0009
- ADR-0023
supersedes: []
last_updated: 2025-09-13
---

# ADR-0018: Mass-Deletion Guard

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
Accidental mass deletions can cause catastrophic data loss. A pre-push guard is required to block pushes where deletions exceed a safe threshold.

## 2. Decision
- Pre-push hook blocks pushes if deletions exceed 30% of total changes (adds + dels).
- Users must explicitly commit intentional deletions and document them in `reports/mass_deletion_receipt.txt`.
- CI verifies the presence of receipts for any mass-deletion event.

## 3. Rationale
- Prevents accidental data loss and enforces review of destructive changes.
- Ensures traceability and auditability of mass deletions.

## 4. Consequences
- Accidental mass deletions are blocked before reaching remote.
- All intentional mass deletions are documented and auditable.

## 5. Enforcement
- Pre-push hook enforces deletion threshold.
- CI checks for mass-deletion receipts and explicit documentation.

## 6. Machine-Parseable Blocks
```yaml
MACHINE_BLOCK:
  type: mass-deletion-guard
  threshold: 30
  receipt: reports/mass_deletion_receipt.txt
```

## 7. Token Blocks
```yaml
TOKEN_BLOCK:
  accepted:
    - MASS_DELETION_OK
    - DELETION_RECEIPT_OK
  drift:
    - DRIFT: mass_deletion_blocked
    - DRIFT: missing_deletion_receipt
```