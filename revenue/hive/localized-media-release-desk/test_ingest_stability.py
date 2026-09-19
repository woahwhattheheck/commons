"""Observed-change ingestion regressions, with real files and public consumers.

The hooks schedule actual writes on separate descriptors; they do not fabricate
read results. The explicit metadata-field test separately checks the comparator.
No sleeps or live services are used. A subprocess bounds the old FIFO hang.
"""
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing, contextmanager, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import desk


class IngestStabilityTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.path = self.root / "input.bin"
        self.path.write_bytes(b"abcdefgh")
        self.db = self.root / "desk.sqlite3"
        self.d = desk.ReleaseDesk(self.db)
        self.req = [{"locale": "es", "territory": "US", "kind": "subtitle"}]

    def dump(self):
        with closing(sqlite3.connect(self.db)) as c:
            return list(c.iterdump())

    def create(self):
        self.d.create_title("create", "title", self.path, self.req)

    def ready(self):
        self.create()
        self.d.set_rights_ready("rights", "title", True)
        v = self.d.add_variant("variant", "title", "es", "US", "subtitle", self.path)
        self.d.approve_variant("approve", "title", "es", "US", "subtitle",
                               "reviewer", v["revision"], v["content_sha256"])

    def append(self):
        with self.path.open("ab") as f:
            f.write(b"tail")

    def rewrite(self):
        before = self.path.stat()
        self.path.write_bytes(b"ABCDEFGH")
        os.utime(self.path, ns=(before.st_atime_ns, before.st_mtime_ns + 2_000_000_000))

    @contextmanager
    def after_stat(self, action):
        real = os.fstat
        target = self.path.stat()
        hit = []
        def observe(fd):
            st = real(fd)
            if not hit and (st.st_dev, st.st_ino) == (target.st_dev, target.st_ino):
                hit.append(fd)
                action()
            return st
        with patch.object(desk.os, "fstat", side_effect=observe):
            yield hit
        self.assertEqual(len(hit), 1, "the intended real input must be observed")

    @contextmanager
    def after_read(self, action, short=False):
        real_read, real_stat = os.read, os.fstat
        target = self.path.stat()
        hit = []
        def observe(fd, n):
            st = real_stat(fd)
            chosen = (st.st_dev, st.st_ino) == (target.st_dev, target.st_ino)
            data = real_read(fd, min(n, 3) if short and chosen else n)
            if chosen and not hit:
                hit.append(fd)
                action()
            return data
        with patch.object(desk.os, "read", side_effect=observe):
            yield hit
        self.assertEqual(len(hit), 1, "the intended real input must be read")

    def reject_unchanged(self, operation, interleaving):
        before = self.dump()
        with interleaving:
            with self.assertRaises(desk.InvalidState):
                operation()
        self.assertEqual(self.dump(), before, "failure must not consume requests or mutate state")

    def test_stable_bytes_path_and_digest(self):
        data, digest, size, name = desk.read_file(self.path)
        self.assertEqual((data, digest, size, name),
                         (b"abcdefgh", desk.sha(b"abcdefgh"), 8, "input.bin"))
        self.assertEqual(desk.read_file(os.fsencode(self.path))[3], b"input.bin")

    def test_stable_empty_input(self):
        self.path.write_bytes(b"")
        self.assertEqual(desk.read_file(self.path)[:3], (b"", desk.sha(b""), 0))

    def test_partial_reads_are_reassembled(self):
        real = os.read
        with patch.object(desk.os, "read", side_effect=lambda fd, n: real(fd, min(n, 2))):
            self.assertEqual(desk.read_file(self.path)[0], b"abcdefgh")

    def test_size_cap_boundary_and_one_over(self):
        with patch.object(desk, "MAX", 8):
            self.assertEqual(desk.read_file(self.path)[2], 8)
            self.append()
            with patch.object(desk.os, "read") as read:
                with self.assertRaises(desk.InvalidState):
                    desk.read_file(self.path)
                read.assert_not_called()

    def test_growth_after_initial_stat_rejected(self):
        with self.after_stat(self.append):
            with self.assertRaises(desk.InvalidState):
                desk.read_file(self.path)

    def test_initially_empty_growth_rejected(self):
        self.path.write_bytes(b"")
        with self.after_stat(self.append):
            with self.assertRaises(desk.InvalidState):
                desk.read_file(self.path)

    def test_append_after_last_body_read_rejected(self):
        with self.after_read(self.append):
            with self.assertRaises(desk.InvalidState):
                desk.read_file(self.path)

    def test_same_size_rewrite_between_chunks_rejected(self):
        with self.after_read(self.rewrite, short=True):
            with self.assertRaises(desk.InvalidState):
                desk.read_file(self.path)

    def test_rewrite_after_all_body_bytes_rejected(self):
        with self.after_read(self.rewrite):
            with self.assertRaises(desk.InvalidState):
                desk.read_file(self.path)

    def test_truncation_before_read_rejected(self):
        with self.after_stat(lambda: self.path.write_bytes(b"abc")):
            with self.assertRaises(desk.InvalidState):
                desk.read_file(self.path)

    def test_truncation_after_body_read_rejected(self):
        with self.after_read(lambda: self.path.write_bytes(b"abc")):
            with self.assertRaises(desk.InvalidState):
                desk.read_file(self.path)

    def test_each_metadata_field_is_compared(self):
        real = os.fstat
        fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
        for field in fields:
            with self.subTest(field=field):
                calls = []
                def altered(fd):
                    st = real(fd)
                    calls.append(fd)
                    values = {name: getattr(st, name) for name in fields}
                    if len(calls) == 2:
                        values[field] += 1
                    return SimpleNamespace(**values)
                with patch.object(desk.os, "fstat", side_effect=altered):
                    with self.assertRaises(desk.InvalidState):
                        desk.read_file(self.path)
                self.assertEqual(len(calls), 2)

    def test_atime_change_does_not_reject_stable_content(self):
        real = os.fstat
        calls = []
        def atime_only(fd):
            st = real(fd)
            calls.append(fd)
            attrs = {name: getattr(st, name) for name in dir(st) if name.startswith("st_")}
            attrs["st_atime_ns"] += len(calls) * 2_000_000_000
            return SimpleNamespace(**attrs)
        with patch.object(desk.os, "fstat", side_effect=atime_only):
            self.assertEqual(desk.read_file(self.path)[0], b"abcdefgh")

    def test_changed_input_fd_is_closed(self):
        with self.after_stat(self.append) as fds:
            with self.assertRaises(desk.InvalidState):
                desk.read_file(self.path)
        with self.assertRaises(OSError):
            os.fstat(fds[0])

    def test_read_error_closes_fd(self):
        real_open = os.open
        fds = []
        def track(*a, **kw):
            fd = real_open(*a, **kw)
            fds.append(fd)
            return fd
        with patch.object(desk.os, "open", side_effect=track), \
             patch.object(desk.os, "read", side_effect=OSError("injected read failure")):
            with self.assertRaises(OSError):
                desk.read_file(self.path)
        self.assertEqual(len(fds), 1)
        with self.assertRaises(OSError):
            os.fstat(fds[0])

    def test_unsupported_nonblocking_refused_before_open(self):
        with patch.object(desk.os, "O_NONBLOCK", 0, create=True), \
             patch.object(desk.os, "open") as opened:
            with self.assertRaises(desk.InvalidState):
                desk.read_file(self.path)
            opened.assert_not_called()

    def test_directory_rejected(self):
        with self.assertRaises(desk.InvalidState):
            desk.read_file(self.root)

    @unittest.skipUnless(getattr(os, "O_NOFOLLOW", 0), "no-follow unsupported")
    def test_symlink_leaf_remains_rejected(self):
        link = self.root / "link"
        link.symlink_to(self.path)
        with self.assertRaises(OSError):
            desk.read_file(link)
        self.assertEqual(self.path.read_bytes(), b"abcdefgh")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO unsupported")
    def test_fifo_without_writer_does_not_hang(self):
        fifo = self.root / "pipe"
        os.mkfifo(fifo)
        script = """import desk, sys
try:
    desk.read_file(sys.argv[1])
except desk.InvalidState as exc:
    print(str(exc))
    raise SystemExit(0)
raise SystemExit(9)
"""
        opts = ["-O"] if sys.flags.optimize else []
        try:
            result = subprocess.run([sys.executable, *opts, "-B", "-c", script, str(fifo)],
                                    cwd=Path(desk.__file__).parent, capture_output=True,
                                    text=True, timeout=3)
        except subprocess.TimeoutExpired:
            self.fail("FIFO ingestion waited for a writer; child was killed and reaped")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("not a regular file", result.stdout)

    def test_create_growth_preserves_all_tables_and_retry_key(self):
        self.reject_unchanged(self.create, self.after_stat(self.append))
        self.create()
        self.assertEqual(self.d.status("title")["source"]["size"], 12)

    def test_update_growth_preserves_ready_state_and_retry_key(self):
        self.ready()
        self.reject_unchanged(lambda: self.d.update_source("update", "title", self.path),
                              self.after_stat(self.append))
        self.assertEqual(self.d.status("title")["release_status"], "READY_FOR_LOCAL_HANDOFF")
        self.assertTrue(self.d.update_source("update", "title", self.path)["changed"])
        self.assertIn("STALE_SOURCE_BINDING:es/US/subtitle", self.d.status("title")["holds"])

    def test_variant_rewrite_preserves_approval_and_retry_key(self):
        self.ready()
        op = lambda: self.d.add_variant("revise", "title", "es", "US", "subtitle", self.path)
        self.reject_unchanged(op, self.after_read(self.rewrite, short=True))
        self.assertEqual(self.d.status("title")["release_status"], "READY_FOR_LOCAL_HANDOFF")
        self.assertEqual(op()["revision"], 2)
        self.assertIn("MISSING_CURRENT_APPROVAL:es/US/subtitle", self.d.status("title")["holds"])

    def test_verify_cannot_ignore_new_tail(self):
        self.ready()
        self.path = self.root / "release.zip"
        self.d.export_package("title", self.path)
        self.reject_unchanged(lambda: self.d.verify_package("title", self.path),
                              self.after_stat(self.append))
        self.assertFalse(self.d.verify_package("title", self.path)["valid"])

    def test_cli_required_growth_cannot_create_title(self):
        self.path.write_text(json.dumps(self.req))
        source = self.root / "source"
        source.write_bytes(b"master")
        before = self.dump()
        out = io.StringIO()
        with self.after_stat(lambda: self.path.open("ab").close()):
            # A stable requirements read remains a successful control.
            with redirect_stdout(out):
                code = desk.main(["--db", str(self.db), "create-title", "--request-id", "ok",
                                  "--title-id", "ok", "--source", str(source),
                                  "--required", str(self.path)])
        self.assertEqual(code, 0)
        self.assertNotEqual(self.dump(), before)
        before = self.dump()
        out = io.StringIO()
        with self.after_stat(self.append), redirect_stdout(out):
            code = desk.main(["--db", str(self.db), "create-title", "--request-id", "bad",
                              "--title-id", "bad", "--source", str(source),
                              "--required", str(self.path)])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue())["error"], "INVALID")
        self.assertEqual(self.dump(), before)

    def test_stable_public_operations_replay_after_reopen(self):
        self.ready()
        before = self.dump()
        reopened = desk.ReleaseDesk(self.db)
        reopened.create_title("create", "title", self.path, self.req)
        reopened.add_variant("variant", "title", "es", "US", "subtitle", self.path)
        self.assertEqual(self.dump(), before)
        data, receipt = reopened.build_package("title")
        self.path = self.root / "release.zip"
        self.path.write_bytes(data)
        self.assertTrue(reopened.verify_package("title", self.path)["valid"])
        self.assertEqual(receipt["package_sha256"], desk.sha(data))


if __name__ == "__main__":
    unittest.main(verbosity=2)
