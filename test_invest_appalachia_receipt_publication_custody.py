from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from opportunities.invest_appalachia_framer_lms import attachment_recovery as recovery


_CHILD_ENV = "INVEST_APPALACHIA_PUBLICATION_CUSTODY_OPT_CHILD"
_IS_OPT_CHILD = os.environ.get(_CHILD_ENV) == "1"


class ReceiptPublicationCustodyTests(unittest.TestCase):
    def test_successful_publish_is_exact_and_private(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "receipt.json"
            rendered = '{"ok":true}\n'
            recovery._write_receipt_exclusive(str(target), rendered)
            self.assertEqual(target.read_text(encoding="utf-8"), rendered)
            if os.name == "posix":
                self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(Path(tmp).glob(".receipt.json.*.tmp")), [])

    def test_prepublication_failure_preserves_foreign_final_successor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "receipt.json"

            def fail_fsync_after_foreign_appears(_fd: int) -> None:
                target.write_text("FOREIGN\n", encoding="utf-8")
                raise OSError("synthetic fsync failure after foreign successor appeared")

            with mock.patch.object(recovery.os, "fsync", side_effect=fail_fsync_after_foreign_appears):
                with self.assertRaisesRegex(recovery.AttachmentRecoveryError, "cannot write receipt staging file"):
                    recovery._write_receipt_exclusive(str(target), '{"ours":true}\n')

            self.assertEqual(target.read_text(encoding="utf-8"), "FOREIGN\n")
            self.assertEqual(list(root.glob(".receipt.json.*.tmp")), [])

    def test_postlink_replacement_fails_closed_without_deleting_foreign_successor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "receipt.json"
            real_stat = recovery.os.stat
            swapped = False

            def stat_with_swap(path, *args, **kwargs):
                nonlocal swapped
                candidate = os.path.abspath(os.fspath(path))
                if candidate == os.path.abspath(str(target)) and not swapped:
                    swapped = True
                    target.unlink()
                    target.write_text("FOREIGN-AFTER-LINK\n", encoding="utf-8")
                return real_stat(path, *args, **kwargs)

            with mock.patch.object(recovery.os, "stat", side_effect=stat_with_swap):
                with self.assertRaisesRegex(recovery.AttachmentRecoveryError, "publication identity changed"):
                    recovery._write_receipt_exclusive(str(target), '{"ours":true}\n')

            self.assertTrue(swapped)
            self.assertEqual(target.read_text(encoding="utf-8"), "FOREIGN-AFTER-LINK\n")
            self.assertEqual(list(root.glob(".receipt.json.*.tmp")), [])

    def test_existing_final_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "receipt.json"
            target.write_text("SENTINEL\n", encoding="utf-8")
            with self.assertRaisesRegex(recovery.AttachmentRecoveryError, "cannot publish receipt output exclusively"):
                recovery._write_receipt_exclusive(str(target), '{"ours":true}\n')
            self.assertEqual(target.read_text(encoding="utf-8"), "SENTINEL\n")
            self.assertEqual(list(root.glob(".receipt.json.*.tmp")), [])


@unittest.skipIf(_IS_OPT_CHILD, "parent-only optimized replay harness")
class ReceiptPublicationCustodyOptimizedBridgeTests(unittest.TestCase):
    def test_same_hostiles_pass_under_python_optimized(self) -> None:
        env = os.environ.copy()
        env[_CHILD_ENV] = "1"
        root = Path(__file__).resolve().parent
        completed = subprocess.run(
            [sys.executable, "-O", str(Path(__file__).resolve())],
            cwd=root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("Ran 5 tests", completed.stdout)
        self.assertRegex(completed.stdout, r"(?m)^OK \(skipped=1\)$")


if __name__ == "__main__":
    unittest.main()
