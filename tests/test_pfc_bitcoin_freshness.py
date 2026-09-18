"""Cloud-only regressions for pool job freshness; no worker execution.

Exercise both source mirrors through Conn and cycle. A deterministic socket
supplies protocol bytes; routing and external answer reads are replaced.
The test does not interpret worker status values or require a new cadence.
"""

from collections import deque
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
STALE_POOL = "stale-job (pool invalidated work before submission)"
ANSWER = (1, 7, 11)
REGISTRY = {"pfc_exec_input": {"offset": 0}, "pfc_on": {"offset": 116}}
ORIGINAL_JOB = {
    "job_id": "job-A", "prevhash": "00" * 32, "coinb1": "", "coinb2": "",
    "merkle_branch": [], "version": "20000000", "nbits": "1d00ffff",
    "ntime": "65000000", "clean_jobs": True,
}
ACCEPTED = {"id": 100, "result": True, "error": None}


def notify(clean_jobs, job_id="job-B"):
    return {"id": None, "method": "mining.notify", "params": [
        job_id, "11" * 32, "", "", [], "20000000", "1d00ffff", "65000001", clean_jobs,
    ]}


def frame(message):
    return (json.dumps(message) + "\n").encode()


class Clock:
    def __init__(self):
        self.now = 100.0

    def monotonic(self):
        return self.now

    def sleep(self, delay):
        self.now += delay


class ScriptedSocket:
    """Queue exhaustion is distinct from a successfully read partial frame."""

    def __init__(self, clock, incoming=(), read_cost=0.001):
        self.clock = clock
        self.incoming = deque(incoming)
        self.timeout = 15.0
        self.read_cost = read_cost
        self.recv_calls = 0
        self.sent = []
        self.closed = False
        self.on_submit = None
        self.repeat_chunk = None

    def settimeout(self, timeout):
        self.timeout = timeout

    def gettimeout(self):
        return self.timeout

    def setblocking(self, blocking):
        self.timeout = None if blocking else 0.0

    def recv(self, size):
        self.recv_calls += 1
        if self.incoming or self.repeat_chunk is not None:
            chunk = self.incoming.popleft() if self.incoming else self.repeat_chunk
            self.clock.now += self.read_cost
            if isinstance(chunk, BaseException):
                raise chunk
            if len(chunk) > size:
                self.incoming.appendleft(chunk[size:])
                chunk = chunk[:size]
            return chunk
        if self.timeout == 0:
            raise BlockingIOError("no currently available bytes")
        if self.timeout is None:
            raise AssertionError("test socket must not perform an unbounded receive")
        self.clock.now += self.timeout
        raise socket.timeout("fixture receive deadline")

    def sendall(self, data):
        message = json.loads(data)
        self.sent.append(message)
        if message.get("method") == "mining.submit" and self.on_submit:
            self.on_submit(self)

    def close(self):
        self.closed = True


def load_subject(relative_path):
    path = ROOT / relative_path
    name = "freshness_" + relative_path.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.object(sys, "argv", ["embedding-program", "--unrelated", "option"]):
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(module)
    return module


