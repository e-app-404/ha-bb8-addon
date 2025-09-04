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

import pytest
import os
import logging
import time
import tempfile
import yaml


@pytest.fixture
def env_toggle():
    orig = os.environ.copy()

    def set_env(**kwargs):
        for k, v in kwargs.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = str(v)

    yield set_env
    os.environ.clear()
    os.environ.update(orig)


@pytest.fixture(autouse=True)
def caplog_level(caplog):
    caplog.set_level(logging.INFO)
    yield


@pytest.fixture
def time_sleep_counter(monkeypatch):
    counter = {"count": 0, "total": 0.0}

    def fake_sleep(secs):
        counter["count"] += 1
        counter["total"] += secs

    monkeypatch.setattr(time, "sleep", fake_sleep)
    yield counter


@pytest.fixture
def tmp_config(tmp_path):
    cfg = {"mqtt_host": "127.0.0.1", "mqtt_port": 1883}
    f = tmp_path / "config.yaml"
    f.write_text(yaml.dump(cfg))
    yield str(f)
