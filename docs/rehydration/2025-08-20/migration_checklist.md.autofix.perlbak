## 3.2 Migration checklist (concise)

* Create **`addon/`** as the workspace add‑on clone (bind to remote).
* Ensure **runtime clone** at `/Volumes/HA/addons/local/beep_boop_bb8` tracks the same remote.
* Merge **`HA-BB8/bb8_core` → `addon/bb8_core`** (if sources present), then remove `HA-BB8/bb8_core`.
* Create **`ops/`**; move operational scripts from `scripts/`, `tools/`, `tests/`, and any `addon/ops/` into `ops/`.
* Keep wrappers in **`scripts/`**; wrappers export `WORKSPACE_ROOT` and `REPORT_ROOT`.
* Ensure **`reports/`** exists; remove any alternative report sinks under the add‑on tree.
* Add **helper scripts** (names only specified above) and a short **ADR** file in `docs/adr/`.
* **Deploy** (push workspace; runtime fetch+hard‑reset) and emit acceptance tokens.
