# Development Setup


## Editable Install & Test/Coverage Setup

To install the addon in editable mode (so changes to the code are reflected immediately), run:

```sh
pip install -e ./addon
```

For development, testing, and coverage, install dev requirements:

```sh
pip install -r addon/requirements-dev.txt
```

This will link the package defined in `addon/pyproject.toml` for development and ensure pytest/pytest-cov are available.

## Editable install

To set up the addon in editable mode:

```sh
source .venv/bin/activate
pip install -e addon
pip install -r addon/requirements-dev.txt
```

After this, you can remove the PYTHONPATH line from your `.env` file, as the editable install handles import paths automatically.
