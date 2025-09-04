import pytest
from tests.helpers.util import assert_contains_log

@pytest.mark.usefixtures("caplog_level")
def test_version_probe_log(caplog):
    # Simulate version probe logic
    assert True
    assert_contains_log(caplog, "version")
