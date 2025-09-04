import pytest
from tests.helpers.util import build_topic, assert_contains_log

@pytest.mark.usefixtures("caplog_level")
def test_topic_build_parse(caplog):
    topic = build_topic("bb8", "cmd", "drive")
    assert topic == "bb8/cmd/drive"
    assert_contains_log(caplog, "cmd")

@pytest.mark.usefixtures("caplog_level")
def test_malformed_topic(caplog):
    topic = build_topic("bb8", "", "")
    assert topic == "bb8//"
    assert_contains_log(caplog, "bb8")
