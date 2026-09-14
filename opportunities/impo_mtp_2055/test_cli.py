"""Filesystem-boundary CLI tests."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
