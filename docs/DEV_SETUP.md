# Development Setup

## Editable Install

To install the addon in editable mode (so changes to the code are reflected immediately), run:

```sh
pip install -e ./addon
```

This will link the package defined in `addon/pyproject.toml` for development.

## Editable install

To set up the addon in editable mode:

```sh
source .venv/bin/activate
pip install -e addon
```

After this, you can remove the PYTHONPATH line from your `.env` file, as the editable install handles import paths automatically.
