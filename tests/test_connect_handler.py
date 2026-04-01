import ast
import asyncio
from pathlib import Path

import pytest

from bb8_core import bridge_controller


class FakeClient:
    def __init__(self):
        self.calls = []

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.calls.append(
            {
                "topic": topic,
                "payload": payload,
                "qos": qos,
                "retain": retain,
            }
        )


class FakeBleSession:
    def __init__(self, *, connected=False, connect_error=None):
        self._connected = connected
        self._connect_error = connect_error
        self.connect_calls = 0

    def is_connected(self):
        return self._connected

    async def connect(self):
        self.connect_calls += 1
        if self._connect_error is not None:
            raise self._connect_error
        self._connected = True


class FakeFacade:
    def __init__(self):
        self.set_ble_session_calls = []
        self.holdoff_calls = 0
        self.presence_calls = []
        self.publish_presence = self.presence_calls.append

    def set_ble_session(self, ble_session):
        self.set_ble_session_calls.append(ble_session)

    def mark_post_connect_holdoff(self):
        self.holdoff_calls += 1


def _load_bridge_controller_tree() -> ast.AST:
    source_path = Path(__file__).resolve().parents[1] / "bb8_core" / "bridge_controller.py"
    return ast.parse(source_path.read_text())


def _find_connect_branch() -> ast.If:
    tree = _load_bridge_controller_tree()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Compare):
            continue
        if not isinstance(test.left, ast.Name) or test.left.id != "cmd":
            continue
        if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
            continue
        if len(test.comparators) != 1:
            continue
        comparator = test.comparators[0]
        if isinstance(comparator, ast.Constant) and comparator.value == "connect":
            return node
    raise AssertionError("connect command branch not found")


def _branch_rejects_only_empty_payload(branch: ast.If) -> bool:
    if not branch.body:
        return False
    guard = branch.body[0]
    if not isinstance(guard, ast.If):
        return False
    test = guard.test
    if not isinstance(test, ast.UnaryOp) or not isinstance(test.op, ast.Not):
        return False
    operand = test.operand
    if not isinstance(operand, ast.Call):
        return False
    if not isinstance(operand.func, ast.Attribute):
        return False
    if operand.func.attr != "strip":
        return False
    if not isinstance(operand.func.value, ast.Name) or operand.func.value.id != "raw":
        return False
    return bool(guard.orelse)


def _branch_schedules_connect_attempt(branch: ast.If) -> bool:
    if not branch.body:
        return False
    raw_guard = branch.body[0]
    if not isinstance(raw_guard, ast.If) or len(raw_guard.orelse) < 3:
        return False
    shared_session_assign = raw_guard.orelse[0]
    if not isinstance(shared_session_assign, ast.Assign):
        return False
    if len(shared_session_assign.targets) != 1:
        return False
    target = shared_session_assign.targets[0]
    if not isinstance(target, ast.Name) or target.id != "shared_ble_session":
        return False
    value = shared_session_assign.value
    if not isinstance(value, ast.Call):
        return False
    if not isinstance(value.func, ast.Name) or value.func.id != "_resolve_shared_ble_session":
        return False

    session_guard = raw_guard.orelse[1]
    if not isinstance(session_guard, ast.If):
        return False

    if len(raw_guard.orelse) < 3:
        return False

    call_stmt = raw_guard.orelse[2]
    if not isinstance(call_stmt, ast.Expr) or not isinstance(call_stmt.value, ast.Call):
        return False
    call = call_stmt.value
    if not isinstance(call.func, ast.Name) or call.func.id != "_schedule_async_command_ack":
        return False

    for keyword in call.keywords:
        if keyword.arg != "coroutine_factory":
            continue
        if not isinstance(keyword.value, ast.Lambda):
            return False
        body = keyword.value.body
        if not isinstance(body, ast.Call):
            return False
        if not isinstance(body.func, ast.Name) or body.func.id != "_request_connect_attempt":
            return False
        for inner_keyword in body.keywords:
            if inner_keyword.arg != "ble_session":
                continue
            if not isinstance(inner_keyword.value, ast.Name):
                return False
            return inner_keyword.value.id == "shared_ble_session"
        return True
    return False


def _branch_has_missing_session_guard(branch: ast.If) -> bool:
    if not branch.body:
        return False
    raw_guard = branch.body[0]
    if not isinstance(raw_guard, ast.If) or len(raw_guard.orelse) < 2:
        return False
    session_guard = raw_guard.orelse[1]
    if not isinstance(session_guard, ast.If):
        return False
    test = session_guard.test
    if not isinstance(test, ast.Compare):
        return False
    if not isinstance(test.left, ast.Name) or test.left.id != "shared_ble_session":
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Is):
        return False
    if len(test.comparators) != 1:
        return False
    comparator = test.comparators[0]
    if not isinstance(comparator, ast.Constant) or comparator.value is not None:
        return False
    return bool(session_guard.body)