class FreshnessContract:
    relative_path = None

    def setUp(self):
        self.subject = load_subject(self.relative_path)

    def bare_connection(self, sock, buffered=b""):
        connection = self.subject.Conn.__new__(self.subject.Conn)
        connection.s = sock
        connection.buf = buffered
        return connection

    def run_cycle(self, incoming=(), wait_s=0.2, during_answer=None, after_submit=None):
        clock = Clock()
        sock = ScriptedSocket(clock, incoming)
        connection = self.bare_connection(sock)
        original_job = copy.deepcopy(ORIGINAL_JOB)
        answer_read_times = []
        output = io.StringIO()

        def read_answer():
            answer_read_times.append(clock.now)
            if during_answer:
                during_answer(sock)
            return ANSWER

        sock.on_submit = after_submit or (lambda current: current.incoming.append(frame(ACCEPTED)))
        with tempfile.TemporaryDirectory() as directory:
            receipt_path = Path(directory) / "job.json"
            with contextlib.ExitStack() as stack:
                stack.enter_context(mock.patch.object(self.subject, "Conn", return_value=connection))
                stack.enter_context(mock.patch.object(self.subject, "receive_job",
                                                     return_value=("abcd", 4, original_job)))
                route = stack.enter_context(mock.patch.object(self.subject, "send_block"))
                stack.enter_context(mock.patch.object(self.subject, "read_full_answer", side_effect=read_answer))
                stack.enter_context(mock.patch.object(self.subject.time, "monotonic", clock.monotonic))
                stack.enter_context(mock.patch.object(self.subject.time, "sleep", clock.sleep))
                stack.enter_context(mock.patch.object(self.subject, "OUT", directory))
                stack.enter_context(mock.patch.object(self.subject, "JOB", str(receipt_path)))
                stack.enter_context(contextlib.redirect_stdout(output))
                self.subject.cycle(REGISTRY, wait_s=wait_s)
            receipt = json.loads(receipt_path.read_text())
        # Every outcome retains one original routing act and one opaque read.
        route.assert_called_once()
        self.assertEqual(route.call_args.args[1], ORIGINAL_JOB)
        self.assertEqual(original_job, ORIGINAL_JOB)
        self.assertEqual(len(answer_read_times), 1)
        self.assertAlmostEqual(answer_read_times[0], 100.0 + wait_s)
        self.assertEqual(receipt["job_id"], ORIGINAL_JOB["job_id"])
        self.assertEqual(receipt["answer"], {"status": ANSWER[0], "en2": ANSWER[1], "nonce": ANSWER[2]})
        self.assertTrue(sock.closed)
        return receipt, sock, output.getvalue()

    def assert_original_submission(self, receipt, sock):
        self.assertTrue(receipt["submission_attempted"])
        self.assertEqual(receipt["pool"], "ACCEPTED — SHARE")
        self.assertEqual(receipt["verdict"], ACCEPTED)
        self.assertEqual(sock.sent, [{
            "id": 100, "method": "mining.submit", "params": [
                self.subject.WALLET, "job-A", "00000007", "65000000", "0000000b",
            ],
        }])

    def assert_stale(self, receipt, sock):
        self.assertEqual(receipt["pool"], STALE_POOL)
        self.assertFalse(receipt["submission_attempted"])
        self.assertIsNone(receipt["verdict"])
        self.assertEqual(sock.sent, [])

    def test_no_notifications_preserve_full_settle_and_original_submission(self):
        receipt, sock, _output = self.run_cycle()
        self.assert_original_submission(receipt, sock)

    def test_clean_false_does_not_replace_original_job_or_answer(self):
        receipt, sock, _output = self.run_cycle(incoming=[frame(notify(False))])
        self.assert_original_submission(receipt, sock)

    def test_clean_true_skips_submission_without_shortening_settle(self):
        receipt, sock, output = self.run_cycle(incoming=[frame(notify(True))])
        self.assert_stale(receipt, sock)
        self.assertIn(STALE_POOL, output)

    def test_true_during_wait_remains_stale_after_false_in_final_drain(self):
        receipt, sock, _output = self.run_cycle(
            incoming=[frame(notify(True))],
            during_answer=lambda current: current.incoming.append(frame(notify(False, "job-C"))))
        self.assert_stale(receipt, sock)

    def test_reused_job_id_with_clean_true_still_invalidates(self):
        receipt, sock, _output = self.run_cycle(incoming=[frame(notify(True, "job-A"))])
        self.assert_stale(receipt, sock)

    def test_zero_settle_still_drains_before_submission(self):
        receipt, sock, _output = self.run_cycle(incoming=[frame(notify(True))], wait_s=0.0)
        self.assert_stale(receipt, sock)

    def test_notification_arriving_during_answer_read_is_observed(self):
        receipt, sock, _output = self.run_cycle(
            during_answer=lambda current: current.incoming.append(frame(notify(True))))
        self.assert_stale(receipt, sock)

    def test_final_drain_continues_through_empty_result_from_partial_frame(self):
        packet = frame(notify(True))
        receipt, sock, _output = self.run_cycle(
            incoming=[packet[:11], packet[11:37], packet[37:]], wait_s=0.0)
        self.assert_stale(receipt, sock)

    def test_drain_completes_prebuffered_partial_and_reads_following_message(self):
        clock = Clock()
        first = frame(notify(False))
        second = frame(notify(True))
        sock = ScriptedSocket(clock, [first[13:], second[:17], second[17:]])
        connection = self.bare_connection(sock, first[:13])
        with mock.patch.object(self.subject.time, "monotonic", clock.monotonic):
            messages = connection.drain()
        self.assertEqual(messages, [notify(False), notify(True)])
        self.assertEqual(connection.buf, b"")
        self.assertEqual(list(sock.incoming), [])

    def test_drain_includes_complete_prebuffered_lines_and_new_socket_bytes(self):
        clock = Clock()
        sock = ScriptedSocket(clock, [frame(notify(True))])
        connection = self.bare_connection(sock, frame(notify(False)))
        with mock.patch.object(self.subject.time, "monotonic", clock.monotonic):
            messages = connection.drain()
        self.assertEqual(messages, [notify(False), notify(True)])
        self.assertEqual(connection.buf, b"")

    def test_clean_jobs_requires_an_exact_boolean(self):
        for value in (0, 1, None, "false", []):
            with self.subTest(value=value):
                with self.assertRaises(self.subject.PoolProtocolError):
                    self.subject.parse_job(notify(value)["params"])
        for value in (False, True):
            with self.subTest(value=value):
                self.assertIs(self.subject.parse_job(notify(value)["params"])["clean_jobs"], value)

    def test_notification_after_actual_submit_does_not_replace_pool_reply(self):
        def after_submit(current):
            current.incoming.append(frame(notify(True)) + frame(ACCEPTED))

        receipt, sock, _output = self.run_cycle(after_submit=after_submit)
        self.assert_original_submission(receipt, sock)

    def test_continuously_readable_drain_has_a_bounded_deadline(self):
        clock = Clock()
        sock = ScriptedSocket(clock, read_cost=0.2)
        sock.repeat_chunk = frame({"method": "mining.set_difficulty", "params": [1]})
        connection = self.bare_connection(sock)
        with mock.patch.object(self.subject.time, "monotonic", clock.monotonic):
            with self.assertRaises(TimeoutError):
                connection.drain(timeout=0.5)
        self.assertLessEqual(clock.now, 100.7)
        self.assertLessEqual(sock.recv_calls, 4)

    def test_settle_disconnect_preserves_wait_and_writes_unattempted_receipt(self):
        receipt, sock, _output = self.run_cycle(incoming=[ConnectionResetError("fixture pool reset")])
        self.assertFalse(receipt["submission_attempted"])
        self.assertIsNone(receipt["verdict"])
        self.assertIn("connection-lost", receipt["pool"])
        self.assertIn("fixture pool reset", receipt["pool"])
        self.assertEqual(sock.sent, [])

    def test_invalid_notification_after_clean_true_is_not_silently_discarded(self):
        receipt, sock, _output = self.run_cycle(
            incoming=[frame(notify(True)) + frame(notify("false"))])
        self.assertFalse(receipt["submission_attempted"])
        self.assertIsNone(receipt["verdict"])
        self.assertIn("invalid-pool-message", receipt["pool"])
        self.assertEqual(sock.sent, [])


class HostFreshnessTests(FreshnessContract, unittest.TestCase):
    relative_path = "host/pfc_bitcoin_autopilot.py"


class InfraFreshnessTests(FreshnessContract, unittest.TestCase):
    relative_path = "infra/host/pfc_bitcoin_autopilot.py"


if __name__ == "__main__":
    unittest.main()
