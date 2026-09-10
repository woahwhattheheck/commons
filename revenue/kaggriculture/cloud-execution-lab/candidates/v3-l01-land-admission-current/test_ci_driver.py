# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from ci_support import extract_verified, git_blob_id


class CiDriverTests(unittest.TestCase):
    def test_git_blob_identity(self):
        payload = b"hello\n"
        expected = hashlib.sha1(b"blob 6\0hello\n").hexdigest()  # noqa: S324
        self.assertEqual(git_blob_id(payload), expected)

    def test_extract_rejects_links(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            archive = root / "bad.tar.gz"
            with tarfile.open(archive, "w:gz") as handle:
                member = tarfile.TarInfo("escape")
                member.type = tarfile.SYMTYPE
                member.linkname = "../outside"
                handle.addfile(member, io.BytesIO())
            with self.assertRaises(ValueError):
                extract_verified(archive, root / "out")


if __name__ == "__main__":
    unittest.main()
