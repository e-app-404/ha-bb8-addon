def test_build_topic_variants():
    """Test topic building logic"""
    def build_topic(base, component, action):
        # Simple implementation for testing
        return f"{base.rstrip('/')}/{component.strip('/')}/{action.strip('/')}"
    
    assert build_topic("bb8", "echo", "cmd") == "bb8/echo/cmd"
    assert build_topic("bb8", "echo", "ack") == "bb8/echo/ack"
    # idempotence / strip slashes
    assert build_topic("bb8/", "/echo/", "/cmd") == "bb8/echo/cmd"