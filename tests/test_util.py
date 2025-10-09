import types

import addon.bb8_core.util as util


def test_clamp_within_range(monkeypatch):
    logs = []
    dummy_logger = types.SimpleNamespace(debug=lambda msg: logs.append(msg))
    monkeypatch.setattr(util, "logger", dummy_logger)
    assert util.clamp(5, 1, 10) == 5
    assert logs[-1]["event"] == "util_clamp"
    assert logs[-1]["x"] == 5
    assert logs[-1]["lo"] == 1
    assert logs[-1]["hi"] == 10


def test_clamp_below_range(monkeypatch):
    logs = []
    dummy_logger = types.SimpleNamespace(debug=lambda msg: logs.append(msg))
    monkeypatch.setattr(util, "logger", dummy_logger)
    assert util.clamp(-5, 1, 10) == 1
    assert logs[-1]["x"] == -5


def test_clamp_above_range(monkeypatch):
    logs = []
    dummy_logger = types.SimpleNamespace(debug=lambda msg: logs.append(msg))
    monkeypatch.setattr(util, "logger", dummy_logger)
    assert util.clamp(15, 1, 10) == 10
    assert logs[-1]["x"] == 15


def test_clamp_edge_cases(monkeypatch):
    logs = []
    dummy_logger = types.SimpleNamespace(debug=lambda msg: logs.append(msg))
    monkeypatch.setattr(util, "logger", dummy_logger)
    # x == lo
    assert util.clamp(1, 1, 10) == 1
    # x == hi
    assert util.clamp(10, 1, 10) == 10
    # lo == hi
    assert util.clamp(5, 5, 5) == 5
    assert util.clamp(0, 5, 5) == 5
    assert util.clamp(10, 5, 5) == 5
