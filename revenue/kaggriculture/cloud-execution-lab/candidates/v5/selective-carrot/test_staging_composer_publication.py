from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import staging_composer as sc


class PublicationCustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_success_publishes_exact_pair(self):
        out = self.root / "candidate.tar.gz"
        receipt = self.root / "receipt.json"
        sc.publish_pair(out, receipt, b"archive-payload", b"receipt-payload")
        self.assertEqual(out.read_bytes(), b"archive-payload")
        self.assertEqual(receipt.read_bytes(), b"receipt-payload")

    def test_foreign_replacement_fails_and_preserves_foreign_path(self):
        out = self.root / "candidate.tar.gz"
        receipt = self.root / "receipt.json"
        original = sc._write_all
        calls = 0

        def replace_after_second_write(fd, raw):
            nonlocal calls
            calls += 1
            original(fd, raw)
            if calls == 2:
                out.unlink()
                out.write_bytes(b"foreign-sentinel")

        with patch.object(sc, "_write_all", side_effect=replace_after_second_write):
            with self.assertRaisesRegex(sc.ComposerError, "ownership changed"):
                sc.publish_pair(out, receipt, b"archive", b"receipt")
        self.assertEqual(out.read_bytes(), b"foreign-sentinel")
        self.assertFalse(receipt.exists())

    def test_same_inode_payload_mutation_fails_and_rolls_back_owned_pair(self):
        out = self.root / "candidate.tar.gz"
        receipt = self.root / "receipt.json"
        original = sc._write_all
        calls = 0

        def mutate_after_second_write(fd, raw):
            nonlocal calls
            calls += 1
            original(fd, raw)
            if calls == 2:
                with out.open("r+b") as stream:
                    stream.seek(0)
                    stream.write(b"X")
                    stream.flush()

        with patch.object(sc, "_write_all", side_effect=mutate_after_second_write):
            with self.assertRaisesRegex(sc.ComposerError, "payload changed"):
                sc.publish_pair(out, receipt, b"archive", b"receipt")
        self.assertFalse(out.exists())
        self.assertFalse(receipt.exists())


if __name__ == "__main__":
    unittest.main()
