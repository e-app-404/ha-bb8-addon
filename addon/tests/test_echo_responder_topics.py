import addon.bb8_core.echo_responder as er


def test_block_wildcard_returns_default(caplog):
    er._opts = {"mqtt_echo_cmd_topic": "bb8/#"}
    with caplog.at_level("WARNING"):
        got = er._resolve_topic("mqtt_echo_cmd_topic", "echo/cmd")
    assert got.endswith("echo/cmd")
    assert "#" not in got
    assert any("Wildcard detected" in r.message for r in caplog.records)
