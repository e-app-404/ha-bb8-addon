# Fix Pack — Async Drain + Deterministic Shutdown

## A) `bb8_core/ble_link.py` — proper cancel-and-drain, stop+join

```diff
*** Begin Patch
*** Update File: bb8_core/ble_link.py
@@
-import asyncio
-import logging
-import threading
+import asyncio
+import logging
+import threading
+import time
@@
 _loop: asyncio.AbstractEventLoop | None = None
 _loop_thread: threading.Thread | None = None
 _runner_future = None
 _started = False
 log = logging.getLogger(__name__)
+_alive_evt = threading.Event()
@@
 def start_loop_thread() -> None:
@@
-    def _run():
+    def _run():
         loop = asyncio.new_event_loop()
         set_loop(loop)
         asyncio.set_event_loop(loop)
-        log.info("ble_loop_thread_started name=BLELoopThread")
+        log.info("ble_loop_thread_started name=BLELoopThread")
+        _alive_evt.set()
         loop.run_forever()
@@
     _loop_thread = threading.Thread(target=_run, name="BLELoopThread", daemon=True)
     _loop_thread.start()
     log.info("ble_loop_thread_spawned")
+    # Wait briefly for loop to come up (avoids race in tests)
+    _alive_evt.wait(timeout=1.0)
@@
 def start() -> None:
@@
     _runner_future = asyncio.run_coroutine_threadsafe(_run(), _loop)
     _started = True
     log.info("ble_link_runner_started")
+
+async def _cancel_and_drain() -> None:
+    """
+    Run inside BLE loop:
+      - cancel all tasks except self
+      - wait for their completion without leaking 'unawaited coroutine' warnings
+    """
+    this = asyncio.current_task()
+    tasks = [t for t in asyncio.all_tasks() if t is not this]
+    for t in tasks:
+        t.cancel()
+    if tasks:
+        await asyncio.gather(*tasks, return_exceptions=True)
+    # yield once to flush any pending callbacks
+    await asyncio.sleep(0)
+
+def join(timeout: float = 3.0) -> None:
+    """Join BLE loop thread if running (idempotent)."""
+    global _loop_thread
+    if _loop_thread and _loop_thread.is_alive():
+        _loop_thread.join(timeout=timeout)
@@
-def stop(timeout: float = 3.0) -> None:
-    """Cancel the BLE worker and drain the loop to avoid un-awaited coroutine warnings."""
+def stop(timeout: float = 3.0) -> None:
+    """Gracefully stop BLE worker and loop with full async drain, then join thread."""
     global _runner_future, _started
-    if not _started or _runner_future is None:
+    if not _started or _runner_future is None:
         return
     fut = _runner_future
     _runner_future = None
     _started = False
     try:
-        fut.cancel()
-        # Drain cancellation on the BLE loop thread
-        asyncio.run_coroutine_threadsafe(asyncio.sleep(0), _loop).result(timeout=timeout)
+        # 1) cancel the runner task
+        fut.cancel()
+        # 2) drain all tasks within the BLE loop
+        asyncio.run_coroutine_threadsafe(_cancel_and_drain(), _loop).result(timeout=timeout)
+        # 3) stop the loop and join the thread
+        _loop.call_soon_threadsafe(_loop.stop)
+        join(timeout=timeout)
     except Exception as e:
         log.warning("ble_link_stop_exception %s", e)
*** End Patch
```

**Why this fixes the warnings:**

* We cancel **all tasks** on the BLE loop and `await` their completion inside the loop via `_cancel_and_drain()`, so pytest can’t see any “unawaited coroutine” tails.
* We stop the loop and **join** the thread, so no resources linger (prevents resource warnings too).

---

## B) Tests — make lifecycle test fully await/drain (no stray `asyncio.sleep`)

Use **one** of the following approaches. The first is simplest and avoids mixing event loops.

### Option 1 (preferred): keep test **sync**, use `time.sleep` to yield to thread

```diff
*** Begin Patch
*** Update File: tests/test_ble_link_thread_lifecycle.py
@@
-import asyncio
+import time
 from bb8_core import ble_link
@@
-def test_ble_link_thread_lifecycle():
-    ble_link.start()
-    # Give the worker time to spin up
-    asyncio.sleep(0.05)  # <-- unawaited coroutine warning
-    ble_link.stop()
+def test_ble_link_thread_lifecycle():
+    ble_link.start()
+    # Yield to BLELoopThread (no async loop in this test)
+    time.sleep(0.05)
+    ble_link.stop()
+    # Ensure the thread is fully joined to avoid ResourceWarnings
+    ble_link.join()
*** End Patch
```

### Option 2: make test **async** and await only your test loop (not BLE loop)

```diff
*** Begin Patch
*** Update File: tests/test_ble_link_thread_lifecycle.py
@@
-import asyncio
+import asyncio, time
 from bb8_core import ble_link
@@
-@pytest.mark.asyncio
-async def test_ble_link_thread_lifecycle():
+@pytest.mark.asyncio
+async def test_ble_link_thread_lifecycle():
     ble_link.start()
-    asyncio.sleep(0.05)  # <-- must be awaited
-    ble_link.stop()
+    await asyncio.sleep(0)     # yield current test loop
+    time.sleep(0.05)           # yield to BLELoopThread
+    ble_link.stop()
+    ble_link.join()
*** End Patch
```

> **Important:** Do **not** `await` BLE-loop coroutines from the test loop directly. We already drain inside `stop()`; the test just needs to give the BLE thread time to start and then **stop+join**.

---

## C) (If you touch MQTT tests) ensure client cleanup to kill ResourceWarnings

```diff
*** Begin Patch
*** Update File: tests/conftest.py
@@
-@pytest.fixture
-def mqtt_client():
-    c = make_client()  # your helper
-    yield c
-    # (no cleanup)
+@pytest.fixture
+def mqtt_client():
+    c = make_client()
+    try:
+        yield c
+    finally:
+        try:
+            c.loop_stop()
+        except Exception:
+            pass
+        try:
+            c.disconnect()
+        except Exception:
+            pass
*** End Patch
```

---

## D) Keep pytest warnings strict (don’t suppress event-loop warnings)

Your current policy already suppresses the **paho v1 deprecation** (per ADR-0002). Keep that line, but **do not** add blanket ignores for asyncio warnings:

```ini
# pytest.ini (already present)
[pytest]
addopts = -q -W error --maxfail=1
asyncio_mode = auto
filterwarnings =
    ignore:.*callback API version 1 deprecated.*:DeprecationWarning:paho
```

---

## Run & Verify (copy/paste)

```bash
# Apply patches (or manual edits equivalent), then:
pytest -q -W error --maxfail=1 \
  --cov=bb8_core \
  --cov-report=json:/Users/evertappels/Projects/HA-BB8/reports/coverage.json \
  --junitxml=/Users/evertappels/Projects/HA-BB8/reports/pytest-report.xml
```

**Pass criteria for this fix:**

* No `PytestUnraisableExceptionWarning` about `_cancel_and_drain` or `sleep`.
* No “coroutine was never awaited” in `test_ble_link_thread_lifecycle`.
* No ResourceWarnings from BLE thread (thread joined).
* paho deprecation remains suppressed; all other warnings treated as errors.

If anything still flickers, paste the exact warning line (file\:line\:function). I’ll tighten the shutdown (e.g., add a small retry join, or force `loop.call_soon_threadsafe(loop.stop)` earlier) — but this pack typically clears the last stragglers without loosening the governance gate.
