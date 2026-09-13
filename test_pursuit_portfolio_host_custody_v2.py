from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from revenue.pursuit_portfolio import host
from revenue.pursuit_portfolio.core import PortfolioError
import revenue.pursuit_portfolio.core_v2 as core
from test_pursuit_portfolio import NOW, authority_rows, opp, source

KEY_ID = "owner-root-v2"
KEY_BYTES = b"k" * 32


def canonical(value):
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def key_file(root: Path) -> Path:
    path = root / "authority-key.json"
    path.write_bytes(
        canonical(
            {
                "schema": host.KEY_SCHEMA,
                "key_id": KEY_ID,
                "key_hex": KEY_BYTES.hex(),
            }
        )
    )
    path.chmod(0o600)
    return path


def floor_file(root: Path, authority: dict) -> Path:
    normalized = core.normalize_upstream_authority(authority)
    unsigned = {
        "authority_sha256": core.upstream_authority_sha256(normalized),
        "key_id": KEY_ID,
        "revision": normalized["revision"],
        "schema": host.FLOOR_SCHEMA,
        "updated_at": NOW,
    }
    value = {
        **unsigned,
        "hmac_sha256": hmac.new(
            KEY_BYTES, canonical(unsigned), hashlib.sha256
        ).hexdigest(),
    }
    path = root / "authority-floor.json"
    path.write_bytes(canonical(value))
    path.chmod(0o600)
    return path


def one():
    row = opp("A", 10, {"proposal": 1})
    data = source([row])
    authority = authority_rows(
        data["opportunities"], captured="2026-09-13T13:00:00Z"
    )
    return data, authority


@unittest.skipUnless(os.name == "posix", "retained dir_fd custody requires POSIX")
class HostCustodyV2Tests(unittest.TestCase):
    def test_group_readable_host_floor_is_rejected(self):
        data, authority = one()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path = key_file(root)
            floor_path = floor_file(root, authority)
            floor_path.chmod(0o640)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value=NOW):
                with self.assertRaisesRegex(PortfolioError, "owner-only permissions"):
                    host.compile_current(data, authority)

    def test_host_floor_symlink_is_rejected(self):
        data, authority = one()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path = key_file(root)
            real_floor = floor_file(root, authority)
            link = root / "floor-link.json"
            link.symlink_to(real_floor)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", link
            ), mock.patch.object(host, "_now", return_value=NOW):
                with self.assertRaises(Exception):
                    host.compile_current(data, authority)

    def test_output_ancestor_symlink_is_rejected(self):
        data, authority = one()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path = key_file(root)
            floor_path = floor_file(root, authority)
            real_parent = root / "real-parent"
            real_parent.mkdir(mode=0o700)
            out = real_parent / "out"
            out.mkdir(mode=0o700)
            alias = root / "alias-parent"
            alias.symlink_to(real_parent, target_is_directory=True)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(host, "_now", return_value=NOW):
                value = host.compile_current(data, authority)
                with self.assertRaises(Exception):
                    host.publish_current(value, alias / "out")
            self.assertEqual(list(out.iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
