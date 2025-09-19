#!/usr/bin/env bash
set -euo pipefail

## Wrapper for ADR validator. CI and pre-commit expect scripts/validate_adrs.sh
## Delegate to ops/ADR/validate_adrs.sh which contains the canonical implementation.

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT="$DIR/.."
exec bash "$ROOT/ops/ADR/validate_adrs.sh" "$@"
