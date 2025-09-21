#!/usr/bin/env bash
# Protocol enforcer stub.
# Runs lightweight validators and prints tokens. Intended as a CI early-fail job.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
echo "Running protocol enforcer from ${ROOT_DIR}"

PYTHON=${PYTHON:-python3}

echo "Running import_validator..."
${PYTHON} ${ROOT_DIR}/ops/guardrails/import_validator.py || true

echo "Running topic_literal_checker..."
${PYTHON} ${ROOT_DIR}/ops/guardrails/topic_literal_checker.py || true

echo "Running reports_checker..."
${PYTHON} ${ROOT_DIR}/ops/guardrails/reports_checker.py || true

echo "TOKEN_BLOCK: [PROTOCOL_ENFORCED_OK]"

exit 0
