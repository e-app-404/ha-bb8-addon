---
id: "OPS-REORG-001"
title: "ops/ Directory Reorganization Plan"
authors: "HA-BB8 Maintainers"
slug: "ops-directory-reorganization-plan"
tags: ["ops", "directory", "reorganization", "workflow"]
date: "2025-10-27"
last_updated: "2025-10-27"
url: ""
related: ""
adr: ""
---

# ops/ Directory Reorganization Plan

## Current Analysis

### Current Structure Issues

1. **Inconsistent naming**: Some scripts use underscores, others use hyphens.
2. **Unclear hierarchy**: Scripts with similar purposes are scattered across directories.
3. **Missing documentation**: No clear index or purpose documentation for each directory.
4. **Workflow gaps**: No clear execution order or dependency management.

### Current Directory Analysis

#### Well-Organized Directories

- `ops/release/` — Clear purpose: version management and deployment
- `ops/diag/` — Clear purpose: diagnostics collection
- `ops/ADR/` — Clear purpose: Architecture Decision Record management

#### Needs Improvement

- `ops/workspace/` — Mixed purposes: deployment, cleanup, validation, setup
- `ops/evidence/` — Mixed with workspace operations
- `ops/audit/` — Overlaps with `qa/` and `guardrails/`
- `ops/qa/` — Minimal content, overlaps with `audit/`
- `ops/guardrails/` — Single script, could be consolidated

#### Problematic

- Root-level scripts in `ops/` — No clear categorization
- `ops/dev/` — Single script, unclear if it belongs in dev workflow

## Proposed Reorganization

### 1. Core Workflow Directories (Keep & Enhance)

#### `ops/release/`

**Purpose**: Version management, publishing, deployment

**Scripts**:

- `bump_version.sh`
- `deploy_ha_over_ssh.sh`
- `publish_addon_archive.sh` (move from `workspace/`)

#### `ops/build/` (New)

**Purpose**: Compilation, testing, CI/CD pipeline

**Scripts**:

- `compile_test_gate_bleep.sh` (move from `dev/`)
- `qa_pipeline.sh` (new wrapper)
- `coverage_check.sh` (extract from existing)

#### `ops/deploy/` (New)

**Purpose**: Deployment orchestration and environment management

**Scripts**:

- `deploy_dual_clone.sh` (move from root)
- `deploy_workspace.sh` (move from `workspace/`)
- `accept_runtime_canonical.sh` (move from `workspace/`)

### 2. Management & Maintenance (Consolidate)

#### `ops/workspace/` (Refactor)

**Purpose**: Workspace setup, maintenance, validation

**Scripts**:

- `one_shot_setup.sh`
- `ws_ops.sh`
- `fix_wrappers.sh`
- `symlink_purge.sh`
- Remove: deployment scripts (→ `ops/deploy/`)
- Remove: publishing scripts (→ `ops/release/`)

#### `ops/validation/` (New — Consolidate `audit/`, `qa/`, `guardrails/`)

**Purpose**: Code quality, structure validation, compliance

**Scripts**:

- `check_structure.sh` (from `audit/`)
- `verify_addon.sh` (from `guardrails/`)
- `discovery_align_audit.py` (from `audit/`)
- `qa_harvest.py` (from `qa/`)
- `shape_guard.py` (from `guardrails/`)

### 3. Operational Support (Keep & Enhance)

#### `ops/diag/`

**Purpose**: Diagnostics and troubleshooting

**Scripts**:

- `collect_ha_bb8_diagnostics.sh`

#### `ops/evidence/`

**Purpose**: Evidence collection and attestation

**Scripts**:

- `evidence_preflight.sh`
- `run_evidence_stp4.sh`
- `collect_stp4.py`

#### `ops/ADR/`

**Purpose**: Architecture Decision Record management

**Scripts**:

- `generate_adr_index.sh`
- `validate_adrs.sh`
- `validate_cross_repo_links.sh`

### 4. Utilities & Support (New)

#### `ops/utils/` (New)

**Purpose**: General utilities and helper scripts

**Scripts**:

- `check_workspace_quiet.sh` (move from root)
- `copilot_baseline_artifacts.sh` (move from root)
- `index_generator.sh` (new — generates `README.md` for each dir)

## Implementation Plan

### Phase 1: Create New Directory Structure

- Create `ops/build/`, `ops/deploy/`, `ops/validation/`, `ops/utils/`
- Add `README.md` to each directory explaining purpose and usage

### Phase 2: Move Scripts Logically

- Move scripts according to the plan above
- Update any internal path references
- Update Makefile references to new paths

### Phase 3: Standardization

- Standardize script naming (prefer hyphens over underscores)
- Add consistent header format to all scripts
- Add usage documentation to each script

### Phase 4: Create Master Index

- Create `ops/README.md` with complete directory overview
- Create `ops/WORKFLOW.md` showing execution order and dependencies
- Add script interdependency mapping

## Benefits

- **Clear Purpose**: Each directory has a single, well-defined purpose
- **Logical Workflow**: Scripts grouped by when/how they're used
- **Easier Navigation**: Developers can quickly find relevant scripts
- **Better Maintenance**: Related scripts are co-located
- **Improved Documentation**: Each directory self-documents its purpose
- **Workflow Clarity**: Clear separation between build, deploy, validate, maintain

## Script Migration Map

```text
OLD LOCATION                              → NEW LOCATION
ops/dev/compile_test_gate_bleep.sh        → ops/build/compile_test_gate_bleep.sh
ops/deploy_dual_clone.sh                  → ops/deploy/deploy_dual_clone.sh
ops/workspace/deploy_workspace.sh         → ops/deploy/deploy_workspace.sh
ops/workspace/publish_addon_archive.sh    → ops/release/publish_addon_archive.sh
ops/audit/check_structure.sh              → ops/validation/check_structure.sh
ops/guardrails/verify_addon.sh            → ops/validation/verify_addon.sh
ops/qa/qa_harvest.py                      → ops/validation/qa_harvest.py
ops/check_workspace_quiet.sh              → ops/utils/check_workspace_quiet.sh
ops/copilot_baseline_artifacts.sh         → ops/utils/copilot_baseline_artifacts.sh
```

## Backward Compatibility

- Maintain symbolic links from old locations during transition
- Update Makefile gradually
- Add deprecation warnings to moved scripts
- Full migration timeline: 2–3 releases
