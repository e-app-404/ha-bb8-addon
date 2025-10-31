#!/bin/bash
# Simple shell test to see if container environment is stable

echo "SHELL_TEST: Starting shell test" >&2
echo "SHELL_TEST: Date: $(date)" >&2
echo "SHELL_TEST: Uptime: $(uptime)" >&2
echo "SHELL_TEST: Python version:" >&2
python3 --version >&2
echo "SHELL_TEST: Memory info:" >&2
cat /proc/meminfo | head -5 >&2

for i in {1..10}; do
  echo "SHELL_TEST: Loop $i/10" >&2
  sleep 2
done

echo "SHELL_TEST: Completed successfully" >&2