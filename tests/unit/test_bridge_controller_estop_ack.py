import asyncio
import sys
from pathlib import Path

# Add repository root to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import bb8_core.bridge_controller as bc  # type: ignore[import-not-found]


class _ImmediateLoop:
    def call_soon_threadsafe(self, callback):
        callback()


def _ack_collector(bucket, done_event=None):
    def _ack(cmd, cid, ok=True, reason=None):
        bucket.append({"cmd": cmd, "cid": cid, "ok": ok, "reason": reason})
        if done_event is not None:
            done_event.set()

    return _ack


def test_estop_ack_emitted_after_successful_completion():
    calls = []

    async def _ok():
        calls.append("completed")

    async def _run():
        acks = []
        done = asyncio.Event()
        bc._schedule_async_command_ack(
            loop=_ImmediateLoop(),
            create_task=asyncio.create_task,
            coroutine_factory=_ok,
            ack_fn=_ack_collector(acks, done),
            cmd="estop",
            cid="cid-success",
        )
        assert acks == []
        await asyncio.wait_for(done.wait(), timeout=1.0)
        assert acks == [
            {"cmd": "estop", "cid": "cid-success", "ok": True, "reason": None}
        ]

    asyncio.run(_run())
    assert calls == ["completed"]


def test_estop_ack_reports_failure_when_task_raises():
    async def _boom():
        raise RuntimeError("estop failed")

    async def _run():
        acks = []
        done = asyncio.Event()
        bc._schedule_async_command_ack(
            loop=_ImmediateLoop(),
            create_task=asyncio.create_task,
            coroutine_factory=_boom,
            ack_fn=_ack_collector(acks, done),
            cmd="estop",
            cid="cid-fail",
        )
        await asyncio.wait_for(done.wait(), timeout=1.0)
        assert len(acks) == 1
        assert acks[0]["cmd"] == "estop"
        assert acks[0]["cid"] == "cid-fail"
        assert acks[0]["ok"] is False
        assert "estop failed" in str(acks[0]["reason"])

    asyncio.run(_run())


def test_clear_estop_ack_parity_on_success():
    async def _ok():
        return None

    async def _run():
        acks = []
        done = asyncio.Event()
        bc._schedule_async_command_ack(
            loop=_ImmediateLoop(),
            create_task=asyncio.create_task,
            coroutine_factory=_ok,
            ack_fn=_ack_collector(acks, done),
            cmd="clear_estop",
            cid="cid-clear",
        )
        await asyncio.wait_for(done.wait(), timeout=1.0)
        assert acks == [
            {
                "cmd": "clear_estop",
                "cid": "cid-clear",
                "ok": True,
                "reason": None,
            }
        ]

    asyncio.run(_run())
