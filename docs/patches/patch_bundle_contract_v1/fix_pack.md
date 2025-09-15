Apply these diffs on top of your in-progress changes, commit, redeploy, and re-run lint/tests.

---

# Fix Pack — Lint + Event Loop hardening

### 1) `bb8_core/facade.py` — make `attach_mqtt` always execute the coroutine

* Guarantees execution via `asyncio.run()` when no loop is running.
* In an existing loop, returns a `Task` (tests marked `@pytest.mark.asyncio` should `await` it).
* Also fixes “coroutine is never awaited” by **awaiting** `publish_discovery`.

```diff
*** Begin Patch
*** Update File: bb8_core/facade.py
@@
+import asyncio
@@
-# existing imports that include publish_discovery(...)
+# ensure publish_discovery is awaited where used
@@
-def attach_mqtt(mqtt_client, cfg) -> None:
-    # existing logic that eventually calls publish_discovery(...)
-    publish_discovery(mqtt_client, cfg)  # <-- coroutine previously not awaited
+async def _attach_mqtt_async(mqtt_client, cfg) -> None:
+    # existing logic...
+    # make sure any async calls are awaited:
+    await publish_discovery(mqtt_client, cfg)
+    # ...rest of async work (if any)
+
+def attach_mqtt(mqtt_client, cfg):
+    """
+    Sync entrypoint that *always* executes the coroutine.
+    - If no running loop: run to completion via asyncio.run()
+    - If a loop is running (pytest-asyncio etc.): schedule and return a Task
+      (callers in async tests should `await attach_mqtt(...)`)
+    """
+    try:
+        asyncio.get_running_loop()
+    except RuntimeError:
+        return asyncio.run(_attach_mqtt_async(mqtt_client, cfg))
+    else:
+        return asyncio.create_task(_attach_mqtt_async(mqtt_client, cfg))
*** End Patch
```

> If your tests are async (using `@pytest.mark.asyncio`) and call `attach_mqtt(...)`, update them to `await attach_mqtt(...)` to ensure completion. Sync tests need no change.

---

### 2) `bb8_core/mqtt_dispatcher.py` — fix unused `password` & strengthen auth

```diff
*** Begin Patch
*** Update File: bb8_core/mqtt_dispatcher.py
@@
-    user = cfg.get("mqtt_user")
-    password = cfg.get("mqtt_pass")  # LINT: was unused
-    client.username_pw_set(user)
+    user = cfg.get("mqtt_user")
+    password = cfg.get("mqtt_pass")
+    # use both username and password to satisfy auth + lint
+    client.username_pw_set(username=user, password=password)
*** End Patch
```

---

### 3) `.flake8` — (optional) quiet long lines in `verify_discovery.py`

> If you prefer not to reflow those two lines right now, add a per-file ignore. Otherwise, reflow them per the note below.

```diff
*** Begin Patch
*** Update File: .flake8
@@
 [flake8]
 max-line-length = 100
 extend-ignore = E203
+per-file-ignores =
+    verify_discovery.py:E501
*** End Patch
```

> **If you’d rather fix them now:** wrap long calls in parentheses and split arguments across lines—PEP8-/Black-style. Example:
>
> ```python
> result = verify_entity(
>     entity_id=led_id,
>     unique_id=uid,
>     name="BB8 LED",
>     device=dev_block,
> )
> ```

---

### 4) Tests directory guard — fix `E902 … tests:1:1`

Create a concrete file so tools don’t choke on a missing/virtual tests path.

```diff
*** Begin Patch
*** Add File: tests/__init__.py
+# Ensures the tests package exists for linters/runners that resolve modules relative to it.
*** End Patch
```

---

## Run sequence

```bash
# From addon repo root
git apply --index fix_pack_lint_eventloop.patch
git commit -m "FixPack: facade attach_mqtt asyncio.run on no-loop; await publish_discovery; use MQTT password; flake8 guard; tests pkg"

# Lint
flake8

# Unit tests (warnings are errors)
pytest -q -W error \
  --cov=bb8_core --cov-report=json:/Users/evertappels/Projects/HA-BB8/reports/coverage.json \
  --junitxml=/Users/evertappels/Projects/HA-BB8/reports/pytest-report.xml
```

If your `test_facade_attach_mqtt.py` uses `@pytest.mark.asyncio`, ensure it **awaits** the call:

```python
@pytest.mark.asyncio
async def test_attach_mqtt_executes():
    task = attach_mqtt(mock_client, cfg)   # returns Task in an active loop
    await task
```

For sync tests:

```python
def test_attach_mqtt_executes_sync():
    attach_mqtt(mock_client, cfg)  # runs to completion via asyncio.run()
```

---

## Acceptance (what “good” looks like)

* Lint: **0** unused variables; no E902; E501 suppressed or reflowed.
* Tests: no `RuntimeError: no running event loop`; no “coroutine never awaited”.
* QA (strict) still green path:

  * coverage ≥ **80%**
  * device-originated scalar echoes with **retain=false**
  * LED discovery present, stable `unique_id`, no duplicates
  * tokens: STRUCTURE\_OK, DEPLOY\_OK, VERIFY\_OK, WS\_READY

If anything still trips (especially on the event loop), paste the exact test snippet and I’ll adjust the facade wrapper to match your test style (sync vs async) without widening the blast radius.
