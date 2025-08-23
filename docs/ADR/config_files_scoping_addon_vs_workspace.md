Here’s a decisive mapping of each item to **addon-scoped** vs **workspace-scoped**, based on ADR-0001 (+ addenda) and your current layout goals.

## Classification

### Addon-scoped (should live under `addon/`)

These are the add-on’s packaging, runtime, Python config, and docs that ship with the container.

* `__init__.py` → `addon/__init__.py` (or remove if not needed)
* `.dockerignore` → `addon/.dockerignore`
* `apparmor.txt` → `addon/apparmor.txt`
* `CHANGELOG.md` → `addon/CHANGELOG.md`
* `config.yaml` → `addon/config.yaml`
* `Dockerfile` → `addon/Dockerfile`
* `Makefile` *(build for the add-on image)* → `addon/Makefile`
* `mypy.ini` → `addon/mypy.ini`
* `pyproject.toml` → `addon/pyproject.toml`
* `pytest.ini` → `addon/pytest.ini`
* `README.md` *(the add-on’s README)* → `addon/README.md`
* `requirements-dev.in` → `addon/requirements-dev.in`
* `requirements-dev.txt` → `addon/requirements-dev.txt` *(already present in `addon/` — keep here)*
* `requirements.in` → `addon/requirements.in`
* `requirements.txt` → `addon/requirements.txt`
* `ruff.toml` → `addon/ruff.toml`
* `run.sh` → `addon/run.sh`
* `VERSION` → `addon/VERSION`

### Workspace-scoped (stay at repo root)

These describe/operate the **workspace**, not the packaged add-on.

* `.editorconfig`
* `.evidence.env`
* `.gitignore`
* `.gitignore.bak` *(temporary/cleanup artifact; safe to delete)*
* `.HA_ADDON_README.md` *(boundary marker for ADR-0001)*
* `.DS_Store` *(shouldn’t be tracked; keep ignored in `.gitignore`)*
* `stp4_evidence_rerun.log` *(artifact; move under `reports/` or delete)*

### Note on `README.md`

* If this **README** is the add-on’s user doc → **addon-scoped** (move to `addon/README.md`).
* If it’s a workspace meta-README → **workspace-scoped** (keep at root) **and** ensure a separate `addon/README.md` exists for the add-on.

---

## Quick “fix it” block (Copilot-ready)

Run at the **workspace root**:

```bash
# Create addon/ if needed
mkdir -p addon

# Move add-on files into addon/
git mv -k __init__.py addon/ 2>/dev/null || true
git mv -k .dockerignore addon/ 2>/dev/null || true
git mv -k apparmor.txt addon/ 2>/dev/null || true
git mv -k CHANGELOG.md addon/ 2>/dev/null || true
git mv -k config.yaml addon/ 2>/dev/null || true
git mv -k Dockerfile addon/ 2>/dev/null || true
git mv -k Makefile addon/ 2>/dev/null || true
git mv -k mypy.ini addon/ 2>/dev/null || true
git mv -k pyproject.toml addon/ 2>/dev/null || true
git mv -k pytest.ini addon/ 2>/dev/null || true
git mv -k requirements-dev.in addon/ 2>/dev/null || true
git mv -k requirements.in addon/ 2>/dev/null || true
git mv -k requirements.txt addon/ 2>/dev/null || true
git mv -k ruff.toml addon/ 2>/dev/null || true
git mv -k run.sh addon/ 2>/dev/null || true
git mv -k VERSION addon/ 2>/dev/null || true

# Handle README: move only if this is the add-on README
# (skip if it is a workspace README)
if grep -qi 'home assistant add-on\|configuration\|options\|installation' README.md 2>/dev/null; then
  git mv -k README.md addon/ || true
fi

# Workspace hygiene
mkdir -p reports
[ -f stp4_evidence_rerun.log ] && git mv -k stp4_evidence_rerun.log reports/ || true
[ -f .gitignore.bak ] && git rm -f .gitignore.bak || true

git add -A
git commit -m "ADR-0001: relocate add-on files under addon/; keep workspace files at root"
```

**After this**, your structure will align with ADR-0001:

* **Workspace**: `ops/`, `docs/`, `reports/`, `scripts/`, `.githooks/`, `.github/`, `_backups/`, etc.
* **Add-on**: **everything that defines the container** under `addon/` (including Python/tooling configs and packaging files).

If you want, I can emit a follow-up guard that fails CI if any of those add-on files reappear at the root again.
