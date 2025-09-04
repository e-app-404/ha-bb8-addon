import pytest
from tests.helpers.util import assert_contains_log

def clamp(val, minv, maxv):
    return max(minv, min(val, maxv))

@pytest.mark.parametrize("val,minv,maxv,expected", [
    (5, 0, 10, 5),
    (-1, 0, 10, 0),
    (11, 0, 10, 10),
])
def test_clamp(val, minv, maxv, expected, capsys):
    print("clamp")
    assert clamp(val, minv, maxv) == expected
    out = capsys.readouterr()
    assert "clamp" in out.out or "clamp" in out.err

def test_bad_payload(capsys):
    try:
        int("notanint")
    except Exception:
        print("bad payload")
    out = capsys.readouterr()
    assert "bad payload" in out.out or "bad payload" in out.err
