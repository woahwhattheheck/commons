from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import staging_composer as sc


class PublicationDelegationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_publish_pair_delegates_exact_pair_to_shared_helper(self):
        out = self.root / "candidate.tar.gz"
        receipt = self.root / "receipt.json"
        with patch.object(sc.publication_custody, "publish_exclusive") as publish:
            sc.publish_pair(out, receipt, b"archive-payload", b"receipt-payload")
        publish.assert_called_once_with(
            ((out, b"archive-payload"), (receipt, b"receipt-payload"))
        )

    def test_success_publishes_exact_pair_through_shared_helper(self):
        out = self.root / "candidate.tar.gz"
        receipt = self.root / "receipt.json"
        sc.publish_pair(out, receipt, b"archive-payload", b"receipt-payload")
        self.assertEqual(out.read_bytes(), b"archive-payload")
        self.assertEqual(receipt.read_bytes(), b"receipt-payload")

    def test_alias_maps_shared_validation_to_composer_error_before_creation(self):
        out = self.root / "candidate.tar.gz"
        alias = self.root / "." / "candidate.tar.gz"
        with self.assertRaisesRegex(sc.ComposerError, "distinct"):
            sc.publish_pair(out, alias, b"archive", b"receipt")
        self.assertFalse(out.exists())

    def test_preexisting_receipt_rolls_back_archive_without_overwrite(self):
        out = self.root / "candidate.tar.gz"
        receipt = self.root / "receipt.json"
        receipt.write_bytes(b"foreign-sentinel")
        with self.assertRaises(FileExistsError):
            sc.publish_pair(out, receipt, b"archive", b"receipt")
        self.assertFalse(out.exists())
        self.assertEqual(receipt.read_bytes(), b"foreign-sentinel")

    def test_shared_oserror_propagates_without_translation(self):
        out = self.root / "candidate.tar.gz"
        receipt = self.root / "receipt.json"
        with patch.object(
            sc.publication_custody,
            "publish_exclusive",
            side_effect=OSError("root publication failure"),
        ):
            with self.assertRaisesRegex(OSError, "root publication failure"):
                sc.publish_pair(out, receipt, b"archive", b"receipt")


if __name__ == "__main__":
    unittest.main()
