"""Real two-connection regressions for one-generation release reads.

Only scheduling is instrumented. Writers use public ReleaseDesk operations against
an on-disk database; WAL lets those commits finish while the reader is paused.
"""
import io
import json
import sqlite3
import tempfile
import threading
import unittest
import zipfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from desk import HoldError, InvalidState, ReleaseDesk, sha256_bytes


class ReadSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / "release.sqlite3"
        self.source = self.root / "source.txt"
        self.source.write_bytes(b"master one\n")
        self.es = self.root / "es.srt"
        self.es.write_bytes(b"subtitle one\n")
        self.fr = self.root / "fr.srt"
        self.fr.write_bytes(b"sous-titre un\n")
        self.reader = ReleaseDesk(self.db)
        self.writer = ReleaseDesk(self.db)
        with closing(self.reader.conn()) as c:
            self.assertEqual(c.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
        self.reader.create_title("create", "title", self.source, [
            {"locale": "es", "territory": "US", "kind": "subtitle"},
            {"locale": "fr", "territory": "CA", "kind": "subtitle"},
        ])
        self.reader.set_rights_ready("rights", "title", True)
        self.add_approved(self.reader, "es", "US", self.es, "es")
        self.add_approved(self.reader, "fr", "CA", self.fr, "fr")

    def add_approved(self, target, locale, territory, path, request):
        row = target.add_variant(request + "-add", "title", locale, territory, "subtitle", path)
        target.approve_variant(request + "-approve", "title", locale, territory,
                               "subtitle", "reviewer-" + locale, row["revision"], row["content_sha256"])
        return row

    def race(self, read, write, prefix="SELECT * FROM variants", occurrence=1):
        """Commit a real writer between two reader queries; fail on missed barriers."""
        reached = threading.Event()
        finished = threading.Event()
        errors = []
        original = self.reader.conn
        connections = []

        class Boundary:
            def __init__(self):
                self.connection = original()
                self.matches = 0
                connections.append(self)

            def execute(self, sql, *args):
                if sql.startswith(prefix):
                    self.matches += 1
                    if self.matches == occurrence:
                        reached.set()
                        if not finished.wait(5):
                            raise RuntimeError("writer did not commit at the read barrier")
                return self.connection.execute(sql, *args)

            def close(self):
                self.connection.close()

        def worker():
            try:
                if not reached.wait(5):
                    raise RuntimeError("reader never reached the expected SQL boundary")
                write()
            except BaseException as error:
                errors.append(error)
            finally:
                finished.set()

        thread = threading.Thread(target=worker, name="release-snapshot-writer", daemon=True)
        thread.start()
        try:
            with patch.object(self.reader, "conn", Boundary):
                result = read()
        finally:
            thread.join(6)
        self.assertFalse(thread.is_alive(), "writer must finish before fixture cleanup")
        if errors:
            raise errors[0]
        self.assertTrue(reached.is_set(), "test must exercise the intended interleaving")
        self.assertEqual(len(connections), 1, "one public projection must use one connection")
        return result

    def revoke(self):
        return self.writer.set_rights_ready("revoke", "title", False)

    def add_reviewer(self):
        row = self.writer.status("title")["variants"][0]
        return self.writer.approve_variant("second-review", "title", "es", "US", "subtitle",
                                           "second-reviewer", row["revision"], row["content_sha256"])

    def test_rights_revocation_cannot_splice_ready_and_revoked_audit(self):
        before = self.reader.status("title")
        raced = self.race(lambda: self.reader.status("title"), self.revoke)
        self.assertEqual(raced, before)
        after = self.reader.status("title")
        self.assertEqual(after["release_status"], "HOLD")
        self.assertFalse(after["owner_supplied_rights_ready"])
        self.assertEqual(after["events"][-1]["detail"], {"rights_ready": False})

    def test_rights_restoration_does_not_clear_an_older_hold(self):
        self.revoke()
        before = self.reader.status("title")
        raced = self.race(lambda: self.reader.status("title"),
                          lambda: self.writer.set_rights_ready("restore", "title", True))
        self.assertEqual(raced, before)
        self.assertEqual(self.reader.status("title")["release_status"], "READY_FOR_LOCAL_HANDOFF")

    def test_source_change_keeps_source_variants_and_events_together(self):
        before = self.reader.status("title")
        self.source.write_bytes(b"master two\n")
        raced = self.race(lambda: self.reader.status("title"),
                          lambda: self.writer.update_source("source-two", "title", self.source))
        self.assertEqual(raced, before)
        after = self.reader.status("title")
        self.assertNotEqual(after["source"]["sha256"], before["source"]["sha256"])
        self.assertIn("STALE_SOURCE_BINDING:es/US/subtitle", after["holds"])
        self.assertIn("STALE_SOURCE_BINDING:fr/CA/subtitle", after["holds"])

    def test_revision_between_variant_and_approval_read_is_coherent(self):
        before = self.reader.status("title")
        self.es.write_bytes(b"subtitle two\n")
        raced = self.race(lambda: self.reader.status("title"),
                          lambda: self.writer.add_variant("es-two", "title", "es", "US", "subtitle", self.es),
                          prefix="SELECT reviewer_id,approved_at")
        self.assertEqual(raced, before)
        after = self.reader.status("title")
        self.assertEqual(after["variants"][0]["revision"], 2)
        self.assertIn("MISSING_CURRENT_APPROVAL:es/US/subtitle", after["holds"])

    def test_new_approval_is_not_injected_between_projection_and_audit(self):
        before = self.reader.status("title")
        raced = self.race(lambda: self.reader.status("title"), self.add_reviewer,
                          prefix="SELECT seq,event_kind")
        self.assertEqual(raced, before)
        after = self.reader.status("title")
        self.assertEqual(len(after["variants"][0]["approvals"]), 2)
        self.assertEqual(after["events"][-1]["detail"]["reviewer_id"], "second-reviewer")

    def test_multiple_variant_reads_cannot_mix_revisions(self):
        before = self.reader.status("title")
        self.es.write_bytes(b"subtitle two\n")
        self.fr.write_bytes(b"sous-titre deux\n")

        def revise_both():
            self.add_approved(self.writer, "es", "US", self.es, "es-two")
            self.add_approved(self.writer, "fr", "CA", self.fr, "fr-two")

        raced = self.race(lambda: self.reader.status("title"), revise_both, occurrence=2)
        self.assertEqual(raced, before)
        self.assertEqual([v["revision"] for v in self.reader.status("title")["variants"]], [2, 2])

    def test_missing_variant_stays_missing_for_the_retained_generation(self):
        # Use supported creation of a second title whose required variant is absent.
        self.reader.create_title("empty-create", "empty", self.source, [
            {"locale": "es", "territory": "US", "kind": "subtitle"},
        ])
        self.reader.set_rights_ready("empty-ready", "empty", True)
        before = self.reader.status("empty")

        def populate():
            row = self.writer.add_variant("empty-add", "empty", "es", "US", "subtitle", self.es)
            self.writer.approve_variant("empty-approve", "empty", "es", "US", "subtitle",
                                        "reviewer", row["revision"], row["content_sha256"])

        raced = self.race(lambda: self.reader.status("empty"), populate)
        self.assertEqual(raced, before)
        self.assertEqual(self.reader.status("empty")["release_status"], "READY_FOR_LOCAL_HANDOFF")

    def test_package_json_markdown_and_receipt_share_one_generation(self):
        expected, receipt = self.reader.build_package("title")
        data, raced_receipt = self.race(lambda: self.reader.build_package("title"), self.revoke,
                                       prefix="SELECT seq,event_kind")
        self.assertEqual(data, expected)
        self.assertEqual(raced_receipt, receipt)
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            stored = json.loads(package.read("receipt.json"))
            self.assertEqual(stored["state_sha256"], sha256_bytes(package.read("release.json")))
            self.assertEqual(stored["markdown_sha256"], sha256_bytes(package.read("release.md")))
            self.assertFalse(json.loads(package.read("release.json"))["external_publish_authorized"])
        with self.assertRaises(HoldError):
            self.reader.build_package("title")

    def test_export_inherits_snapshot_without_changing_output_contract(self):
        expected, receipt = self.reader.build_package("title")
        path = self.root / "release.zip"
        exported = self.race(lambda: self.reader.export_package("title", path), self.add_reviewer)
        self.assertEqual(path.read_bytes(), expected)
        self.assertEqual(exported["package_sha256"], receipt["package_sha256"])
        self.assertFalse(self.reader.verify_package("title", path)["valid"])
        with self.assertRaises(FileExistsError):
            self.reader.export_package("title", path)

    def test_verification_is_point_in_time_not_perpetual_clearance(self):
        path = self.root / "release.zip"
        self.reader.export_package("title", path)
        result = self.race(lambda: self.reader.verify_package("title", path), self.add_reviewer,
                           prefix="SELECT seq,event_kind")
        self.assertTrue(result["valid"])
        self.assertFalse(self.reader.verify_package("title", path)["valid"])

    def test_every_projection_select_is_in_one_read_transaction(self):
        original = self.reader.conn
        trace = []

        class Observed:
            def __init__(self):
                self.connection = original()

            def execute(self, sql, *args):
                result = self.connection.execute(sql, *args)
                trace.append((sql, self.connection.in_transaction))
                return result

            def close(self):
                trace.append(("CLOSE", self.connection.in_transaction))
                self.connection.close()

        with patch.object(self.reader, "conn", Observed):
            self.reader.status("title")
        selects = [(sql, active) for sql, active in trace if sql.startswith("SELECT")]
        self.assertGreaterEqual(len(selects), 6)
        self.assertTrue(all(active for _, active in selects), trace)
        self.assertEqual(trace[0], ("BEGIN", True))
        self.assertEqual(trace[-2:], [("COMMIT", False), ("CLOSE", False)])

    def test_reader_sql_failure_closes_transaction_and_allows_next_writer(self):
        original = self.reader.conn
        closed = []

        class Broken:
            def __init__(self):
                self.connection = original()

            def execute(self, sql, *args):
                if sql.startswith("SELECT * FROM variants"):
                    raise sqlite3.OperationalError("injected read failure")
                return self.connection.execute(sql, *args)

            def close(self):
                closed.append(self.connection)
                self.connection.close()

        with patch.object(self.reader, "conn", Broken):
            with self.assertRaises(sqlite3.OperationalError):
                self.reader.export_package("title", self.root / "never.zip")
        self.assertFalse((self.root / "never.zip").exists())
        self.assertEqual(len(closed), 1)
        with self.assertRaises(sqlite3.ProgrammingError):
            closed[0].execute("SELECT 1")
        # A dangling WAL reader prevents journal-mode transition; this checks cleanup.
        with closing(self.writer.conn()) as c:
            c.execute("PRAGMA busy_timeout=0")
            self.assertEqual(c.execute("PRAGMA journal_mode=DELETE").fetchone()[0], "delete")
        self.revoke()
        self.assertEqual(self.reader.status("title")["release_status"], "HOLD")

    def test_missing_title_exception_releases_reader(self):
        with self.assertRaises(InvalidState):
            self.reader.status("unknown")
        with closing(self.writer.conn()) as c:
            c.execute("PRAGMA busy_timeout=0")
            self.assertEqual(c.execute("PRAGMA journal_mode=DELETE").fetchone()[0], "delete")
        self.revoke()
        self.assertFalse(self.reader.status("title")["owner_supplied_rights_ready"])

    def test_read_does_not_change_state_journal_mode_or_deterministic_bytes(self):
        for mode in ("DELETE", "WAL"):
            with self.subTest(mode=mode):
                with closing(self.writer.conn()) as c:
                    self.assertEqual(c.execute("PRAGMA journal_mode=" + mode).fetchone()[0], mode.lower())
                    before = list(c.iterdump())
                a, ra = self.reader.build_package("title")
                b, rb = ReleaseDesk(self.db).build_package("title")
                self.assertEqual((a, ra), (b, rb))
                with closing(self.writer.conn()) as c:
                    self.assertEqual(c.execute("PRAGMA journal_mode").fetchone()[0], mode.lower())
                    self.assertEqual(list(c.iterdump()), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
