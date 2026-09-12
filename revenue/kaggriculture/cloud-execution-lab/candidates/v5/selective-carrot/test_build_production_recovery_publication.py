import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_production_recovery as bpr


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.out = self.root / "candidate"
        self.tar = self.root / "candidate.tar.gz"
        self.manifest = self.root / "candidate-manifest.json"
        self.files = {"main.py": b"payload\n", "nested/x.py": b"x\n"}
        self.packed = b"archive-bytes"
        self.receipt = {
            "schema": "test",
            "candidate_archive_sha256": hashlib.sha256(self.packed).hexdigest(),
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_success_publishes_pair_and_tree(self):
        bpr._publish(self.files, self.packed, self.receipt, self.out, self.tar, self.manifest)
        self.assertEqual(self.tar.read_bytes(), self.packed)
        self.assertTrue(self.manifest.read_text().endswith("\n"))
        self.assertEqual((self.out / "main.py").read_bytes(), b"payload\n")
        self.assertEqual((self.out / "nested/x.py").read_bytes(), b"x\n")

    def test_manifest_collision_rolls_back_owned_archive(self):
        self.manifest.write_bytes(b"foreign")
        with self.assertRaises(FileExistsError):
            bpr._publish(self.files, self.packed, self.receipt, self.out, self.tar, self.manifest)
        self.assertFalse(self.tar.exists())
        self.assertEqual(self.manifest.read_bytes(), b"foreign")
        self.assertFalse(self.out.exists())

    def test_second_write_failure_rolls_back_both_finals_and_tree(self):
        real = bpr._write_reserved
        calls = {"n": 0}

        def fail_second(fd, payload):
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError("injected manifest write failure")
            return real(fd, payload)

        with patch.object(bpr, "_write_reserved", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "injected"):
                bpr._publish(self.files, self.packed, self.receipt, self.out, self.tar, self.manifest)
        self.assertFalse(self.tar.exists())
        self.assertFalse(self.manifest.exists())
        self.assertFalse(self.out.exists())

    def test_publication_paths_reject_aliases_and_finals_inside_tree(self):
        with self.assertRaisesRegex(ValueError, "distinct"):
            bpr._validate_publication_paths(self.out, self.out, self.manifest)
        with self.assertRaisesRegex(ValueError, "inside"):
            bpr._validate_publication_paths(self.out, self.out / "x.tar.gz", self.manifest)
        with self.assertRaisesRegex(ValueError, "inside"):
            bpr._validate_publication_paths(self.out, self.tar, self.out / "manifest.json")


if __name__ == "__main__":
    unittest.main()
