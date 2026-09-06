"""Transport regressions for cloud execution; never start a live worker or pool.

The cloud checkout supplies host/pfc_bitcoin_autopilot.py and its infra mirror.
All model/registry operations are replaced before any runtime entry point runs.
Only socketpair tests perform real I/O, over local connected sockets.
"""

import contextlib
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
SUBSCRIBE = {
    "id": 1,
    "result": [[["mining.notify", "fixture-session"]], "abcd", 4],
    "error": None,
}
AUTHORIZED = {"id": 2, "result": True, "error": None}
NOTIFY = {
    "id": None,
    "method": "mining.notify",
    "params": [
        "fixture-job", "00" * 32, "", "", [],
        "20000000", "1d00ffff", "65000000", True,
    ],
}
REGISTRY = {"pfc_exec_input": {"offset": 0}, "pfc_on": {"offset": 116}}


class Clock:
    def __init__(self):
        self.now = 100.0

    def monotonic(self):
        return self.now


class ScriptedConnection:
    def __init__(self, clock, replies=()):
        self.clock = clock
        self.replies = list(replies)
        self.sent = []
        self.send_waits = []
        self.waits = []
        self.closed = False

    def send(self, message, timeout=15.0):
        self.send_waits.append((self.clock.now, timeout, message["method"]))
        self.sent.append(message)

    def lines(self, wait=2.0):
        self.waits.append((self.clock.now, wait))
        if self.replies:
            self.clock.now += min(wait, 0.01)
            event = self.replies.pop(0)
            if callable(event):
                return event()
            return event
        self.clock.now += wait
        return []

    def close(self):
        self.closed = True


class CapturedOutput(io.StringIO):
    """Allow main() to configure its stream; import tests use plain StringIO."""

    def reconfigure(self, **_kwargs):
        pass


def load_subject(relative_path):
    path = ROOT / relative_path
    name = "transport_subject_" + relative_path.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    output = io.StringIO()
    # Embedding programs own argv/stdout. Importing make_prefix must not parse
    # these unrelated arguments or require a terminal-specific stream method.
    with mock.patch.object(sys, "argv", ["embedding-program", "--pool", "unrelated"]):
        with contextlib.redirect_stdout(output):
            spec.loader.exec_module(module)
    return module, output.getvalue()


