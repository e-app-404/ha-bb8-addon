---
title: "ADR-0007: Restore add-on working tree into ./addon (Canonical) (legacy)"
date: 2025-08-26
status: Informational
author:
  - Promachos Governance
related:
  - ADR-0001
supersedes: []
last_updated: 2025-08-26
---

# Restore add-on working tree into ./addon (Canonical)

## Table of Contents
1. Source of truth
2. Preferred restore (from GitHub)
3. Emergency restore (from HA runtime clone)
4. Hard rules
5. Rationale
6. Last updated

## Source of truth

The GitHub add-on repo (`e-app-404/ha-bb8-addon`, branch `main`) published via `git subtree split -P addon` from the workspace. The workspace `addon/` is **not** a git repo (no `.git`), per `ADR-0001`.

## Preferred restore (from GitHub)
```sh
# From workspace root (HA-BB8/)
git fetch origin
# Update your workspace normally first…
# If you need to reset addon/ to GitHub’s add-on repo state:
git subtree pull --prefix addon https://github.com/e-app-404/ha-bb8-addon.git main --squash
```

## Emergency restore (from HA runtime clone)

- Use only if GitHub is temporarily unavailable.
- Pull files over SSH from the HA host runtime clone
- **IMPORTANT**: do NOT bring the runtime’s `.git` into `addon/`

```
rsync -avz --delete --exclude='.git' \
	babylon-babes@home-assistant:/addons/local/beep_boop_bb8/ \
	addon/
```

## Hard rules

- Do not `git init` inside `addon/` (no nested repos).
- All git commands run from the workspace root; addon/ is a normal tracked dir.
- After emergency restore, commit from the workspace root and re-publish via subtree.

## Rationale

> Rationale: aligns with ADR-0001 (no nested `.git` in `addon/`, subtree publish) and current runtime path `/addons/local/beep_boop_bb8`.

## Token Blocks

```yaml
TOKEN_BLOCK:
  accepted: []
  drift: []
```