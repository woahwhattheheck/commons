from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from revenue.pursuit_portfolio import cli
from revenue.pursuit_portfolio.core import PortfolioError
from revenue.pursuit_portfolio.current import _compile_authorized_at
import revenue.pursuit_portfolio.publisher as publisher
from test_pursuit_portfolio_current import KEY, NOW, authority_for, source


@unittest.skipUnless(
    os.name == "posix",
    "retained publication byte custody requires POSIX directory descriptors",
)
class PublicationByteCustodyTests(unittest.TestCase):
    def test_same_inode_same_length_mutation_during_directory_fsync_fails_closed(self):
        value = source(max_age=86400 * 5)
        authorized = _compile_authorized_at(value, authority_for(value), KEY, NOW)

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            out.mkdir(mode=0o700)
            real_fsync = publisher.os.fsync
            observed: dict[str, int | bool] = {"mutated": False}

            def adversarial_fsync(fd: int) -> None:
                info = os.fstat(fd)
                if not observed["mutated"] and stat.S_ISDIR(info.st_mode):
                    leaf_fd = os.open(
                        "portfolio.json",
                        os.O_RDWR | os.O_NOFOLLOW,
                        dir_fd=fd,
                    )
                    try:
                        before = os.fstat(leaf_fd)
                        observed["inode"] = int(before.st_ino)
                        replacement = b"X" * int(before.st_size)
                        os.lseek(leaf_fd, 0, os.SEEK_SET)
                        view = memoryview(replacement)
                        while view:
                            written = os.write(leaf_fd, view)
                            if written <= 0:
                                raise AssertionError("short hostile write")
                            view = view[written:]
                        real_fsync(leaf_fd)
                    finally:
                        os.close(leaf_fd)
                    observed["mutated"] = True
                real_fsync(fd)

            with mock.patch.object(
                publisher.os,
                "fsync",
                side_effect=adversarial_fsync,
            ):
                with self.assertRaisesRegex(
                    PortfolioError,
                    "output content changed: portfolio.json",
                ):
                    publisher.publish_authorized(authorized, out)

            self.assertTrue(observed["mutated"])
            after = os.stat(out / "portfolio.json", follow_symlinks=False)
            self.assertEqual(int(after.st_ino), observed["inode"])
            self.assertEqual(after.st_size, len(authorized.compiled.result_bytes))
            self.assertEqual(
                (out / "portfolio.json").read_bytes(),
                b"X" * len(authorized.compiled.result_bytes),
            )
            # Failure preserves the hostile generation as evidence; publication
            # never pathname-deletes a re-resolved output name.
            self.assertTrue((out / "portfolio.md").exists())


class CompileReceiptOutputTests(unittest.TestCase):
    def test_compile_reports_hashes_of_exact_persisted_receipt_bytes(self):
        current_receipt_bytes = b'{"current":"receipt"}\n'
        host_seal_bytes = b'{"host":"seal"}\n'
        authorized = SimpleNamespace(
            current_receipt={
                "authority_sha256": "a" * 64,
                "receipt_sha256": "b" * 64,
            },
            current_receipt_bytes=current_receipt_bytes,
            compiled=SimpleNamespace(
                result={
                    "selected_opportunity_ids": ["alpha"],
                    "selected_priority_units": 11,
                }
            ),
        )
        value = SimpleNamespace(
            authorized=authorized,
            host_seal={"hmac_sha256": "c" * 64},
            host_seal_bytes=host_seal_bytes,
        )
        output = io.StringIO()

        with (
            mock.patch.object(cli, "load_current_input", return_value={}),
            mock.patch.object(cli, "read_regular_bytes", return_value=b"{}\n"),
            mock.patch.object(cli, "load_json_bytes", return_value={}),
            mock.patch.object(cli, "compile_current", return_value=value),
            mock.patch.object(cli, "publish_current"),
            redirect_stdout(output),
        ):
            self.assertEqual(
                cli.main(["compile", "input.json", "authority.json", "out"]),
                0,
            )

        observed = json.loads(output.getvalue())
        self.assertEqual(
            observed["current_receipt_sha256"],
            hashlib.sha256(current_receipt_bytes).hexdigest(),
        )
        self.assertEqual(
            observed["host_seal_sha256"],
            hashlib.sha256(host_seal_bytes).hexdigest(),
        )
        self.assertNotEqual(
            observed["current_receipt_sha256"],
            authorized.current_receipt["receipt_sha256"],
        )
        self.assertNotEqual(
            observed["host_seal_sha256"],
            value.host_seal["hmac_sha256"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
