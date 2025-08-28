---
title: ADR-0001: Canonical Topology — Dual-Clone via Git Remote
date: 2025-08-23
status: Approved
---

# ADR-0001: Canonical Topology — Dual-Clone via Git Remote

## Table of Contents
1. Git Repo Structure & Publishing
2. Backup Storage Decision
3. Addenda
   - Deploy (v4)
   - Remote HEAD (v3)
   - Runtime Artifacts (v1)
   - Canonical Paths & Directory Rules (v2)
4. Governance Tokens — Canonical Catalog
5. Last updated

## Git Repo Structure & Publishing (2025-08-23, Reinforced)

- `addon/` is **not** a git repo in the workspace. Do **not** run `git init` inside `addon/`; no `.git`, no submodules, no symlinks, no nested repos.
- All git operations are run from the workspace root (`HA-BB8/`).
- Publishing to the add-on repo uses `git subtree split -P addon` from the workspace root.
- Scripts and CI must reference `addon/` via pathspecs, e.g.:
	```bash
	WS_ROOT="$(git rev-parse --show-toplevel)"
	git -C "$WS_ROOT" status -- addon
	git -C "$WS_ROOT" diff origin/main -- addon
	git -C "$WS_ROOT" subtree split -P addon -b __addon_pub_tmp
	```
- Running git commands inside `addon/` will fail (no `.git`); this is expected and by design.
- Separation between workspace and add-on repo is handled at publish time (subtree) and at runtime (independent clone on HA).

**Status:** Approved. Supersedes symlink proposals.

**Notes:** Acceptance tokens: `WS_READY …`, `DEPLOY_OK …`, `VERIFY_OK …`, `STRUCTURE_OK`.

## Backup Storage Decision (2025-08-22):

- All workspace backups must be stored as folder tarballs inside the `_backups` directory.
- Good example: `_backups/_backups_20250821_034242.tar.gz` (single tarball file)
- Bad example: `_backups_20250821_071118Z` (loose backup folder, not tarballed)

**Addendum v4 (2025-08-23):** Deploy uses HA Core Services API (/api/services/hassio/addon_restart) authenticated via LLAT from /config/secrets.yaml (key ha_llat). Publisher is no-op tolerant: if no addon/ changes are present, publish is skipped and deploy proceeds.

**Addendum v3 (2025-08-22): Remote HEAD = Add-on Subtree**

- The GitHub repository `e-app-404/ha-bb8-addon`’s `main` branch contains **only** the add-on (the contents of `HA-BB8/addon`) at the repository root.
- Publishing from the workspace uses a subtree publish (archive/filter): export `HA-BB8/addon/` and force-push to `main`.
- Runtime clone `/addons/local/beep_boop_bb8` tracks `origin/main` and is hard-reset on deploy.
- **Forbidden at runtime (and in the add-on repo root):** `docs/`, `ops/`, `reports/`, `scripts/`, `.githooks/`, `.github/`, `_backups/`, and any nested `addon/`.
- **Acceptance Tokens:** `SUBTREE_PUBLISH_OK`, `CLEAN_RUNTIME_OK`, `DEPLOY_OK`, `VERIFY_OK`, `RUNTIME_TOPOLOGY_OK`.
- **Operational Note:** Workspace governance (CI/guards for `ops/`, `reports/`, etc.) applies to the workspace, not the add-on repo. The add-on repo enforces **add-on–only** structure.

**Addendum (2025-08-22): Runtime Artifacts & Clean Deploy**

- Runtime artifacts (logs, caches, reports) MUST live under the container’s `/data` (host: `/data/addons/data/<slug>`).
- The repo’s `addon/reports/` (and `addon/docs/reports/`) are template-only; generated content is ignored via `.gitignore`.
- The deploy step includes `git clean -fdx` on the runtime clone prior to reset to guarantee a clean runtime.
- Acceptance tokens now include `CLEAN_RUNTIME_OK` preceding `DEPLOY_OK`.

**Addendum v2 (2025-08-22): Canonical Paths & Directory Rules (reconciled with ADR-0004)**

- **Workspace**: keep `ops/`, `reports/`, `scripts/`, `docs/`, `.github/`, `_backups/`.  
- **Add-on minimal set**: `addon/config.yaml`, `addon/Dockerfile`, `addon/bb8_core/` (+ `addon/tests/` optional).  
- **CRTP (see ADR-0004)**: `addon/tools/` and `addon/scripts/` are **conditionally allowed** when referenced by Dockerfile/entry or whitelisted via markers; otherwise they belong in the workspace.  
- **Always forbidden in `addon/`**: nested `.git`, nested `addon/`, `docs/`, `ops/`, `reports/`.
- Runtime artifacts remain in container: `/data/...` (host: `/data/addons/data/<slug>/...`)

## Governance Tokens — Canonical Catalog
## Build Mode Semantics (informative)
Home Assistant Supervisor behavior:
- **LOCAL_DEV**: If `image:` is **absent** in `addon/config.yaml`, Supervisor **builds locally** from the add-on `Dockerfile`.
- **PUBLISH**: If `image:` is **present**, Supervisor **pulls** the specified image; ensure `version:` matches the tag published in the registry.
This ADR treats both modes as valid; guards and checkers must detect the mode and validate accordingly.
> Single source of truth for build/deploy/verify markers. All other docs must reference this section.

- **WS_READY** — Workspace prepared (structure, tools, wrappers validated).
- **STRUCTURE_OK** — `addon/` subtree conforms to ADR-0001 (no nested git; no workspace-only dirs).
- **SUBTREE_PUBLISH_OK** — `addon/` subtree published to add-on remote (typically via `git subtree`).
- **CLEAN_RUNTIME_OK** — Runtime add-on folder synchronized (no stray files; no `.git`).
- **DEPLOY_OK** — Supervisor successfully rebuilt the local image from runtime folder.
- **VERIFY_OK** — Runtime health checks passed (service starts; minimal probes succeed).
- **RUNTIME_TOPOLOGY_OK** — Runtime image/tag and path align with ADR-0001 expectations.

**CRTP-specific tokens** (defined by ADR-0004):
- **TOOLS_ALLOWED** — `addon/tools/` allowed per CRTP (referenced by Dockerfile/entry or marker present).
- **SCRIPTS_ALLOWED** — `addon/scripts/` allowed per CRTP.

**Conformance:** CI and scripts must emit exactly these token strings (all-caps with underscores) for machine parsing.

## Last updated

_Last updated: 2025-08-23_