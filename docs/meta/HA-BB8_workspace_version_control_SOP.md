
# HA-BB8 Workspace & Version Control SOP (Standard Operating Procedure)

## 1. Directory Roles

- **Repo of Record:** `HA-BB8/addon` — This is the deployable source.
- **Runtime Clone (HA mount):** `/Volumes/addons/local/beep_boop_bb8` — Not a source of truth except for explicit one-time imports.
- **Workspace-only:** `ops/`, `reports/`, `docs/`, `scripts/`, `tools/` — Local use only; do not deploy or version under `addon/`.

---

## 2. Normal Workflow (Editing `addon/`)

0 Activate virtual environment:
	```bash
	source .venv/bin/activate  
	```
1. Run tests:
	```bash
	python3 -m pytest -q /Users/evertappels/Projects/HA-BB8/addon/tests || exit 1
	```
2. Commit and push changes:
	```bash
	git -C /Users/evertappels/Projects/HA-BB8/addon add -A
	git -C /Users/evertappels/Projects/HA-BB8/addon commit -m "feat/fix: <message>"
	git -C /Users/evertappels/Projects/HA-BB8/addon push origin HEAD:main
	```
3. Sync runtime:
	```bash
	git -C /Volumes/addons/local/beep_boop_bb8 fetch --all --prune
	git -C /Volumes/addons/local/beep_boop_bb8 checkout -B main origin/main
	git -C /Volumes/addons/local/beep_boop_bb8 reset --hard origin/main
	```
4. Emit tokens:
	```bash
	WSH=$(git -C /Users/evertappels/Projects/HA-BB8/addon rev-parse --short HEAD)
	RTH=$(git -C /Volumes/addons/local/beep_boop_bb8 rev-parse --short HEAD)
	echo "DEPLOY_OK runtime_head=${RTH} branch=main"
	echo "VERIFY_OK ws_head=${WSH} runtime_head=${RTH} remote=$(git -C /Users/evertappels/Projects/HA-BB8/addon remote get-url origin)"
	echo "STRUCTURE_OK"
	echo "WS_READY addon_ws=git_clone_ok runtime=git_clone_ok reports=ok wrappers=ok ops=ok"
	```
5. If version bumped, update `addon/config.yaml` and `CHANGELOG.md`, then (optional) tag:
	```bash
	git -C /Users/evertappels/Projects/HA-BB8/addon tag -a vYYYY.MM.DD -m "Release YYYY.MM.DD"
	git -C /Users/evertappels/Projects/HA-BB8/addon push --tags
	```

---

## 3. If You Accidentally Edited the Runtime (HA mount)

**Preferred (discard runtime edits):**
```bash
git -C /Volumes/addons/local/beep_boop_bb8 fetch --all --prune
git -C /Volumes/addons/local/beep_boop_bb8 reset --hard origin/main
git -C /Volumes/addons/local/beep_boop_bb8 clean -fdX
```

**Exception (accept runtime edits as canonical one-time import):**
```bash
git -C /Volumes/addons/local/beep_boop_bb8 add -A
git -C /Volumes/addons/local/beep_boop_bb8 commit -m "hotfix: accept runtime edits as canonical"
git -C /Volumes/addons/local/beep_boop_bb8 push origin HEAD:main

git -C /Users/evertappels/Projects/HA-BB8/addon fetch --all --prune
git -C /Users/evertappels/Projects/HA-BB8/addon checkout -B main origin/main
git -C /Users/evertappels/Projects/HA-BB8/addon reset --hard origin/main
```
Then run the normal workflow to confirm alignment.

---

## 4. Workspace-only Areas (`ops/`, `docs/`, `reports/`, `scripts/`, `tools/`)

- Do not deploy to HA runtime.
- Intentionally ignored by `.gitignore` in the addon repo.
- If versioning is needed, use a separate repo for workspace automation. Never re-add under `addon/`.

---

## 5. Quick Health Checks

```bash
for d in docs ops reports scripts tools addon .github; do test ! -d /Users/evertappels/Projects/HA-BB8/addon/$d; done && echo "[repo ok]"
for d in docs ops reports scripts tools addon .github; do test ! -d /Volumes/addons/local/beep_boop_bb8/$d; done && echo "[runtime ok]"
python3 -m pytest -q /Users/evertappels/Projects/HA-BB8/addon/tests && echo "[tests ok]"
```

---

## 6. If `git push` Is Rejected (Diverged)

```bash
git -C /Users/evertappels/Projects/HA-BB8/addon fetch --all --prune
git -C /Users/evertappels/Projects/HA-BB8/addon rebase origin/main   # resolve conflicts, keep .gitignore guards intact
git -C /Users/evertappels/Projects/HA-BB8/addon push origin HEAD:main
```

---

## 7. HA Add-on Restart

If your deploy script doesn’t auto-restart, restart the add-on from HA UI or wire the restart into your deploy wrapper. The runtime reset already points to the new commit.

---

## 8. Ground Rules

- **Deploy:** Push workspace → runtime (`fetch`, `checkout -B main origin/main`, `reset --hard`).
- **Never** reintroduce `addon/{docs,ops,reports,scripts,tools,addon,.github}` (guarded by `.gitignore`).
- **Tests first, tokens last:** Always verify with `STRUCTURE_OK`, `VERIFY_OK`, `WS_READY`, `DEPLOY_OK`.
