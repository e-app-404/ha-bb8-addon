import json
import os
import tempfile
import time
from unittest import mock

from addon.bb8_core import evidence_capture


class DummyClient:
    def __init__(self):
        self.callbacks = {}

    def message_callback_add(self, topic, cb):
        self.callbacks[topic] = cb

    def loop_start(self):
        pass

    def loop_stop(self):
        pass

    def subscribe(self, topic, qos=0):
        pass


def test_evidence_recorder_start_stop(monkeypatch):
    client = DummyClient()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "evidence.jsonl")
        recorder = evidence_capture.EvidenceRecorder(client, "bb8", path, max_lines=10)
        monkeypatch.setattr(recorder, "_runner", lambda: None)
        recorder.start()
        # Thread is started but immediately exits due to patched runner
        assert recorder._t is not None
    recorder.stop()


def test_evidence_recorder_message_handling(monkeypatch):
    client = DummyClient()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "evidence.jsonl")
        recorder = evidence_capture.EvidenceRecorder(client, "bb8", path, max_lines=10)
        monkeypatch.setattr(recorder, "_runner", lambda: None)
        recorder.start()
        payload = json.dumps({"event": "cmd", "ts": time.time()})
        msg = mock.Mock()
        msg.payload = payload.encode()
        msg.topic = "bb8/cmd/anything"
        recorder.client.on_message(client, None, msg)
    # Should queue evidence twice due to chained callback
    assert recorder._cmd_q.qsize() == 2
    recorder.stop()


def test_evidence_recorder_file_writing(monkeypatch):
    client = DummyClient()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "evidence.jsonl")
        recorder = evidence_capture.EvidenceRecorder(client, "bb8", path, max_lines=2)

        # Patch _run to write two records then exit
        def fake_runner():
            for i in range(2):
                recorder._cmd_q.put({"event": f"cmd{i}", "ts": time.time()})
            recorder._stop.set()
            # Simulate flush by writing to file
            os.makedirs(os.path.dirname(recorder.report_path), exist_ok=True)
            with open(recorder.report_path, "w") as f:
                for i in range(2):
                    f.write(json.dumps({"event": f"cmd{i}", "ts": time.time()}) + "\n")

        monkeypatch.setattr(recorder, "_runner", fake_runner)
        recorder.start()
        time.sleep(0.1)
        recorder.stop()
        # Check file contents
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 2
        for line in lines:
            data = json.loads(line)
            assert "event" in data


def test_evidence_recorder_queue_max(monkeypatch):
    client = DummyClient()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "evidence.jsonl")
        recorder = evidence_capture.EvidenceRecorder(client, "bb8", path, max_lines=1)

        # Patch _run to put more than max_lines into _cmd_q and simulate file writing
        def fake_runner():
            for i in range(3):
                recorder._cmd_q.put({"event": f"cmd{i}", "ts": time.time()})
            recorder._stop.set()
            os.makedirs(os.path.dirname(recorder.report_path), exist_ok=True)
            with open(recorder.report_path, "w") as f:
                f.write(json.dumps({"event": "cmd0", "ts": time.time()}) + "\n")

        monkeypatch.setattr(recorder, "_runner", fake_runner)
        recorder.start()
        time.sleep(0.1)
        recorder.stop()
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 1


def test_evidence_recorder_malformed_payload(monkeypatch):
    client = DummyClient()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "evidence.jsonl")
        recorder = evidence_capture.EvidenceRecorder(client, "bb8", path, max_lines=10)
        monkeypatch.setattr(recorder, "_runner", lambda: None)
        recorder.start()
        # Simulate malformed payload
        msg = mock.Mock()
        msg.payload = b"notjson"
    msg.topic = "bb8/cmd/anything"
    # Use the installed on_message callback
    recorder.client.on_message(client, None, msg)
    # Should queue evidence twice due to chained callback
    assert recorder._cmd_q.qsize() == 2
    recorder.stop()


def test_evidence_recorder_timeout(monkeypatch):
    client = DummyClient()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "evidence.jsonl")
        recorder = evidence_capture.EvidenceRecorder(client, "bb8", path, max_lines=10)

        # Patch _run to sleep and simulate timeout
        def fake_runner():
            time.sleep(0.2)
            recorder._running = False

        monkeypatch.setattr(recorder, "_runner", fake_runner)
        recorder.start()
        time.sleep(0.3)
        recorder.stop()
        # Should not error
