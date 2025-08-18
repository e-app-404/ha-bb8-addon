# Run from repo root
set -euo pipefail
mkdir -p reports

# Runtime env (adjust if needed)
export MQTT_BASE=bb8 REQUIRE_DEVICE_ECHO=1 ENABLE_BRIDGE_TELEMETRY=1 EVIDENCE_TIMEOUT_SEC=3.0
export PYTHONWARNINGS=default

# Formatting & lint (tee logs)
black --check .                         2>&1 | tee reports/black.log
ruff check .                            2>&1 | tee reports/ruff.log

# Types
mypy --install-types --non-interactive . 2>&1 | tee reports/mypy.log

# Tests + coverage, with rich logging to console and file
pytest -q --maxfail=1 --disable-warnings \
  --cov=bb8_core --cov-report=term-missing \
  -o log_cli=true --log-cli-level=INFO \
  --log-file=reports/pytest.log --log-file-level=DEBUG \
  --log-date-format="%Y-%m-%d %H:%M:%S" \
  --log-format="%(asctime)s %(levelname)s:%(name)s: %(message)s" \
  2>&1 | tee -a reports/pytest.log

# Security (non-blocking; still logged)
bandit -q -r bb8_core         2>&1 | tee reports/bandit.log || true
safety check --full-report    2>&1 | tee reports/safety.log || true
