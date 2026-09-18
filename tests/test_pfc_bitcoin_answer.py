"""Cloud-only answer-reader regressions; never execute a live worker.

The external answer is nine bytes: status, four-byte LE en2, four-byte LE
nonce. Status is transported unchanged, including zero; it is not readiness.
Complete fixtures and fixed pool replies establish I/O behavior only.
"""

import builtins
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = {"pfc_exec_input": {"offset": 0}, "pfc_on": {"offset": 116}}
ORIGINAL_JOB = {
    "job_id": "answer-fixture-job", "prevhash": "00" * 32,
    "coinb1": "", "coinb2": "", "merkle_branch": [],
    "version": "20000000", "nbits": "1d00ffff", "ntime": "65000000",
    "clean_jobs": True,
}
ACCEPTED = {"id": 100, "result": True, "error": None}


class TrackingReader(io.BytesIO):
    def __init__(self, payload, failure=None):
        super().__init__(payload)
        self.requests = []
        self.failure = failure

    def read(self, size=-1):
        self.requests.append(size)
        if self.failure is not None:
            raise self.failure
        return super().read(size)


class Clock:
    def __init__(self):
        self.now = 100.0

    def monotonic(self):
        return self.now

    def sleep(self, delay):
        self.now += delay


class ReceiptConnection:
    def __init__(self, clock, events):
        self.clock = clock
        self.events = events
        self.sent = []
        self.replies = []
        self.closed = False

    def send(self, message, timeout=15.0):
        self.events.append(("send",))
        self.sent.append(message)
        self.replies.append(ACCEPTED)

    def lines(self, wait=2.0):
        if self.replies:
            return [self.replies.pop(0)]
        self.clock.sleep(wait)
        return []

    def drain(self, timeout=1.0):
        self.events.append(("drain",))
        return []

    def close(self):
        self.events.append(("close",))
        self.closed = True


def load_subject(relative_path):
    path = ROOT / relative_path
    name = "answer_" + relative_path.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.object(sys, "argv", ["embedding-program", "--unrelated", "option"]):
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(module)
    return module


