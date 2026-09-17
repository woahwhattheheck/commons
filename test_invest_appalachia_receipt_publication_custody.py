from __future__ import annotations

import errno
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from opportunities.invest_appalachia_framer_lms import attachment_recovery as recovery


_CHILD_ENV = "INVEST_APPALACHIA_PUBLICATION_CUSTODY_OPT_CHILD"
_IS_OPT_CHILD = os.environ.get(_CHILD_ENV) == "1"


class ReceiptPublicationCustodyTests(unittest.TestCase):
    def test_successful_publish_is_exact_private_and_consumes_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "receipt.json"
            rendered = '{"ok":true}\n'
            recovery._write_receipt_exclusive(str(target), rendered)
            self.assertEqual(target.read_text(encoding="utf-8"), rendered)
            if os.name == "posix":
                self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(root.glob(".receipt.json.*.tmp")), [])

    def test_durability_call_order_is_file_fsync_publish_directory_fsync(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "receipt.json"
            events: list[str] = []
            real_fsync = recovery.os.fsync
            real_rename = recovery._rename_noreplace

            def traced_fsync(fd: int) -> None:
                mode = recovery.os.fstat(fd).st_mode
                events.append("directory-fsync" if stat.S_ISDIR(mode) else "file-fsync")
                real_fsync(fd)

            def traced_rename(src_name: str, dst_name: str, *, dir_fd: int) -> None:
                events.append("publish")
                real_rename(src_name, dst_name, dir_fd=dir_fd)

            with mock.patch.object(recovery.os, "fsync", side_effect=traced_fsync), mock.patch.object(
                recovery, "_rename_noreplace", side_effect=traced_rename
            ):
                recovery._write_receipt_exclusive(str(target), '{"ours":true}\n')

            self.assertEqual(events, ["file-fsync", "publish", "directory-fsync"])

    def test_prepublication_failure_preserves_foreign_final_and_retains_private_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "receipt.json"

            def fail_file_fsync_after_foreign_appears(fd: int) -> None:
                if not stat.S_ISDIR(recovery.os.fstat(fd).st_mode):
                    target.write_text("FOREIGN\n", encoding="utf-8")
                    raise OSError("synthetic file fsync failure after foreign successor appeared")
                os.fsync(fd)

            with mock.patch.object(recovery.os, "fsync", side_effect=fail_file_fsync_after_foreign_appears):
                with self.assertRaisesRegex(recovery.AttachmentRecoveryError, "cannot write receipt staging file"):
                    recovery._write_receipt_exclusive(str(target), '{"ours":true}\n')

            self.assertEqual(target.read_text(encoding="utf-8"), "FOREIGN\n")
            staging = list(root.glob(".receipt.json.*.tmp"))
            self.assertEqual(len(staging), 1)
            self.assertEqual(staging[0].read_text(encoding="utf-8"), '{"ours":true}\n')
            if os.name == "posix":
                self.assertEqual(staging[0].stat().st_mode & 0o777, 0o600)

    def test_staging_replacement_after_last_owned_observation_survives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "receipt.json"
            real_rename = recovery._rename_noreplace
            swapped = False

            def swap_then_rename(src_name: str, dst_name: str, *, dir_fd: int) -> None:
                nonlocal swapped
                swapped = True
                recovery.os.unlink(src_name, dir_fd=dir_fd)
                foreign_fd = recovery.os.open(
                    src_name,
                    recovery.os.O_WRONLY | recovery.os.O_CREAT | recovery.os.O_EXCL,
                    0o600,
                    dir_fd=dir_fd,
                )
                try:
                    recovery.os.write(foreign_fd, b"FOREIGN-STAGING\n")
                    recovery.os.fsync(foreign_fd)
                finally:
                    recovery.os.close(foreign_fd)
                real_rename(src_name, dst_name, dir_fd=dir_fd)

            with mock.patch.object(recovery, "_rename_noreplace", side_effect=swap_then_rename):
                with self.assertRaisesRegex(recovery.AttachmentRecoveryError, "publication identity changed"):
                    recovery._write_receipt_exclusive(str(target), '{"ours":true}\n')

            self.assertTrue(swapped)
            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "FOREIGN-STAGING\n")
            self.assertEqual(list(root.glob(".receipt.json.*.tmp")), [])

    def test_directory_fsync_failure_fails_closed_without_deleting_foreign_final(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "receipt.json"
            real_fsync = recovery.os.fsync
            replaced = False

            def fail_directory_fsync(fd: int) -> None:
                nonlocal replaced
                if stat.S_ISDIR(recovery.os.fstat(fd).st_mode):
                    target.unlink()
                    target.write_text("FOREIGN-AFTER-PUBLISH\n", encoding="utf-8")
                    replaced = True
                    raise OSError("synthetic parent directory fsync failure")
                real_fsync(fd)

            with mock.patch.object(recovery.os, "fsync", side_effect=fail_directory_fsync):
                with self.assertRaisesRegex(recovery.AttachmentRecoveryError, "cannot durably commit"):
                    recovery._write_receipt_exclusive(str(target), '{"ours":true}\n')

            self.assertTrue(replaced)
            self.assertEqual(target.read_text(encoding="utf-8"), "FOREIGN-AFTER-PUBLISH\n")
            self.assertEqual(list(root.glob(".receipt.json.*.tmp")), [])

    def test_existing_final_is_never_overwritten_and_failed_stage_is_retained(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "receipt.json"
            target.write_text("SENTINEL\n", encoding="utf-8")
            with self.assertRaisesRegex(recovery.AttachmentRecoveryError, "cannot publish receipt output exclusively"):
                recovery._write_receipt_exclusive(str(target), '{"ours":true}\n')
            self.assertEqual(target.read_text(encoding="utf-8"), "SENTINEL\n")
            staging = list(root.glob(".receipt.json.*.tmp"))
            self.assertEqual(len(staging), 1)
            self.assertEqual(staging[0].read_text(encoding="utf-8"), '{"ours":true}\n')

    def test_unsupported_atomic_publish_fails_closed_and_retains_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "receipt.json"
            with mock.patch.object(
                recovery,
                "_rename_noreplace",
                side_effect=OSError(errno.ENOTSUP, "synthetic unsupported renameat2"),
            ):
                with self.assertRaisesRegex(recovery.AttachmentRecoveryError, "cannot publish receipt output exclusively"):
                    recovery._write_receipt_exclusive(str(target), '{"ours":true}\n')
            self.assertFalse(target.exists())
            staging = list(root.glob(".receipt.json.*.tmp"))
            self.assertEqual(len(staging), 1)
            self.assertEqual(staging[0].read_text(encoding="utf-8"), '{"ours":true}\n')


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
        self.assertIn("Ran 8 tests", completed.stdout)
        self.assertRegex(completed.stdout, r"(?m)^OK \(skipped=1\)$")


if __name__ == "__main__":
    unittest.main()
