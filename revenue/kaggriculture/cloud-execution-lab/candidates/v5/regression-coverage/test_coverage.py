import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

import coverage as target


class CoverageHelpersTest(unittest.TestCase):
    def _tar(self, members, *, symlink=None):
        tmp = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
        tmp.close()
        path = Path(tmp.name)
        with tarfile.open(path, "w:gz") as tf:
            for name, raw in members:
                info = tarfile.TarInfo(name)
                info.size = len(raw)
                tf.addfile(info, io.BytesIO(raw))
            if symlink is not None:
                info = tarfile.TarInfo(symlink)
                info.type = tarfile.SYMTYPE
                info.linkname = "target"
                tf.addfile(info)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def test_normalize_rejects_escape_absolute_and_backslash(self):
        for value in ("../x", "/x", "a/../../b", "a\\b", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                target.normalize_member_path(value)
        self.assertEqual(target.normalize_member_path("./a/b"), "a/b")

    def test_archive_inventory_rejects_duplicate(self):
        path = self._tar([("./a", b"one"), ("a", b"two")])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            target.archive_inventory(path)

    def test_archive_inventory_rejects_symlink(self):
        path = self._tar([("a", b"one")], symlink="link")
        with self.assertRaisesRegex(ValueError, "non-regular"):
            target.archive_inventory(path)

    def test_pair_summary(self):
        left = {"members": {"a": {"sha256":"1","size":1}, "b":{"sha256":"2","size":1}}}
        right = {"members": {"a": {"sha256":"1","size":1}, "b":{"sha256":"3","size":1}, "c":{"sha256":"4","size":1}}}
        self.assertEqual(target.pair_summary(left, right), {
            "common_count":2,"identical_common_count":1,"changed_common_count":1,
            "v31_only_count":0,"v4_only_count":1,"changed_common_paths":["b"],"v4_only_paths":["c"]})

    def test_config_delta(self):
        got = target.config_delta(json.dumps({"same":1,"old":2}).encode(), json.dumps({"same":1,"new":3}).encode())
        self.assertEqual(got["common_equal_count"], 1)
        self.assertEqual(got["changed_common"], {})
        self.assertEqual(got["v31_only"], {"old":2})
        self.assertEqual(got["v4_only"], {"new":3})

    def test_changed_symbols(self):
        left = b"x=1\ndef f():\n return 1\nclass C:\n def m(self):\n  return 1\n"
        right = b"x=2\ndef f():\n return 2\nclass C:\n def m(self):\n  return 1\n"
        self.assertEqual(target.changed_symbols(left, right), ["f", "__module__"])

    def test_manifest_digest_is_canonical(self):
        a = {"b":1,"a":2}
        b = {"a":2,"b":1}
        self.assertEqual(target.sha256_bytes(target.canonical_json(a)), target.sha256_bytes(target.canonical_json(b)))


if __name__ == "__main__":
    unittest.main()
