from __future__ import annotations

# --- BEGIN: ensure repo root on sys.path + test MQTT host before any imports ---
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force tests to use localhost, not the real HA broker.
# Must be set at module import time (before any bb8_core imports).
os.environ.setdefault("MQTT_HOST", "127.0.0.1")
# --- END ---


