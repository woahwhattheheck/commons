"""Cloud-only monitor regressions using external-file fixtures, never a server.

Both source mirrors receive the same tests. The nine-byte answer's status is
displayed as data; it cannot establish whether a complete record is available.
"""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
REASON = "incomplete external answer: expected 9 bytes, read 8"


class CapturedOutput(io.StringIO):
    def reconfigure(self, **kwargs):
        pass


class TrackingReader(io.BytesIO):
    def __init__(self, payload):
        super().__init__(payload)
        self.requests = []

    def read(self, size=-1):
        self.requests.append(size)
        return super().read(size)


class ExternalFiles:
    """Return only the two approved fixture streams, once per snapshot."""

    def __init__(self, subject, receipts, payload=b"\0" * 9):
        self.subject = subject
        self.receipts = iter(receipts)
        self.payload = payload
        self.readers = []
        self.paths = []

    def open(self, path, mode="r", **kwargs):
        self.paths.append(path)
        if path == self.subject.SAFEZONE:
            if mode != "rb":
                raise AssertionError("answer fixture must be opened read-only as bytes")
            reader = TrackingReader(self.payload)
            self.readers.append(reader)
            return reader
        if path == self.subject.JOBFILE:
            if mode != "r" or kwargs.get("encoding") != "utf-8":
                raise AssertionError("receipt fixture must be opened read-only as UTF-8")
            return io.StringIO(json.dumps(next(self.receipts)))
        raise AssertionError("unexpected file access: %r" % (path,))


class TwoFrameWriter:
    def __init__(self):
        self.frames = []

    def write(self, payload):
        self.frames.append(payload.decode("utf-8"))

    def flush(self):
        if len(self.frames) == 2:
            raise BrokenPipeError("fixture stream finished after two frames")


def load_subject(relative_path):
    name = "monitor_" + relative_path.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    subject = importlib.util.module_from_spec(spec)
    # The existing monitor configures stdout during import. No CLI or server
    # entry point runs under this unique non-main module name.
    with contextlib.redirect_stdout(CapturedOutput()):
        with mock.patch.object(sys, "argv", ["fixture-embedding-program"]):
            spec.loader.exec_module(subject)
    return subject


def receipt(**updates):
    value = {
        "job_id": "monitor-fixture-job", "zbits": 23,
        "pool": "REJECTED", "answer": {"status": 0, "en2": 0, "nonce": 0},
        "answer_error": None, "submission_attempted": True,
    }
    value.update(updates)
    return value


