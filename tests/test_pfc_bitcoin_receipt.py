"""Cloud-only atomic receipt tests; use fixture files and mocked pool/worker I/O.

The concurrent case checks publication integrity, not timing or throughput.
On Windows an explicit sharing failure must preserve the old complete receipt.
"""

import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
OLD_BYTES = b'{ "job_id": "previous-fixture", "answer": null, "pool": "no-reply" }\n'
NEW_RECEIPT = {
    "job_id": "next-fixture", "zbits": 23,
    "answer": {"status": 0, "en2": 0, "nonce": 0}, "answer_error": None,
    "submission_attempted": True,
    "verdict": {"id": 100, "result": None, "error": [21, "Job not found", None]},
    "pool": "REJECTED (Job not found)",
}
JOB = {
    "job_id": "cycle-fixture", "prevhash": "00" * 32,
    "coinb1": "", "coinb2": "", "merkle_branch": [],
    "version": "20000000", "nbits": "1d00ffff", "ntime": "65000000",
    "clean_jobs": True,
}


def load_subject(relative_path):
    name = "receipt_" + relative_path.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    subject = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        with mock.patch.object(sys, "argv", ["fixture-embedding-program"]):
            spec.loader.exec_module(subject)
    return subject


class StagingWriter:
    """A real staging stream with one explicit write, flush, or close fault."""

    def __init__(self, stream, failure=None, pause=None, release=None):
        self.stream = stream
        self.failure = failure
        self.pause = pause
        self.release = release

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        result = self.stream.__exit__(*args)
        if self.failure == "close":
            raise OSError("fixture staging close failure")
        return result

    def write(self, payload):
        cut = max(1, len(payload) // 2)
        if self.failure == "write":
            self.stream.write(payload[:cut])
            self.stream.flush()
            raise OSError("fixture staging write failure")
        if self.failure == "short-write":
            return self.stream.write(payload[:cut])
        if self.pause is not None:
            self.stream.write(payload[:cut])
            self.stream.flush()
            self.pause.set()
            if not self.release.wait(5.0):
                raise TimeoutError("fixture did not release staged writer")
            self.stream.write(payload[cut:])
            return len(payload)
        return self.stream.write(payload)

    def flush(self):
        self.stream.flush()
        if self.failure == "flush":
            raise OSError("fixture staging flush failure")


class PoolFixture:
    def __init__(self):
        self.sent = []
        self.closed = False

    def drain(self, timeout=1.0):
        return []

    def send(self, message, timeout=15.0):
        self.sent.append(message)

    def lines(self, wait=2.0):
        return [{"id": 100, "result": True, "error": None}]

    def close(self):
        self.closed = True


class ReceiptCases:
    def setUp(self):
        self.subject = load_subject(self.relative_path)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "autopilot_job.json"
        self.path.write_bytes(OLD_BYTES)
        # A similarly named file belongs to another operation and must survive.
        self.unrelated = self.path.with_name("." + self.path.name + ".unrelated.tmp")
        self.unrelated.write_bytes(b"unrelated operation fixture bytes")
        self.initial_names = {path.name for path in self.path.parent.iterdir()}
        self.job_patch = mock.patch.object(self.subject, "JOB", str(self.path))
        self.job_patch.start()
        self.addCleanup(self.job_patch.stop)

    def assert_original_preserved_and_staging_cleaned(self):
        self.assertEqual(self.path.read_bytes(), OLD_BYTES)
        self.assertEqual(json.loads(self.path.read_bytes())["job_id"], "previous-fixture")
        self.assertEqual(self.unrelated.read_bytes(), b"unrelated operation fixture bytes")
        self.assertEqual({path.name for path in self.path.parent.iterdir()}, self.initial_names)

    @contextlib.contextmanager
    def wrapped_staging(self, **kwargs):
        real_temporary_file = self.subject.tempfile.NamedTemporaryFile
        writers = []

        def temporary_file(*args, **options):
            writer = StagingWriter(real_temporary_file(*args, **options), **kwargs)
            writers.append(writer)
            return writer

        with mock.patch.object(self.subject.tempfile, "NamedTemporaryFile", side_effect=temporary_file):
            yield writers

    @contextlib.contextmanager
    def cycle_context(self):
        connection = PoolFixture()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(self.subject, "Conn", return_value=connection))
            stack.enter_context(mock.patch.object(self.subject, "receive_job",
                                                 return_value=("abcd", 4, copy.deepcopy(JOB))))
            route = stack.enter_context(mock.patch.object(self.subject, "send_block"))
            wait = stack.enter_context(mock.patch.object(self.subject, "wait_for_job", return_value=False))
            answer = stack.enter_context(mock.patch.object(self.subject, "read_full_answer", return_value=(0, 0, 0)))
            stack.enter_context(mock.patch.object(self.subject, "OUT", self.directory.name))
            publication = stack.enter_context(mock.patch.object(
                self.subject, "publish_receipt", wraps=self.subject.publish_receipt,
            ))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            yield connection, route, wait, answer, publication

    def test_success_replaces_complete_receipt_from_same_directory(self):
        real_replace = self.subject.os.replace
        replacements = []

        def replace(source, destination):
            source = Path(source)
            destination = Path(destination)
            self.assertEqual(source.parent.resolve(), self.path.parent.resolve())
            self.assertNotEqual(source.resolve(), destination.resolve())
            self.assertEqual(destination.resolve(), self.path.resolve())
            self.assertEqual(destination.read_bytes(), OLD_BYTES)
            self.assertEqual(json.loads(source.read_text(encoding="utf-8")), NEW_RECEIPT)
            replacements.append((source, destination))
            return real_replace(source, destination)

        with mock.patch.object(self.subject.os, "replace", side_effect=replace):
            self.subject.publish_receipt(NEW_RECEIPT)
        self.assertEqual(len(replacements), 1)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), NEW_RECEIPT)
        self.assertEqual({path.name for path in self.path.parent.iterdir()}, self.initial_names)
        self.assertEqual(self.unrelated.read_bytes(), b"unrelated operation fixture bytes")

    def test_success_can_publish_the_first_receipt(self):
        self.path.unlink()
        self.subject.publish_receipt(NEW_RECEIPT)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), NEW_RECEIPT)
        self.assertEqual({path.name for path in self.path.parent.iterdir()}, self.initial_names)

    def test_serialization_failure_preserves_exact_old_bytes_and_unrelated_file(self):
        malformed = dict(NEW_RECEIPT, unserializable=object())
        with self.assertRaises(TypeError):
            self.subject.publish_receipt(malformed)
        self.assert_original_preserved_and_staging_cleaned()

    def test_partial_write_failure_closes_stream_and_preserves_old_receipt(self):
        with self.wrapped_staging(failure="write") as writers:
            with self.assertRaisesRegex(OSError, "fixture staging write failure"):
                self.subject.publish_receipt(NEW_RECEIPT)
        self.assertEqual(len(writers), 1)
        self.assertTrue(writers[0].closed)
        self.assert_original_preserved_and_staging_cleaned()

    def test_flush_failure_closes_stream_and_preserves_old_receipt(self):
        with self.wrapped_staging(failure="flush") as writers:
            with self.assertRaisesRegex(OSError, "fixture staging flush failure"):
                self.subject.publish_receipt(NEW_RECEIPT)
        self.assertEqual(len(writers), 1)
        self.assertTrue(writers[0].closed)
        self.assert_original_preserved_and_staging_cleaned()

    def test_short_write_is_reported_without_publishing_truncated_json(self):
        with self.wrapped_staging(failure="short-write") as writers:
            with self.assertRaises(OSError):
                self.subject.publish_receipt(NEW_RECEIPT)
        self.assertEqual(len(writers), 1)
        self.assertTrue(writers[0].closed)
        self.assert_original_preserved_and_staging_cleaned()

    def test_close_failure_preserves_old_receipt_and_removes_staging_file(self):
        with self.wrapped_staging(failure="close") as writers:
            with self.assertRaisesRegex(OSError, "fixture staging close failure"):
                self.subject.publish_receipt(NEW_RECEIPT)
        self.assertEqual(len(writers), 1)
        self.assertTrue(writers[0].closed)
        self.assert_original_preserved_and_staging_cleaned()

    def test_replace_failure_propagates_and_removes_only_its_staging_file(self):
        failure = OSError("fixture receipt replacement failure")
        with mock.patch.object(self.subject.os, "replace", side_effect=failure) as replace:
            with self.assertRaises(OSError) as caught:
                self.subject.publish_receipt(NEW_RECEIPT)
        self.assertIs(caught.exception, failure)
        replace.assert_called_once()
        self.assert_original_preserved_and_staging_cleaned()

    def test_concurrent_reader_observes_only_complete_previous_or_new_receipts(self):
        staged = threading.Event()
        release = threading.Event()
        completed = threading.Event()
        errors = []
        next_receipt = dict(NEW_RECEIPT, detail="fixture payload " * 4096)
        previous_receipt = json.loads(OLD_BYTES)

        def publish():
            try:
                self.subject.publish_receipt(next_receipt)
            except Exception as error:
                errors.append(error)
            finally:
                completed.set()

        with self.wrapped_staging(pause=staged, release=release) as writers:
            writer = threading.Thread(target=publish, name="fixture-receipt-publisher", daemon=True)
            writer.start()
            try:
                self.assertTrue(staged.wait(5.0), "publisher did not reach its staging write")
                # The writer is paused after flushing only half of the new JSON.
                for _ in range(8):
                    self.assertEqual(self.path.read_bytes(), OLD_BYTES)
                release.set()
                deadline = time.monotonic() + 5.0
                while not completed.is_set() and time.monotonic() < deadline:
                    payload = self.path.read_bytes()
                    value = json.loads(payload)
                    self.assertIn(value, [previous_receipt, next_receipt])
            finally:
                release.set()
                writer.join(5.0)
        self.assertFalse(writer.is_alive(), "fixture publisher did not finish")
        self.assertEqual(len(writers), 1)
        self.assertTrue(writers[0].closed)
        if errors:
            self.assertEqual(len(errors), 1)
            error = errors[0]
            if not (os.name == "nt" and isinstance(error, OSError)
                    and getattr(error, "winerror", None) in (32, 33)):
                raise error
            self.assert_original_preserved_and_staging_cleaned()
            print("Windows concurrent publication surfaced %r; previous receipt remains complete" % error,
                  file=sys.stderr)
        else:
            final = json.loads(self.path.read_text(encoding="utf-8"))
            self.assertEqual(final, next_receipt)
            self.assertEqual({path.name for path in self.path.parent.iterdir()}, self.initial_names)
            self.assertEqual(self.unrelated.read_bytes(), b"unrelated operation fixture bytes")
        self.assertTrue(completed.is_set())

    def test_cycle_publishes_one_complete_receipt_through_helper(self):
        with self.cycle_context() as (connection, route, wait, answer, publication):
            self.subject.cycle({}, wait_s=0.0)
        route.assert_called_once()
        wait.assert_called_once_with(connection, 0.0)
        answer.assert_called_once_with()
        publication.assert_called_once()
        published = publication.call_args.args[0]
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), published)
        self.assertEqual(published["job_id"], JOB["job_id"])
        self.assertEqual(published["answer"], {"status": 0, "en2": 0, "nonce": 0})
        self.assertTrue(published["submission_attempted"])
        self.assertEqual(published["verdict"], {"id": 100, "result": True, "error": None})
        self.assertEqual(len(connection.sent), 1)
        self.assertTrue(connection.closed)

    def test_cycle_surfaces_publication_failure_without_losing_previous_receipt(self):
        failure = OSError("fixture cycle receipt replacement failure")
        with self.cycle_context() as (connection, route, wait, answer, publication):
            with mock.patch.object(self.subject.os, "replace", side_effect=failure):
                with self.assertRaises(OSError) as caught:
                    self.subject.cycle({}, wait_s=0.0)
        self.assertIs(caught.exception, failure)
        publication.assert_called_once()
        route.assert_called_once()
        wait.assert_called_once_with(connection, 0.0)
        answer.assert_called_once_with()
        self.assertEqual(len(connection.sent), 1)
        self.assertTrue(connection.closed)
        self.assert_original_preserved_and_staging_cleaned()


class HostReceiptTests(ReceiptCases, unittest.TestCase):
    relative_path = "host/pfc_bitcoin_autopilot.py"


class InfraReceiptTests(ReceiptCases, unittest.TestCase):
    relative_path = "infra/host/pfc_bitcoin_autopilot.py"


if __name__ == "__main__":
    unittest.main()
