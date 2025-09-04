import pytest
from tests.helpers.util import build_topic, assert_json_schema, assert_contains_log

@pytest.mark.usefixtures("caplog_level")
def test_serialization(caplog):
    payload = '{"a":1,"b":2}'
    obj = assert_json_schema(payload, ["a", "b"])
    assert obj["a"] == 1
    assert_contains_log(caplog, "a")

@pytest.mark.parametrize("val,minv,maxv,expected", [
    (None, 0, 10, 0),
    (5, 0, 10, 5),
    (15, 0, 10, 10),
])
def test_clamp(val, minv, maxv, expected, caplog):
    v = 0 if val is None else max(minv, min(val, maxv))
    assert v == expected
    assert_contains_log(caplog, "clamp")
