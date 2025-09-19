**HANDOFF NOTE → Strategos**

**Mission:** Manage the transition from current HA‑BB8 layout to the canonical dual‑clone topology (no symlinks). You will emit **one** copy‑paste Copilot block with built‑in acceptance tokens. I (Evert) will paste your block to Copilot and return its raw output back to you.

---

## Scope & ADR

* **ADR‑0001 (effective):** *Canonical Topology — Dual‑Clone via Git Remote*

  * Workspace clone: `HA-BB8/addon` (normal git clone)
  * Runtime clone: `/Volumes/HA/addons/local/beep_boop_bb8` (same remote)
  * Deploy = push (workspace) → fetch+hard‑reset (runtime)
  * No symlinks, no submodules

---

## Inputs (constants)

* **Remote:** `git@github.com:e-app-404/ha-bb8-addon.git`
* **Workspace root:** `/Users/evertappels/Projects/HA-BB8` → “WS”
* **Workspace addon (target):** `/Users/evertappels/Projects/HA-BB8/addon`
* **Runtime addon (HA mount):** `/Volumes/HA/addons/local/beep_boop_bb8`
* **Wrappers:** `WS/scripts`
* **Ops (target):** `WS/ops`
* **Reports root:** `WS/reports` (exported as `REPORT_ROOT`)

---

## Target Workspace Shape (what you must produce)

```
HA-BB8/
├─ addon/                  # clean add-on repo clone ONLY
│  ├─ bb8_core/            # source code here (no duplicate at WS root)
│  └─ standard add-on files (config.yaml, requirements.txt, etc.)
├─ ops/                    # operational tools (NOT inside addon/)
├─ scripts/                # wrappers that call into ops/; export REPORT_ROOT
├─ reports/                # single report sink
├─ docs/
├─ mypy.ini  pyproject.toml  pytest.ini  ruff.toml
```

**Invariants:**

* `addon/ops` **must not exist** after consolidation.
* `HA-BB8/bb8_core` at WS root **must not exist** after merge (content lives in `addon/bb8_core`).
* `reports/` is the **only** report sink (wrappers export `REPORT_ROOT=WS/reports`).

---

## Current Workspace Shape (as observed)

```
HA-BB8/
├─ _backup_20250821_034242/
├─ _backup_20250821_042444/
├─ _backup_20250821_044155/
├─ _backup_20250821_044455/
├─ _backup_20250821_044910_addon_ws/   # prior addon content archived
├─ bb8_core/                            # contains __pycache__/... (compiled .pyc)
├─ docs/
├─ reports/
├─ scripts/
├─ tests/
├─ tools/
├─ mypy.ini  pyproject.toml  pytest.ini  ruff.toml
└─ (no addon/ directory currently)
```

**Gaps vs target:** missing `addon/` clone; missing `ops/`; stray `bb8_core/` at WS root; potential overlap between `scripts/` and `tools/`.

---

## Rehydration Seed (include in your Copilot block header)

```yaml
rehydration_seed:
  adr: ADR-0001  # Dual-Clone via Git Remote
  remote: git@github.com:e-app-404/ha-bb8-addon.git
  ws_root: /Users/evertappels/Projects/HA-BB8
  addon_ws: /Users/evertappels/Projects/HA-BB8/addon
  addon_runtime: /Volumes/HA/addons/local/beep_boop_bb8
  wrappers_root: /Users/evertappels/Projects/HA-BB8/scripts
  ops_root: /Users/evertappels/Projects/HA-BB8/ops
  reports_root: /Users/evertappels/Projects/HA-BB8/reports
  rules:
    - no_symlinks: true
    - no_submodules: true
    - preserve_existing_backups: true
    - no_placeholders: true
    - non_destructive_merges: true
    - move_all_operational_tools_to_ops: true
    - wrappers_export_REPORT_ROOT: true
    - remove_ws_root_bb8_core_after_merge: true
    - forbid_addon_ops_dir_at_finish: true
  phases:
    - P0: Preflight + backup snapshot (read-only)
    - P1: Create/normalize addon_ws as clean git clone of remote
    - P2: Normalize addon_runtime to same remote
    - P3: Merge WS bb8_core (if sources present) -> addon/bb8_core; then remove WS/bb8_core
    - P4: Create ws_root/ops and relocate operational tools from scripts/tools/tests and any addon/ops -> ops
    - P5: Ensure wrappers in scripts/ export WORKSPACE_ROOT and REPORT_ROOT=reports_root
    - P6: Ensure reports_root exists; remove any alternate report sinks under addon/
    - P7: Deploy (push workspace; runtime fetch+hard-reset) + verification
```

---

## What your Copilot block must do (imperatives)

* **Create** `addon/` as a normal git clone of the remote (if absent).
* **Ensure** runtime path is a normal git clone of the same remote (fetch/reset only after push).
* **Merge** any source files from `WS/bb8_core/` into `addon/bb8_core/` (newer‑only), then **remove** `WS/bb8_core/` (archive first).
* **Create** `WS/ops/` and **relocate** all operational tools from `scripts/`, `tools/`, `tests/`, and any `addon/ops/` into `ops/`.
* **Leave** wrappers in `scripts/`; **prepend** `export WORKSPACE_ROOT` and `export REPORT_ROOT`.
* **Ensure** `reports/` exists and is the only report sink (fail if `addon/reports/` remains).
* **Install** helper stubs (you generate content):

  * `scripts/deploy_to_ha.sh` (push WS/addon branch; runtime fetch+hard‑reset same branch → print `DEPLOY_OK ...`)
  * `scripts/verify_workspace.sh` (print `VERIFY_OK ws_head=… runtime_head=… remote=…`)
  * `tools/check_structure.sh` (assert invariants → print `STRUCTURE_OK`)
* **Back up** anything you move/replace into a timestamped `_backup_*/` dir at WS root.
* **Do not** fabricate missing runtime files; instead, print `[missing] <path>` and stop.

---

## Output Contract (acceptance tokens)

Your Copilot block must end by echoing **all** of the following tokens on success:

1. `WS_READY addon_ws=git_clone_ok runtime=git_clone_ok reports=ok wrappers=ok ops=ok`
2. `DEPLOY_OK runtime_head=<sha> branch=<name>`
3. `VERIFY_OK ws_head=<sha> runtime_head=<sha> remote=git@github.com:e-app-404/ha-bb8-addon.git`
4. `STRUCTURE_OK`

**Hard checks (fail the run if violated):**

* `addon/` is a **git repo** (not a symlink; not a submodule).
* `/Volumes/HA/addons/local/beep_boop_bb8` is a git repo with same `origin`.
* `addon/ops` **does not exist** at finish.
* `WS/ops` **exists** and contains the relocated operational tools.
* `WS/scripts` contains wrappers only and they **export REPORT\_ROOT**.
* `WS/bb8_core` **absent** at finish (content merged into `addon/bb8_core`).
* `WS/reports` **exists** and is writable.

---

## Return flow

I will paste your Copilot block to Copilot. Copilot will run it and reply with raw console lines. I will forward those lines to you verbatim for validation against the **Output Contract** above.
