import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
# ascend to repo root (detect .git OR both addon/.vscode)
cur = ROOT
for _ in range(10):
    if (cur / ".git").exists() or (
        (cur / "addon").exists() and (cur / ".vscode").exists()
    ):
        ROOT = cur
        break
    cur = cur.parent


def find_one(name):
    hits = [
        p
        for p in ROOT.rglob(name)
        if not any(
            x in p.parts
            for x in (
                ".venv",
                ".tox",
                ".git",
                "dist",
                "build",
                "reports",
                "services.d",
                "docs",
            )
        )
    ]
    return hits


errors = []
pytest_cfg = find_one("pytest.ini")
ruff_cfg = find_one("ruff.toml")
mypy_ini = find_one("mypy.ini") or find_one("mypy")
pyproject = (
    list((ROOT / "pyproject.toml",)) if (ROOT / "pyproject.toml").exists() else []
)
print("ROOT:", ROOT)
print("pytest.ini:", [str(p.relative_to(ROOT)) for p in pytest_cfg])
print("ruff.toml:", [str(p.relative_to(ROOT)) for p in ruff_cfg])
print("mypy.ini/mypy:", [str(p.relative_to(ROOT)) for p in mypy_ini])
print("pyproject.toml:", [str(p.relative_to(ROOT)) for p in pyproject])
if len(pytest_cfg) != 1:
    errors.append(f"Expected exactly 1 pytest.ini, found {len(pytest_cfg)}")
if len(ruff_cfg) != 1:
    errors.append(f"Expected exactly 1 ruff.toml, found {len(ruff_cfg)}")
# mypy: allow either mypy.ini OR [tool.mypy] in pyproject, but not both
has_mypy_ini = len(mypy_ini) == 1
has_toml_mypy = False
if pyproject:
    txt = (pyproject[0]).read_text()
    has_toml_mypy = bool(re.search(r"^\[tool\.mypy\]", txt, re.M))
    # also reject duplicate pytest/ruff sections in pyproject
    if re.search(r"^\[tool\.pytest\.ini_options\]", txt, re.M):
        errors.append(
            "pyproject.toml contains [tool.pytest.ini_options] (should be removed)"
        )
    if re.search(r"^\[tool\.ruff(\.|$)]", txt, re.M):
        errors.append("pyproject.toml contains [tool.ruff*] (should be removed)")
if has_mypy_ini and has_toml_mypy:
    errors.append(
        "Both mypy.ini and [tool.mypy] present—keep only one (recommend mypy.ini)."
    )
if not has_mypy_ini and not has_toml_mypy:
    errors.append("No mypy config found—add mypy.ini or [tool.mypy].")
if errors:
    print("CONFIG ERRORS:")
    [print(" -", e) for e in errors]
    sys.exit(1)
print("CONFIG OK")
