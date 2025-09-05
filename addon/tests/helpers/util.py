import json


def build_topic(base, *parts):
    return "/".join([base] + list(parts))


def assert_contains_log(caplog, needle):
    # Relaxed: allow substring match, not exact message
    assert any(
        needle in r.message or needle in r.name for r in caplog.records
    ), f"Log missing: {needle}"


def assert_json_schema(payload, required_keys):
    obj = json.loads(payload)
    for k in required_keys:
        assert k in obj, f"Missing key: {k}"
    return obj
