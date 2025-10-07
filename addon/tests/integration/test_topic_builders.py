from addon.bb8_core.mqtt_dispatcher import build_topic

def test_build_topic_variants():
    assert build_topic("bb8","echo","cmd") == "bb8/echo/cmd"
    assert build_topic("bb8","echo","ack") == "bb8/echo/ack"
    # idempotence / strip slashes
    assert build_topic("bb8/","/echo/","/cmd") == "bb8/echo/cmd"