class TransportContract:
    relative_path = None

    def setUp(self):
        self.subject, self.import_output = load_subject(self.relative_path)

    def connection(self, replies=()):
        clock = Clock()
        return clock, ScriptedConnection(clock, replies)

    def bare_connection(self, sock, buffered=b""):
        connection = self.subject.Conn.__new__(self.subject.Conn)
        connection.s = sock
        connection.buf = buffered
        return connection

    def assert_no_routing_after_handshake_failure(self, replies, exception_type):
        clock, connection = self.connection(replies)
        with mock.patch.object(self.subject, "Conn", return_value=connection):
            with mock.patch.object(self.subject.time, "monotonic", clock.monotonic):
                with mock.patch.object(self.subject, "send_block") as route:
                    with self.assertRaises(exception_type) as caught:
                        self.subject.cycle(REGISTRY, wait_s=0.0)
        route.assert_not_called()
        self.assertFalse(any(m["method"] == "mining.submit" for m in connection.sent))
        self.assertTrue(connection.closed)
        return caught.exception

    def cycle_receipt(self, replies=(), submit_error=None, submit_elapsed=0.0):
        clock, connection = self.connection([[SUBSCRIBE, AUTHORIZED, NOTIFY], *replies])
        ordinary_send = connection.send

        def send(message, timeout=15.0):
            ordinary_send(message, timeout=timeout)
            if message["method"] == "mining.submit":
                clock.now += submit_elapsed
                if submit_error is not None:
                    raise submit_error

        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            receipt_path = Path(directory) / "job.json"
            with contextlib.ExitStack() as stack:
                stack.enter_context(mock.patch.object(self.subject, "Conn", return_value=connection))
                stack.enter_context(mock.patch.object(connection, "send", side_effect=send))
                stack.enter_context(mock.patch.object(self.subject.time, "monotonic", clock.monotonic))
                stack.enter_context(mock.patch.object(self.subject.time, "sleep"))
                stack.enter_context(mock.patch.object(self.subject, "send_block"))
                # This is a fixed opaque worker output, not a readiness assertion.
                stack.enter_context(mock.patch.object(self.subject, "read_full_answer", return_value=(1, 7, 11)))
                stack.enter_context(mock.patch.object(self.subject, "OUT", directory))
                stack.enter_context(mock.patch.object(self.subject, "JOB", str(receipt_path)))
                stack.enter_context(contextlib.redirect_stdout(output))
                self.subject.cycle(REGISTRY, wait_s=0.0)
            receipt = json.loads(receipt_path.read_text())
        return receipt, connection, clock, output.getvalue()

    def test_import_preserves_embedding_argv_and_stdout(self):
        self.assertEqual(self.import_output, "")
        self.assertEqual(self.subject.WAIT, 3.0)
        self.assertTrue(callable(self.subject.make_prefix))
        self.assertTrue(issubclass(self.subject.PoolProtocolError, ConnectionError))

    def test_subscribe_and_notify_do_not_complete_before_delayed_auth(self):
        clock, connection = self.connection()
        auth_delivered = []

        def authorization_reply():
            auth_delivered.append(True)
            return [AUTHORIZED]

        connection.replies = [[SUBSCRIBE, NOTIFY], [], authorization_reply]
        with mock.patch.object(self.subject.time, "monotonic", clock.monotonic):
            en1, en2size, job = self.subject.receive_job(connection, timeout=1.0)
        self.assertEqual(auth_delivered, [True])
        self.assertEqual((en1, en2size, job["job_id"]), ("abcd", 4, "fixture-job"))
        self.assertEqual(connection.sent, [
            {"id": 1, "method": "mining.subscribe", "params": ["pfc-autopilot/1.0"]},
            {"id": 2, "method": "mining.authorize", "params": [self.subject.WALLET, "x"]},
        ])
        for started, timeout, _method in connection.send_waits:
            self.assertGreater(timeout, 0)
            self.assertLessEqual(timeout, 101.0 - started + 1e-9)

    def test_authorized_session_still_waits_for_notify(self):
        clock, connection = self.connection([[SUBSCRIBE], [AUTHORIZED], [], [NOTIFY]])
        with mock.patch.object(self.subject.time, "monotonic", clock.monotonic):
            _, _, job = self.subject.receive_job(connection, timeout=1.0)
        self.assertEqual(job["job_id"], "fixture-job")
        self.assertEqual(len(connection.waits), 4)

    def test_auth_rejection_preserves_provider_error_and_never_routes(self):
        for result in (False, None):
            with self.subTest(result=result):
                denied = {"id": 2, "result": result,
                          "error": [24, "Provider rejected fixture worker", None]}
                error = self.assert_no_routing_after_handshake_failure(
                    [[SUBSCRIBE, NOTIFY], [denied]], self.subject.PoolProtocolError)
                self.assertIn("Provider rejected fixture worker", str(error))

    def test_false_auth_without_error_still_never_routes(self):
        self.assert_no_routing_after_handshake_failure(
            [[SUBSCRIBE, NOTIFY], [{"id": 2, "result": False, "error": None}]],
            self.subject.PoolProtocolError)

    def test_subscription_error_preserves_provider_message(self):
        denied = {"id": 1, "result": None,
                  "error": [20, "Provider subscription unavailable", None]}
        error = self.assert_no_routing_after_handshake_failure(
            [[NOTIFY, denied]], self.subject.PoolProtocolError)
        self.assertIn("Provider subscription unavailable", str(error))

    def test_notify_without_subscription_times_out_before_routing(self):
        self.assert_no_routing_after_handshake_failure([[NOTIFY]], TimeoutError)

    def test_incomplete_subscription_is_not_routed(self):
        malformed = {"id": 1, "result": [[], "abcd"], "error": None}
        self.assert_no_routing_after_handshake_failure(
            [[malformed, NOTIFY]], self.subject.PoolProtocolError)

    def test_handshake_uses_monotonic_deadline_and_caps_socket_wait(self):
        clock, connection = self.connection()
        with mock.patch.object(self.subject.time, "monotonic", clock.monotonic):
            with mock.patch.object(self.subject.time, "time",
                                   side_effect=AssertionError("wall clock used for deadline")):
                with self.assertRaises(TimeoutError):
                    self.subject.receive_job(connection, timeout=0.25)
        self.assertTrue(connection.waits)
        self.assertEqual(len(connection.send_waits), 1)
        self.assertAlmostEqual(connection.send_waits[0][1], 0.25)
        for started, wait in connection.waits:
            self.assertGreater(wait, 0)
            self.assertLessEqual(wait, 100.25 - started + 1e-9)
        self.assertAlmostEqual(clock.now, 100.25)

    def test_socketpair_reassembles_fragments_and_multiple_messages(self):
        left, right = socket.socketpair()
        connection = self.bare_connection(left)
        try:
            right.sendall(b'{"id":2,"res')
            self.assertEqual(connection.lines(wait=0.1), [])
            right.sendall(b'ult":true,"error":null}\n{"id":100,"result":false}\n')
            self.assertEqual(connection.lines(wait=0.1), [
                {"id": 2, "result": True, "error": None},
                {"id": 100, "result": False},
            ])
            self.assertEqual(connection.buf, b"")
        finally:
            connection.close()
            right.close()

    def test_complete_buffered_line_is_delivered_without_recv(self):
        sock = mock.Mock()
        sock.recv.side_effect = AssertionError("buffered answer must not wait on socket")
        connection = self.bare_connection(sock, b'{"id":2,"result":true}\n{"partial":')
        self.assertEqual(connection.lines(wait=0.1), [{"id": 2, "result": True}])
        self.assertEqual(connection.buf, b'{"partial":')
        sock.recv.assert_not_called()

    def test_socketpair_eof_is_explicit_connection_failure(self):
        left, right = socket.socketpair()
        connection = self.bare_connection(left)
        right.close()
        try:
            with self.assertRaises(ConnectionError):
                connection.lines(wait=0.1)
        finally:
            connection.close()

    def test_connection_reset_is_not_disguised_as_empty_poll(self):
        sock = mock.Mock()
        sock.recv.side_effect = ConnectionResetError("fixture peer reset")
        connection = self.bare_connection(sock)
        with self.assertRaises(ConnectionResetError):
            connection.lines(wait=0.1)

    def test_timeout_and_would_block_preserve_partial_buffer(self):
        for error in (socket.timeout("fixture timeout"), BlockingIOError("fixture would block")):
            with self.subTest(error=type(error).__name__):
                sock = mock.Mock()
                sock.recv.side_effect = error
                connection = self.bare_connection(sock, b'{"id":')
                self.assertEqual(connection.lines(wait=0.1), [])
                self.assertEqual(connection.buf, b'{"id":')

    def test_send_restores_explicit_timeout_after_tiny_receive_timeout(self):
        sock = mock.Mock()
        sock.recv.return_value = b'{"id":2,"result":true}\n'
        connection = self.bare_connection(sock)
        self.assertEqual(connection.lines(wait=0.0001), [{"id": 2, "result": True}])
        submission = {"id": 100, "method": "mining.submit", "params": ["fixture"]}
        connection.send(submission, timeout=12.0)
        self.assertEqual(sock.settimeout.call_args_list, [mock.call(0.0001), mock.call(12.0)])
        wire = sock.sendall.call_args.args[0]
        self.assertTrue(wire.endswith(b"\n"))
        self.assertEqual(json.loads(wire), submission)

    def test_null_result_pool_error_is_preserved_as_rejection(self):
        rejected = {"id": 100, "result": None, "error": [21, "Job not found", None]}
        receipt, connection, _clock, output = self.cycle_receipt(replies=[[rejected]])
        self.assertEqual(receipt["pool"], "REJECTED (Job not found)")
        self.assertEqual(receipt["verdict"], rejected)
        self.assertEqual(receipt["job_id"], "fixture-job")
        self.assertIn("REJECTED (Job not found)", output)
        self.assertTrue(connection.closed)

    def test_broken_submit_send_still_writes_transport_failure_receipt(self):
        receipt, connection, _clock, output = self.cycle_receipt(
            submit_error=BrokenPipeError("fixture socket closed during send"))
        self.assertIn("connection-lost", receipt["pool"])
        self.assertIn("fixture socket closed during send", receipt["pool"])
        self.assertIsNone(receipt["verdict"])
        self.assertEqual(receipt["job_id"], "fixture-job")
        self.assertEqual(receipt["answer"], {"status": 1, "en2": 7, "nonce": 11})
        self.assertIn("submission attempted", output)
        self.assertTrue(connection.closed)

    def test_submission_wait_budget_includes_time_spent_sending(self):
        receipt, connection, clock, _output = self.cycle_receipt(submit_elapsed=11.5)
        self.assertEqual(receipt["pool"], "no-reply")
        submitted_at, send_timeout, method = connection.send_waits[-1]
        self.assertEqual(method, "mining.submit")
        self.assertEqual(send_timeout, 12.0)
        receipt_polls = [(started, wait) for started, wait in connection.waits if started >= submitted_at]
        self.assertTrue(receipt_polls)
        for started, wait in receipt_polls:
            self.assertLessEqual(wait, submitted_at + 12.0 - started + 1e-9)
        self.assertAlmostEqual(clock.now - submitted_at, 12.0)
        self.assertTrue(connection.closed)

    def test_cli_help_does_not_read_registry_or_start_cycle(self):
        with mock.patch.object(self.subject, "open", create=True) as registry_open:
            registry_open.side_effect = AssertionError("help must not access machine files")
            with mock.patch.object(self.subject, "cycle") as cycle:
                output = CapturedOutput()
                with contextlib.redirect_stdout(output):
                    with self.assertRaises(SystemExit) as caught:
                        self.subject.main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("usage:", output.getvalue().lower())
        registry_open.assert_not_called()
        cycle.assert_not_called()

    def test_cli_defaults_forward_three_second_wait(self):
        with mock.patch.object(self.subject, "open", mock.mock_open(read_data=json.dumps(REGISTRY)),
                               create=True):
            with mock.patch.object(self.subject, "cycle", side_effect=KeyboardInterrupt) as cycle:
                with mock.patch.object(self.subject.time, "sleep"):
                    with contextlib.redirect_stdout(CapturedOutput()):
                        result = self.subject.main([])
        self.assertEqual(result, 0)
        cycle.assert_called_once()
        args, kwargs = cycle.call_args
        self.assertEqual(args[0], REGISTRY)
        forwarded_wait = kwargs.get("wait_s", args[1] if len(args) > 1 else None)
        self.assertEqual(forwarded_wait, 3.0)

    def test_cli_explicit_positions_forward_cycle_count_and_wait(self):
        with mock.patch.object(self.subject, "open", mock.mock_open(read_data=json.dumps(REGISTRY)),
                               create=True):
            with mock.patch.object(self.subject, "cycle") as cycle:
                with mock.patch.object(self.subject.time, "sleep"):
                    with contextlib.redirect_stdout(CapturedOutput()):
                        result = self.subject.main(["2", "0.25"])
        self.assertEqual(result, 0)
        self.assertEqual(cycle.call_count, 2)
        for args, kwargs in cycle.call_args_list:
            self.assertEqual(args[0], REGISTRY)
            self.assertEqual(kwargs.get("wait_s", args[1] if len(args) > 1 else None), 0.25)

    def test_cli_invalid_wait_fails_before_registry_access(self):
        with mock.patch.object(self.subject, "open", create=True) as registry_open:
            with mock.patch.object(self.subject, "cycle") as cycle:
                with contextlib.redirect_stdout(CapturedOutput()), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as caught:
                        self.subject.main(["1", "not-a-number"])
        self.assertEqual(caught.exception.code, 2)
        registry_open.assert_not_called()
        cycle.assert_not_called()


class HostTransportTests(TransportContract, unittest.TestCase):
    relative_path = "host/pfc_bitcoin_autopilot.py"


class InfraTransportTests(TransportContract, unittest.TestCase):
    relative_path = "infra/host/pfc_bitcoin_autopilot.py"


if __name__ == "__main__":
    unittest.main()
