# ADR-0001: Canonical Topology — Dual-Clone via Git Remote (Short)

**Decision (2025-08-21):**
- Workspace clone at `HA-BB8/addon/` (no symlinks, no submodules)
- Runtime clone at `/Volumes/addons/local/beep_boop_bb8`
- Deploy = push (workspace) → fetch+hard-reset (runtime), then restart add-on in HA
- Single report sink via `REPORT_ROOT` exported by wrappers
- Operational tools live under `HA-BB8/ops/` (not inside `addon/`)

**Status:** Approved. Supersedes symlink proposals.

**Notes:** Acceptance tokens: `WS_READY …`, `DEPLOY_OK …`, `VERIFY_OK …`, `STRUCTURE_OK`.

**Backup Storage Decision (2025-08-22):**
- All workspace backups must be stored as folder tarballs inside the `_backup` directory.
- Good example: `_backup/_backup_20250821_034242.tar.gz` (single tarball file)
- Bad example: `_backup_20250821_071118Z` (loose backup folder, not tarballed)

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
