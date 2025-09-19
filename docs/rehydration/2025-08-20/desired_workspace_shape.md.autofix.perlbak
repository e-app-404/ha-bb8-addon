# 1) Desired workspace shape (target)

**Architecture:** dual‑clone via Git remote (no symlinks, no submodules)

* **Remote**: `git@github.com:e-app-404/ha-bb8-addon.git`
* **Workspace clone**: `/Users/evertappels/Projects/HA-BB8/addon`
* **Runtime clone (HA mount)**: `/Volumes/HA/addons/local/beep_boop_bb8` (HA sees `/addons/local/beep_boop_bb8`)

**Top‑level tree (workspace)**

```
HA-BB8/
├─ addon/                     # the add-on repo clone ONLY
│  ├─ bb8_core/               # code merged here (no duplicate at WS root)
│  ├─ config.yaml
│  ├─ requirements.txt
│  └─ … (all add-on files)
├─ ops/                       # runtime ops & operational tools (NOT inside addon/)
├─ scripts/                   # wrappers; call into ops/
├─ reports/                   # single unified REPORT_ROOT
├─ docs/                      # workspace/meta docs
├─ mypy.ini
├─ pyproject.toml
├─ pytest.ini
└─ ruff.toml
```

**Invariants / rules**

* `addon/` contains **only** the add‑on repo content.
* **No** `addon/ops` directory (ops live in `HA-BB8/ops`).
* Wrappers in `scripts/` export `WORKSPACE_ROOT` and `REPORT_ROOT="$WS/reports"`.
* Reports are **only** under `HA-BB8/reports/`.
* No `HA-BB8/bb8_core` at the workspace root; it’s merged into `addon/bb8_core`.
* Both clones track the same remote; deploy = push (workspace) → fetch+hard‑reset (runtime).

---

# 2) Current workspace shape (as shown)

Source: screenshot of `HA-BB8/`.

**Observed top‑level**

```
HA-BB8/
├─ _backup_20250821_034242/
├─ _backup_20250821_042444/
├─ _backup_20250821_044155/
├─ _backup_20250821_044455/
├─ _backup_20250821_044910_addon_ws/         # prior addon/ content archived
├─ bb8_core/
│  └─ __pycache__/ … cpython-313.pyc files    # compiled artifacts present
├─ docs/
├─ reports/
├─ scripts/
├─ tests/
├─ tools/
├─ mypy.ini
├─ pyproject.toml
├─ pytest.ini
├─ ruff.toml
├─ HA-BB8_clean_20250821_071841.tar.gz
└─ stp4_evidence_rerun.log
```

**Key deltas vs target**

* **No `addon/` directory exists** (your prior `addon/` seems archived as `_backup_20250821_044910_addon_ws/`).
* **`bb8_core/` exists at workspace root** (should be inside `addon/bb8_core/`; also contains only `__pycache__` in view—source `.py` files may be elsewhere or were archived).
* **Multiple `_backup_*` directories** (good for safety; noisy for tooling).
* `ops/` directory **absent** at workspace root (required in target).
* `scripts/` and `tools/` both exist; likely contain overlapping operational content that should be consolidated to `ops/` (with wrappers left in `scripts/`).
* `reports/` exists (good); verify no other report sinks (e.g., `addon/reports/`) remain after consolidation.
