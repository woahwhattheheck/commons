from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from revenue.pursuit_portfolio import host, host_io
from revenue.pursuit_portfolio.core import PortfolioError
from test_pursuit_portfolio import NOW
from test_pursuit_portfolio_host_custody_v2 import floor_file, key_file, one


@unittest.skipUnless(os.name == "posix", "retained dir_fd custody requires POSIX")
class HostPackageIoV2Tests(unittest.TestCase):
    def _compiled(self, root: Path):
        data, authority = one()
        key_path = key_file(root)
        floor_path = floor_file(root, authority)
        with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
            host, "HOST_FLOOR_PATH", floor_path
        ), mock.patch.object(host, "_now", return_value=NOW):
            value = host.compile_current(data, authority)
        return value, key_path, floor_path

    def test_final_package_recheck_catches_early_child_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            value, _, _ = self._compiled(root)
            out = root / "out"
            out.mkdir(mode=0o700)
            real_write = host_io._write_owned_relative
            calls = {"count": 0}

            def hostile_write(dir_fd, name, payload):
                calls["count"] += 1
                if calls["count"] == 2:
                    os.unlink("portfolio.json", dir_fd=dir_fd)
                    fd = os.open(
                        "portfolio.json",
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                        0o600,
                        dir_fd=dir_fd,
                    )
                    try:
                        os.write(fd, b"FOREIGN")
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                return real_write(dir_fd, name, payload)

            with mock.patch.object(host_io, "_write_owned_relative", side_effect=hostile_write):
                with self.assertRaisesRegex(PortfolioError, "changed after publication"):
                    host_io.publish_current(value, out)
            self.assertEqual((out / "portfolio.json").read_bytes(), b"FOREIGN")
            self.assertTrue((out / "portfolio.md").exists())

    def test_output_directory_path_replacement_cannot_report_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            value, _, _ = self._compiled(root)
            out = root / "out"
            out.mkdir(mode=0o700)
            old = root / "old-out"
            real_write = host_io._write_owned_relative
            calls = {"count": 0}

            def hostile_write(dir_fd, name, payload):
                generation = real_write(dir_fd, name, payload)
                calls["count"] += 1
                if calls["count"] == 4:
                    out.rename(old)
                    out.mkdir(mode=0o700)
                return generation

            with mock.patch.object(host_io, "_write_owned_relative", side_effect=hostile_write):
                with self.assertRaisesRegex(PortfolioError, "no longer names retained generation"):
                    host_io.publish_current(value, out)
            self.assertTrue((old / "portfolio.json").exists())
            self.assertEqual(list(out.iterdir()), [])

    def test_double_scan_rejects_cross_file_package_movement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            value, _, _ = self._compiled(root)
            out = root / "out"
            out.mkdir(mode=0o700)
            host_io.publish_current(value, out)
            real_scan = host_io._scan
            calls = {"count": 0}

            def hostile_scan(dir_fd):
                parts = real_scan(dir_fd)
                calls["count"] += 1
                if calls["count"] == 1:
                    os.unlink("portfolio.json", dir_fd=dir_fd)
                    fd = os.open(
                        "portfolio.json",
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                        0o600,
                        dir_fd=dir_fd,
                    )
                    try:
                        os.write(fd, b"FOREIGN")
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                return parts

            with mock.patch.object(host_io, "_scan", side_effect=hostile_scan):
                with self.assertRaisesRegex(PortfolioError, "package generation changed"):
                    host_io.read_current_directory(out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
