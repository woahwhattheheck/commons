"""Filesystem-boundary CLI tests."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import cli
from .test_support import ready_fixture


class CliTests(unittest.TestCase):
    def test_compile_and_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "input.json"
            input_path.write_text(json.dumps(ready_fixture()), encoding="utf-8")
            output_dir = tmp_path / "out"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    cli.main(["compile", str(input_path), "--output-dir", str(output_dir)]),
                    0,
                )
                self.assertEqual(
                    cli.main(
                        [
                            "verify",
                            str(input_path),
                            str(output_dir / "receipt.json"),
                            str(output_dir / "packet.md"),
                        ]
                    ),
                    0,
                )

    def test_second_compile_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "input.json"
            input_path.write_text(json.dumps(ready_fixture()), encoding="utf-8")
            output_dir = tmp_path / "out"
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(["compile", str(input_path), "--output-dir", str(output_dir)]), 0)
                self.assertEqual(cli.main(["compile", str(input_path), "--output-dir", str(output_dir)]), 2)

    def test_require_submission_ready_returns_three(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "input.json"
            input_path.write_text(json.dumps(ready_fixture()), encoding="utf-8")
            output_dir = tmp_path / "out"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    cli.main(
                        [
                            "compile",
                            str(input_path),
                            "--output-dir",
                            str(output_dir),
                            "--require-submission-ready",
                        ]
                    ),
                    3,
                )

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "platform lacks O_NOFOLLOW")
    def test_symlink_input_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target = tmp_path / "target.json"
            target.write_text(json.dumps(ready_fixture()), encoding="utf-8")
            link = tmp_path / "link.json"
            link.symlink_to(target)
            output_dir = tmp_path / "out"
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(["compile", str(link), "--output-dir", str(output_dir)]), 2)

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "platform lacks O_NOFOLLOW")
    def test_symlink_output_directory_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "input.json"
            input_path.write_text(json.dumps(ready_fixture()), encoding="utf-8")
            real_dir = tmp_path / "real"
            real_dir.mkdir()
            link_dir = tmp_path / "out"
            link_dir.symlink_to(real_dir, target_is_directory=True)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(["compile", str(input_path), "--output-dir", str(link_dir)]), 2)

    def test_duplicate_json_key_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text('{"authority":1,"authority":2}', encoding="utf-8")
            with self.assertRaises(cli.SafeFileError):
                cli.load_json(path)

    def test_nonfinite_json_number_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nan.json"
            path.write_text('{"value":NaN}', encoding="utf-8")
            with self.assertRaises(cli.SafeFileError):
                cli.load_json(path)

    @unittest.skipUnless(os.name == "posix", "generation-race hostile requires POSIX file semantics")
    def test_same_inode_mutation_with_restored_mtime_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.bin"
            path.write_bytes(b"generation-one")
            before = os.stat(path)
            real_read = os.read
            mutated = False

            def mutating_read(fd: int, size: int) -> bytes:
                nonlocal mutated
                payload = real_read(fd, size)
                if payload and not mutated:
                    mutated = True
                    with path.open("r+b", buffering=0) as writer:
                        first = writer.read(1)
                        writer.seek(0)
                        writer.write(first)
                        os.fsync(writer.fileno())
                    # Restore mtime so a dev/ino/size/mtime-only fence would false-green.
                    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
                return payload

            with mock.patch.object(cli.os, "read", side_effect=mutating_read):
                with self.assertRaises(cli.SafeFileError):
                    cli.read_regular_file(path, max_bytes=1024)

    @unittest.skipUnless(os.name == "posix", "path-replacement hostile requires POSIX file semantics")
    def test_visible_path_replacement_during_read_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.bin"
            path.write_bytes(b"original-generation")
            replacement = Path(tmp) / "replacement.bin"
            replacement.write_bytes(b"replacement-generation")
            real_read = os.read
            replaced = False

            def replacing_read(fd: int, size: int) -> bytes:
                nonlocal replaced
                payload = real_read(fd, size)
                if payload and not replaced:
                    replaced = True
                    os.replace(replacement, path)
                return payload

            with mock.patch.object(cli.os, "read", side_effect=replacing_read):
                with self.assertRaises(cli.SafeFileError):
                    cli.read_regular_file(path, max_bytes=1024)


if __name__ == "__main__":
    unittest.main()
