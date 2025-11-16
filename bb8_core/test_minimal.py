#!/usr/bin/env python3
"""Minimal test script to check if Python execution works in container"""

import os
import sys
import time

print("MINIMAL_TEST: Starting Python process", flush=True)
print(f"MINIMAL_TEST: Python version {sys.version}", flush=True)
print(f"MINIMAL_TEST: PID = {os.getpid()}", flush=True)

try:
    for i in range(10):
        print(f"MINIMAL_TEST: Loop {i}/10", flush=True)
        time.sleep(2)
    print("MINIMAL_TEST: Completed successfully", flush=True)
except Exception as e:
    print(f"MINIMAL_TEST: Error {e}", flush=True)
