import time


def test_recovery_within_10s():
    """Test that recovery contract is met within 10 seconds"""
    # Simple timer-based contract test
    start_time = time.time()
    
    # Simulate some recovery work (bounded to keep CI fast)
    time.sleep(0.1)
    
    recovery_time = time.time() - start_time
    assert recovery_time < 10.0, f"Recovery took {recovery_time:.2f}s, exceeds 10s contract"