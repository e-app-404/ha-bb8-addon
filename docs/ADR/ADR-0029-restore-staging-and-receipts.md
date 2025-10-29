---
id: ADR-0029
title: Restore staging protocol and receipts
date: 2025-09-27
status: accepted
decision: '### Staging layout - Staging dir: _backups/restore_report/restore_staging/<UTC>/
  - Inventory/receipts: _backups/inventory/{manifest_*.txt,tree_*.txt,staged_manifest_*.json}
  _backups/inventory/restore_receipts/receipt_<UTC>.txt.'
author:
- Evert Appels
related:
- ADR-0015
- ADR-0026
- ADR-0028
supersedes: []
last_updated: 2025-09-27
tags:
- restore
- staging
- receipts
- protocol
- governance
- tokens
- normalization
- auditability
---

# ADR-0029: Restore staging protocol and receipts

## Context

We formalized a safe restore flow using a staging directory and explicit
receipts, to avoid destructive merges and to maintain auditability.

## Decision

### Staging layout

- Staging dir:  
`_backups/restore_report/restore_staging/<UTC>/`
- Inventory/receipts:  
`_backups/inventory/{manifest_*.txt,tree_*.txt,staged_manifest_*.json}`  
`_backups/inventory/restore_receipts/receipt_<UTC>.txt`

### Apply protocol

1. **Preview** (dry-run; list planned copies).
2. **Apply** with rsync, **always** backing up overwritten targets using:
- `--backup --suffix=".from_backup_<UTC>"`
3. **Write a receipt** containing:
- `receipt_ts`, `stage_dir`, action (`apply` or `noop`), branch, notes.
4. **Commit receipts (text only)** — never commit tarballs.

### Normalization

- Root stray manifests are deduped into inventory.
- Legacy suffixes (`*.bak`, `.perlbak`, `_backup`, `_restore`) are renamed to
`.bk.<UTC>` or corralled; content is retained.

## Consequences

- Restores are reproducible and reviewable.
- Every apply/no-op has a durable, textual receipt.

## Implementation notes

- The helper script uses BusyBox-compatible shell; no background writes.
- To revert, use the generated `.from_backup_<UTC>` files.

## Token Block

```yaml
TOKEN_BLOCK:
  accepted:
    - RESTORE_STAGING_OK
    - RECEIPT_PROTOCOL_OK
    - NORMALIZATION_OK
  drift:
    - DRIFT: restore_staging_failed
    - DRIFT: receipt_missing
    - DRIFT: normalization_incomplete
```