class MonitorCases:
    @classmethod
    def setUpClass(cls):
        cls.subject = load_subject(cls.relative_path)

    def snapshot(self, value, payload=b"\0" * 9):
        files = ExternalFiles(self.subject, [value], payload)
        with mock.patch.object(self.subject, "open", side_effect=files.open, create=True):
            with mock.patch.object(self.subject.time, "strftime", return_value="12:34:56"):
                result = self.subject.snapshot()
        self.assertEqual(files.paths, [self.subject.SAFEZONE, self.subject.JOBFILE])
        self.assertTrue(all(reader.closed for reader in files.readers))
        return result, files

    def wallet_line(self, result):
        return next(line for line in result.splitlines() if line.startswith("WALLET"))

    def test_unavailable_answer_has_reason_and_never_invents_nonce_or_submission(self):
        for answer in (None, {}, {"nonce": None}):
            with self.subTest(answer=answer):
                result, _ = self.snapshot(receipt(
                    answer=answer, answer_error=REASON, submission_attempted=False,
                    pool="answer-unavailable (%s)" % REASON,
                ))
                wallet = self.wallet_line(result)
                self.assertIn("submission skipped answer unavailable", wallet)
                self.assertIn(REASON, wallet)
                self.assertNotIn("submitted", wallet)
                self.assertNotIn("nonce=", wallet)
                self.assertIn("job monitor-fixture-job", wallet)
                self.assertIn("target 23 zbits", wallet)
                self.assertIn("pool: answer-unavailable", wallet)

    def test_skipped_complete_zero_answer_retains_nonce_without_claiming_submit(self):
        result, _ = self.snapshot(receipt(
            submission_attempted=False,
            pool="stale-job (pool invalidated work before submission)",
        ))
        wallet = self.wallet_line(result)
        self.assertIn("submission skipped nonce=0", wallet)
        self.assertIn("pool: stale-job (pool invalidated work before submission)", wallet)
        self.assertNotIn("submitted", wallet)

    def test_attempted_complete_zero_answer_retains_zero_and_provider_verdict(self):
        result, _ = self.snapshot(receipt())
        wallet = self.wallet_line(result)
        self.assertIn("submission attempted nonce=0", wallet)
        self.assertIn("pool: REJECTED", wallet)
        self.assertNotIn("answer unavailable", wallet)

    def test_legacy_receipt_without_attempted_flag_reports_the_recorded_attempt(self):
        value = receipt()
        del value["submission_attempted"]
        result, _ = self.snapshot(value)
        self.assertIn("submission attempted nonce=0", self.wallet_line(result))

    def test_invalid_whole_receipt_renders_unavailable_instead_of_crashing(self):
        for value in (None, [], "fixture nonobject receipt"):
            with self.subTest(value=value):
                result, _ = self.snapshot(value)
                self.assertIn(
                    "wallet receipt unavailable (expected an object)",
                    self.wallet_line(result),
                )

    def test_complete_answer_displays_raw_status_and_little_endian_values(self):
        for status, en2, nonce in ((0, 0, 0), (0, 0x01020304, 0xA1B2C3D4), (255, 0xFFFFFFFF, 0xFFFFFFFF)):
            with self.subTest(status=status, en2=en2, nonce=nonce):
                result, _ = self.snapshot(receipt(), struct.pack("<BII", status, en2, nonce))
                answer_line = result.splitlines()[0]
                self.assertIn("status=%d" % status, answer_line)
                self.assertIn("en2=%d" % en2, answer_line)
                self.assertIn("nonce=%d" % nonce, answer_line)
                self.assertNotIn("empty", answer_line)
                self.assertNotIn("not deposited", answer_line)

    def test_short_answer_displays_actual_byte_count(self):
        for size in (0, 5, 8):
            with self.subTest(size=size):
                result, _ = self.snapshot(receipt(), b"\0" * size)
                self.assertIn("incomplete answer (%d of 9 bytes)" % size, result.splitlines()[0])
                self.assertNotIn("nonce=", result.splitlines()[0])

    def test_answer_read_is_bounded_to_one_nine_byte_record(self):
        payload = struct.pack("<BII", 0, 7, 11) + b"fixture trailing external bytes" * 100
        result, files = self.snapshot(receipt(), payload)
        self.assertEqual(len(files.readers), 1)
        self.assertEqual(files.readers[0].requests, [9])
        self.assertIn("nonce=11", result.splitlines()[0])

    def test_event_stream_continues_from_unavailable_answer_to_next_receipt(self):
        values = [
            receipt(answer=None, answer_error=REASON, submission_attempted=False),
            receipt(pool="accepted-by-pool"),
        ]
        files = ExternalFiles(self.subject, values)
        handler = self.subject.H.__new__(self.subject.H)
        handler.path = "/stream"
        handler.send_response = mock.Mock()
        handler.send_header = mock.Mock()
        handler.end_headers = mock.Mock()
        handler.wfile = TwoFrameWriter()
        with mock.patch.object(self.subject, "open", side_effect=files.open, create=True):
            with mock.patch.object(self.subject.time, "strftime", return_value="12:34:56"):
                with mock.patch.object(self.subject.time, "sleep") as sleep:
                    handler.do_GET()
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_any_call("Content-Type", "text/event-stream")
        self.assertEqual(len(handler.wfile.frames), 2)
        first, second = handler.wfile.frames
        self.assertIn("data: WALLET", first)
        self.assertIn("submission skipped answer unavailable", first)
        self.assertIn(REASON, first)
        self.assertIn("submission attempted nonce=0", second)
        self.assertIn("pool: accepted-by-pool", second)
        self.assertTrue(first.endswith("\n\n") and second.endswith("\n\n"))
        self.assertEqual(len(files.readers), 2)
        self.assertTrue(all(reader.closed for reader in files.readers))
        sleep.assert_called_once_with(1.0)


class HostMonitorTests(MonitorCases, unittest.TestCase):
    relative_path = "host/pfc_monitor_ui.py"


class InfraMonitorTests(MonitorCases, unittest.TestCase):
    relative_path = "infra/host/pfc_monitor_ui.py"


if __name__ == "__main__":
    unittest.main()
