---
title: ADR-0006 Helper Functions Migration (legacy)
date: 2025-08-26
status: Informational
---

# Helper Functions Migration

## Table of Contents
1. Migration Summary
2. Update Instructions
3. Last updated

## Migration Summary

As of August 2025, all helper functions previously found in the flexible version of `verify_discovery.py` have been migrated to `addon/bb8_core/util.py` for consistency and maintainability. This ensures a single source of truth for shared utilities.

- Flexible `verify_discovery.py` removed.
- All helper functions (e.g., `get_any`, `first_identifiers`, `extract_cfg`) are now in `util.py`.
- Only the strict audit version remains in `tools/verify_discovery.py`.

## Update Instructions

Update your imports to use `from bb8_core.util import ...` for these helpers.

## Last updated

_Last updated: 2025-08-26_