from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from coordination.connector_preflight import core, publication
from coordination.connector_preflight.core import PreflightError


class PublicationCustodyTests(unittest.TestCase):
    def test_core_writer_name_is_rebound_to_custody_writer(self):
        self.assertIs(core.write_json_exclusive, publication.write_json_exclusive)

    def test_exact_visible_generation_is_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.json"
            publication.write_json_exclusive(path, {"ok": True})
            self.assertEqual('{\n  "ok": true\n}\n', path.read_text(encoding="utf-8"))

    def test_post_open_replacement_refuses_success_and_preserves_foreign(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.json"
            displaced = Path(tmp) / "displaced.json"
            foreign = b"foreign-successor\n"
            real_fsync = os.fsync

            def replace_after_fsync(fd: int) -> None:
                real_fsync(fd)
                os.replace(path, displaced)
                path.write_bytes(foreign)

            with patch.object(publication.os, "fsync", side_effect=replace_after_fsync):
                with self.assertRaisesRegex(PreflightError, "published output"):
                    publication.write_json_exclusive(path, {"ok": True})

            self.assertEqual(foreign, path.read_bytes())
            self.assertTrue(displaced.exists())

    def test_post_open_replacement_then_write_failure_preserves_foreign(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.json"
            displaced = Path(tmp) / "displaced.json"
            foreign = b"foreign-successor\n"
            replaced = False

            def fail_after_replacement(fd: int, data: bytes | memoryview) -> int:
                nonlocal replaced
                if not replaced:
                    replaced = True
                    os.replace(path, displaced)
                    path.write_bytes(foreign)
                raise OSError("synthetic write failure")

            with patch.object(publication.os, "write", side_effect=fail_after_replacement):
                with self.assertRaisesRegex(PreflightError, "cannot publish output safely"):
                    publication.write_json_exclusive(path, {"ok": True})

            self.assertEqual(foreign, path.read_bytes())
            self.assertTrue(displaced.exists())

    def test_exception_path_never_unlinks_public_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.json"
            real_unlink = publication.os.unlink
            unlink_calls: list[str] = []

            def record_unlink(target, *args, **kwargs):
                unlink_calls.append(os.fspath(target))
                return real_unlink(target, *args, **kwargs)

            with patch.object(publication.os, "fsync", side_effect=OSError("synthetic fsync failure")):
                with patch.object(publication.os, "unlink", side_effect=record_unlink):
                    with self.assertRaisesRegex(PreflightError, "cannot publish output safely"):
                        publication.write_json_exclusive(path, {"ok": True})

            self.assertEqual([], unlink_calls)
            self.assertTrue(path.exists())

    def test_second_close_replacement_is_caught_by_final_namespace_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.json"
            displaced = Path(tmp) / "displaced.json"
            foreign = b"foreign-successor\n"
            real_close = os.close
            close_calls = 0

            def replace_on_second_close(fd: int) -> None:
                nonlocal close_calls
                close_calls += 1
                real_close(fd)
                if close_calls == 2:
                    os.replace(path, displaced)
                    path.write_bytes(foreign)

            with patch.object(publication.os, "close", side_effect=replace_on_second_close):
                with self.assertRaisesRegex(PreflightError, "published output path changed after readback"):
                    publication.write_json_exclusive(path, {"ok": True})

            self.assertEqual(2, close_calls)
            self.assertEqual(foreign, path.read_bytes())
            self.assertTrue(displaced.exists())


if __name__ == "__main__":
    unittest.main()
