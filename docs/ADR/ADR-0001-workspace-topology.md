# ADR-0001: Canonical Topology — Dual-Clone via Git Remote (Short)

**Decision (2025-08-21):**
- Workspace clone at `HA-BB8/addon/` (no symlinks, no submodules)
- Runtime clone at `/Volumes/addons/local/beep_boop_bb8`
- Deploy = push (workspace) → fetch+hard-reset (runtime), then restart add-on in HA
- Single report sink via `REPORT_ROOT` exported by wrappers
- Operational tools live under `HA-BB8/ops/` (not inside `addon/`)

**Status:** Approved. Supersedes symlink proposals.

**Notes:** Acceptance tokens: `WS_READY …`, `DEPLOY_OK …`, `VERIFY_OK …`, `STRUCTURE_OK`.
