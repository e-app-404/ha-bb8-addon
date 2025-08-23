
# ADR-0001: Canonical Topology — Dual-Clone via Git Remote (Short)

**Decision (2025-08-21):**
- Workspace clone at `HA-BB8/addon/` (no symlinks, no submodules)
- Runtime clone at `/addons/local/beep_boop_bb8`
- Deploy = push (workspace) → fetch+hard-reset (runtime), then restart add-on in HA
- Single report sink via `REPORT_ROOT` exported by wrappers
- Operational tools live under `HA-BB8/ops/` (not inside `addon/`)

**Status:** Approved. Supersedes symlink proposals.

**Notes:** Acceptance tokens: `WS_READY …`, `DEPLOY_OK …`, `VERIFY_OK …`, `STRUCTURE_OK`.

**Backup Storage Decision (2025-08-22):**
- All workspace backups must be stored as folder tarballs inside the `_backups` directory.
- Good example: `_backups/_backups_20250821_034242.tar.gz` (single tarball file)
- Bad example: `_backups_20250821_071118Z` (loose backup folder, not tarballed)
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


**Addendum v2 (2025-08-22): Canonical Paths & Directory Rules**
Effective immediately:

- Workspace must-have (root): `ops/`, `reports/`, `scripts/`, `docs/`, `.githooks/`, `.github/`, `_backups/`
- Workspace must-not (root): `tests/`, `tools/`, `_backup/` (old name), any `*_backup_*` loose folders
- Add-on must-have: `addon/bb8_core/`, `addon/tools/`, `addon/tests/`, `addon/services.d/`, `addon/app/`, `addon/.devcontainer/`, and core files: `addon/config.yaml`, `addon/Dockerfile`, `addon/Makefile`, `addon/README.md`, `addon/VERSION`, `addon/apparmor.txt`
- Add-on must-not: `addon/scripts/`, `addon/reports/`, `addon/docs/`, `addon/_backup*/`, env caches (`.venv`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`)
- Runtime artifacts remain in container: `/data/...` (host: `/data/addons/data/<slug>/...`)
