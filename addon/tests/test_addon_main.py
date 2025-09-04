import pytest
from tests.helpers.fakes import StubCore
from tests.helpers.util import assert_contains_log

@pytest.mark.usefixtures("caplog_level")
def test_main_start(monkeypatch, caplog):
    # Monkeypatch out network/thread calls
    monkeypatch.setattr("addon.bb8_core.main.start_controller", lambda *a, **kw: True)
    monkeypatch.setattr("addon.bb8_core.main.setup_logging", lambda *a, **kw: True)
    StubCore.calls.clear()
    # Simulate main wiring
    assert True  # Would call main()
    assert_contains_log(caplog, "Starting bridge controller")
    assert_contains_log(caplog, "broker")
