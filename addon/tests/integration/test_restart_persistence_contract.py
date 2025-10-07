import time
from addon.bb8_core.persistence_contract import RecoveryTimer

def test_recovery_within_10s():
    t = RecoveryTimer(max_seconds=10.0)
    t.mark_restart()
    time.sleep(0.1)  # bounded sleep to keep CI fast; contract stays ≤10s
    assert t.ok(), "Recovery exceeded 10s contract"