class AnswerContract:
    relative_path = None

    def setUp(self):
        self.subject = load_subject(self.relative_path)

    def read_fixture(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            answer_path = Path(directory) / "external-answer.bin"
            answer_path.write_bytes(payload)
            with mock.patch.object(self.subject, "SAFEZONE", str(answer_path)):
                return self.subject.read_full_answer()

    def cycle_fixture(self, payload=None, open_failure=None, stale=False):
        events = []
        clock = Clock()
        connection = ReceiptConnection(clock, events)
        original_job = copy.deepcopy(ORIGINAL_JOB)
        real_reader = self.subject.read_full_answer
        wait_s = 0.2

        def route(*_args):
            events.append(("route",))

        def wait_for_job(current, duration):
            self.assertIs(current, connection)
            events.append(("wait", duration))
            clock.sleep(duration)
            return stale

        def read_answer():
            events.append(("read", clock.now))
            return real_reader()

        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            answer_path = Path(directory) / "external-answer.bin"
            receipt_path = Path(directory) / "receipt.json"
            if payload is not None:
                answer_path.write_bytes(payload)

            def file_open(path, *args, **kwargs):
                if str(path) == str(answer_path) and open_failure is not None:
                    raise open_failure
                return builtins.open(path, *args, **kwargs)

            with contextlib.ExitStack() as stack:
                stack.enter_context(mock.patch.object(self.subject, "Conn", return_value=connection))
                stack.enter_context(mock.patch.object(self.subject, "receive_job",
                                                     return_value=("abcd", 4, original_job)))
                route_mock = stack.enter_context(mock.patch.object(self.subject, "send_block", side_effect=route))
                wait_mock = stack.enter_context(mock.patch.object(self.subject, "wait_for_job", side_effect=wait_for_job))
                reader_mock = stack.enter_context(mock.patch.object(self.subject, "read_full_answer", side_effect=read_answer))
                stack.enter_context(mock.patch.object(self.subject, "open", side_effect=file_open, create=True))
                stack.enter_context(mock.patch.object(self.subject, "SAFEZONE", str(answer_path)))
                stack.enter_context(mock.patch.object(self.subject, "OUT", directory))
                stack.enter_context(mock.patch.object(self.subject, "JOB", str(receipt_path)))
                stack.enter_context(mock.patch.object(self.subject.time, "monotonic", clock.monotonic))
                stack.enter_context(mock.patch.object(self.subject.time, "sleep", clock.sleep))
                stack.enter_context(contextlib.redirect_stdout(output))
                self.subject.cycle(REGISTRY, wait_s=wait_s)
            receipt = json.loads(receipt_path.read_text())

        route_mock.assert_called_once()
        wait_mock.assert_called_once_with(connection, wait_s)
        reader_mock.assert_called_once_with()
        self.assertEqual([event[0] for event in events[:3]], ["route", "wait", "read"])
        self.assertAlmostEqual(events[2][1], 100.0 + wait_s)
        self.assertEqual(original_job, ORIGINAL_JOB)
        self.assertEqual(receipt["job_id"], ORIGINAL_JOB["job_id"])
        self.assertTrue(connection.closed)
        return receipt, connection, output.getvalue()

    def test_missing_file_is_a_distinct_answer_read_error(self):
        self.assertTrue(issubclass(self.subject.AnswerReadError, OSError))
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "does-not-exist.bin"
            with mock.patch.object(self.subject, "SAFEZONE", str(missing)):
                with self.assertRaises(self.subject.AnswerReadError) as caught:
                    self.subject.read_full_answer()
        self.assertIn("cannot read external answer", str(caught.exception))

    def test_every_short_length_is_rejected_instead_of_synthetic_zeros(self):
        for length in range(9):
            with self.subTest(length=length):
                with self.assertRaises(self.subject.AnswerReadError) as caught:
                    self.read_fixture(b"\x00" * length)
                self.assertIn("expected 9 bytes", str(caught.exception))
                self.assertIn("read %d" % length, str(caught.exception))

    def test_open_permission_error_preserves_original_reason(self):
        with mock.patch.object(self.subject, "open", create=True,
                               side_effect=PermissionError("fixture unreadable answer file")):
            with self.assertRaises(self.subject.AnswerReadError) as caught:
                self.subject.read_full_answer()
        self.assertIn("fixture unreadable answer file", str(caught.exception))

    def test_read_io_error_preserves_reason_and_closes_file(self):
        reader = TrackingReader(b"\x00" * 9, OSError("fixture read I/O failure"))
        with mock.patch.object(self.subject, "open", return_value=reader, create=True):
            with self.assertRaises(self.subject.AnswerReadError) as caught:
                self.subject.read_full_answer()
        self.assertIn("fixture read I/O failure", str(caught.exception))
        self.assertEqual(reader.requests, [9])
        self.assertTrue(reader.closed)

    def test_complete_values_preserve_status_and_little_endian_fields(self):
        fixtures = [
            (b"\x00" * 9, (0, 0, 0)),
            (b"\x00\x01\x02\x03\x04\xfe\xdc\xba\x98", (0, 0x04030201, 0x98BADCFE)),
            (b"\x00" + b"\xff" * 8, (0, 0xFFFFFFFF, 0xFFFFFFFF)),
            (b"\xff" * 9, (255, 0xFFFFFFFF, 0xFFFFFFFF)),
        ]
        for payload, expected in fixtures:
            with self.subTest(expected=expected):
                self.assertEqual(self.read_fixture(payload), expected)

    def test_reader_consumes_only_first_nine_bytes_and_closes(self):
        payload = b"\xff\x01\x02\x03\x04\xfe\xdc\xba\x98"
        reader = TrackingReader(payload + b"ignored-trailing-data" * 100)
        with mock.patch.object(self.subject, "open", return_value=reader, create=True) as opener:
            answer = self.subject.read_full_answer()
        self.assertEqual(answer, (255, 0x04030201, 0x98BADCFE))
        self.assertEqual(reader.requests, [9])
        self.assertTrue(reader.closed)
        self.assertEqual(opener.call_args.args, (self.subject.SAFEZONE, "rb"))

    def test_cycle_unavailable_answers_write_receipt_without_submission(self):
        fixtures = [
            (None, None, "cannot read external answer"),
            (b"\x00" * 8, None, "expected 9 bytes, read 8"),
            (b"\x00" * 9, PermissionError("fixture unreadable answer file"), "fixture unreadable answer file"),
        ]
        for payload, error, reason in fixtures:
            with self.subTest(reason=reason):
                receipt, connection, output = self.cycle_fixture(payload, open_failure=error)
                self.assertIsNone(receipt["answer"])
                self.assertFalse(receipt["submission_attempted"])
                self.assertIsNone(receipt["verdict"])
                self.assertIn(reason, receipt["answer_error"])
                self.assertEqual(receipt["pool"], "answer-unavailable (%s)" % receipt["answer_error"])
                self.assertIn("answer-unavailable", output)
                self.assertEqual(connection.sent, [])

    def test_cycle_complete_zero_answer_is_still_submitted(self):
        receipt, connection, _output = self.cycle_fixture(b"\x00" * 9)
        self.assertEqual(receipt["answer"], {"status": 0, "en2": 0, "nonce": 0})
        self.assertIsNone(receipt["answer_error"])
        self.assertTrue(receipt["submission_attempted"])
        self.assertEqual(receipt["verdict"], ACCEPTED)
        self.assertEqual(connection.sent, [{
            "id": 100, "method": "mining.submit", "params": [
                self.subject.WALLET, "answer-fixture-job", "00000000", "65000000", "00000000",
            ],
        }])

    def test_cycle_preserves_complete_status_zero_and_255_with_nonzero_fields(self):
        for status in (0, 255):
            with self.subTest(status=status):
                receipt, connection, _output = self.cycle_fixture(bytes([status]) + b"\xff" * 8)
                self.assertEqual(receipt["answer"], {"status": status, "en2": 0xFFFFFFFF, "nonce": 0xFFFFFFFF})
                self.assertIsNone(receipt["answer_error"])
                self.assertTrue(receipt["submission_attempted"])
                self.assertEqual(len(connection.sent), 1)
                self.assertEqual(connection.sent[0]["params"], [
                    self.subject.WALLET, "answer-fixture-job", "ffffffff", "65000000", "ffffffff",
                ])

    def test_stale_job_and_missing_answer_retain_both_observations(self):
        receipt, connection, _output = self.cycle_fixture(stale=True)
        self.assertEqual(receipt["pool"], "stale-job (pool invalidated work before submission)")
        self.assertIsNone(receipt["answer"])
        self.assertFalse(receipt["submission_attempted"])
        self.assertIsNone(receipt["verdict"])
        self.assertIn("cannot read external answer", receipt["answer_error"])
        self.assertEqual(connection.sent, [])


class HostAnswerTests(AnswerContract, unittest.TestCase):
    relative_path = "host/pfc_bitcoin_autopilot.py"


class InfraAnswerTests(AnswerContract, unittest.TestCase):
    relative_path = "infra/host/pfc_bitcoin_autopilot.py"


if __name__ == "__main__":
    unittest.main()
