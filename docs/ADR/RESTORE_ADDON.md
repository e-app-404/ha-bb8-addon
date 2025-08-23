# Restore add-on working tree into ./addon (Canonical)

**Source of truth:** the GitHub add-on repo (`e-app-404/ha-bb8-addon`, branch `main`) published via `git subtree split -P addon` from the workspace. The workspace `addon/` is **not** a git repo (no `.git`), per ADR-0001.

## Preferred restore (from GitHub)
```sh
# From workspace root (HA-BB8/)
git fetch origin
# Update your workspace normally first…
# If you need to reset addon/ to GitHub’s add-on repo state:
git subtree pull --prefix addon https://github.com/e-app-404/ha-bb8-addon.git main --squash
```

Emergency restore (from HA runtime clone)

Use only if GitHub is temporarily unavailable.

# Pull files over SSH from the HA host runtime clone
# IMPORTANT: do NOT bring the runtime’s .git into addon/
rsync -avz --delete --exclude='.git' \
	babylon-babes@home-assistant:/addons/local/beep_boop_bb8/ \
	addon/

Hard rules

Do not git init inside addon/ (no nested repos).

All git commands run from the workspace root; addon/ is a normal tracked dir.

After emergency restore, commit from the workspace root and re-publish via subtree.


> Rationale: aligns with ADR-0001 (no nested `.git` in `addon/`, subtree publish) and current runtime path `/addons/local/beep_boop_bb8`. :contentReference[oaicite:8]{index=8}
