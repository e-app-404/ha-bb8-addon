VENV_ACTIVATE = . .venv/bin/activate

.PHONY: test test-fast test-all

test: test-fast

test-fast:
	$(VENV_ACTIVATE) && pytest -q tests/ -k "not slow" --maxfail=5

test-all:
	$(VENV_ACTIVATE) && pytest -q tests/
