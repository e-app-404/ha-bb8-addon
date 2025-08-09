PYTHON=python3

.PHONY: test lint

test:
	PYTHONPATH=. pytest --maxfail=1 --disable-warnings

lint:
	PYTHONPATH=. ruff .
	PYTHONPATH=. flake8 .
