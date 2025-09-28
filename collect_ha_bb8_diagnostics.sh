#!/bin/bash
# Wrapper for backwards compatibility. The real diagnostics script moved to ops/diag/
set -euo pipefail

echo "This script moved to ops/diag/collect_ha_bb8_diagnostics.sh"
echo "Invoking the new script with the same arguments..."
exec "$(pwd)/ops/diag/collect_ha_bb8_diagnostics.sh" "$@"