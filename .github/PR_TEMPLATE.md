# Pull Request Checklist

Please confirm the following before requesting review:

- [ ] No references to `.venv_new`, `local.mac.beep_boop_bb8`, or `PYTHONPATH=` remain
- [ ] Single source of truth for pytest/ruff/mypy configs
- [ ] `.env` reviewed; optional editable-install note addressed
- [ ] Makefile uses `.venv` consistently for Python
- [ ] VS Code search excludes and watcher excludes updated
- [ ] Sanity scripts (`tools/env_sanity.py`, `tools/check_configs.py`) pass