def test_connect_press_payload_accepted():
    branch = _find_connect_branch()

    assert _branch_rejects_only_empty_payload(branch)
    assert _branch_has_missing_session_guard(branch)
    assert _branch_schedules_connect_attempt(branch)
    assert bool("PRESS".strip()) is True


def test_connect_nonempty_payload_accepted():
    branch = _find_connect_branch()

    assert _branch_rejects_only_empty_payload(branch)
    assert _branch_has_missing_session_guard(branch)
    assert _branch_schedules_connect_attempt(branch)
    assert bool('{"cid":"abc"}'.strip()) is True


def test_connect_empty_payload_rejected_or_ignored_consistently():
    branch = _find_connect_branch()
    guard = branch.body[0]

    assert _branch_rejects_only_empty_payload(branch)
    assert isinstance(guard, ast.If)
    assert guard.body
    ack_call = guard.body[0]
    assert isinstance(ack_call, ast.Expr)
    assert isinstance(ack_call.value, ast.Call)
    assert isinstance(ack_call.value.func, ast.Name)
    assert ack_call.value.func.id == "_ack"
    assert isinstance(ack_call.value.args[0], ast.Constant)
    assert ack_call.value.args[0].value == "connect"
    assert isinstance(ack_call.value.args[2], ast.Constant)
    assert ack_call.value.args[2].value is False
    assert isinstance(ack_call.value.args[3], ast.Constant)
    assert ack_call.value.args[3].value == "Missing connect payload"


def test_connect_branch_uses_bound_shared_session():
    branch = _find_connect_branch()

    assert _branch_schedules_connect_attempt(branch)


def test_connect_branch_missing_session_fails_cleanly():
    branch = _find_connect_branch()
    raw_guard = branch.body[0]
    session_guard = raw_guard.orelse[1]

    assert _branch_has_missing_session_guard(branch)
    assert isinstance(session_guard, ast.If)
    assert len(session_guard.body) >= 2

    log_call = session_guard.body[0]
    ack_call = session_guard.body[1]

    assert isinstance(log_call, ast.Expr)
    assert isinstance(log_call.value, ast.Call)
    assert isinstance(log_call.value.func, ast.Attribute)
    assert log_call.value.func.attr == "error"

    assert isinstance(ack_call, ast.Expr)
    assert isinstance(ack_call.value, ast.Call)
    assert isinstance(ack_call.value.func, ast.Name)
    assert ack_call.value.func.id == "_ack"
    assert isinstance(ack_call.value.args[0], ast.Constant)
    assert ack_call.value.args[0].value == "connect"
    assert isinstance(ack_call.value.args[2], ast.Constant)
    assert ack_call.value.args[2].value is False
    assert isinstance(ack_call.value.args[3], ast.Constant)
    assert ack_call.value.args[3].value == "Shared BLE session unavailable"


def test_connect_already_connected_no_crash(monkeypatch):
    fake_client = FakeClient()
    facade = FakeFacade()
    ble_session = FakeBleSession(connected=True)
    monkeypatch.setattr(bridge_controller, "client", fake_client)

    asyncio.run(
        bridge_controller._request_connect_attempt(
            facade=facade,
            ble_session=ble_session,
            config={},
        )
    )

    assert ble_session.connect_calls == 0
    assert facade.set_ble_session_calls == [ble_session]
    assert facade.holdoff_calls == 1
    assert facade.presence_calls == [True]
    assert fake_client.calls == [
        {
            "topic": "bb8/status/connection",
            "payload": "connected",
            "qos": 0,
            "retain": True,
        }
    ]


def test_connect_success_propagates_post_connect_side_effects(monkeypatch):
    fake_client = FakeClient()
    facade = FakeFacade()
    ble_session = FakeBleSession(connected=False)
    monkeypatch.setattr(bridge_controller, "client", fake_client)

    asyncio.run(
        bridge_controller._request_connect_attempt(
            facade=facade,
            ble_session=ble_session,
            config={},
        )
    )

    assert ble_session.connect_calls == 1
    assert facade.set_ble_session_calls == [ble_session]
    assert facade.holdoff_calls == 1
    assert facade.presence_calls == [True]
    assert fake_client.calls == [
        {
            "topic": "bb8/status/connection",
            "payload": "connected",
            "qos": 0,
            "retain": True,
        }
    ]


def test_connect_failure_does_not_false_publish_connected(monkeypatch):
    fake_client = FakeClient()
    facade = FakeFacade()
    ble_session = FakeBleSession(connected=False, connect_error=RuntimeError("boom"))
    monkeypatch.setattr(bridge_controller, "client", fake_client)

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(
            bridge_controller._request_connect_attempt(
                facade=facade,
                ble_session=ble_session,
                config={},
            )
        )

    assert ble_session.connect_calls == 1
    assert facade.set_ble_session_calls == []
    assert facade.holdoff_calls == 0
    assert facade.presence_calls == []
    assert fake_client.calls == []
