#!/usr/bin/env bash
set -euo pipefail

# Whitelist of allowed commands for LLM/Copilot
case "${SSH_ORIGINAL_COMMAND:-}" in
  "ha core info")                    exec ha core info ;;
  "ha addons info local_beep_boop_bb8") exec ha addons info local_beep_boop_bb8 ;;
  "ha addons logs local_beep_boop_bb8 --lines 200") exec ha addons logs local_beep_boop_bb8 --lines 200 ;;
  "bash /config/domain/shell_commands/addons_runtime_fetch.sh") exec bash /config/domain/shell_commands/addons_runtime_fetch.sh ;;
  # add other *exact* lines you permit, one per case pattern:
  # "ha addons restart local_beep_boop_bb8") exec ha addons restart local_beep_boop_bb8 ;;
  *)
    echo "DENIED: command not allowed for LLM" >&2
    exit 126
    ;;
esac
