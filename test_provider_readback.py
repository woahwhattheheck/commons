#!/usr/bin/env python3
"""Offline contract for measured provider readback receipts."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent
RECEIPT_PATH = Path("ci/provider_readbacks/jsdelivr-0cc5ccba5815.json")


class ProviderReadbackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads((ROOT / RECEIPT_PATH).read_text(encoding="utf-8"))
        cls.mirrors = json.loads((ROOT / "mirrors.json").read_text(encoding="utf-8"))
        cls.provider_map = (ROOT / "ground/COMMONS_PROVIDER_MAP.md").read_text(encoding="utf-8")

    def test_receipt_is_exact_and_truthfully_bounded(self):
        receipt = self.receipt
        source = receipt["source"]
        readback = receipt["readback"]
        boundary = receipt["claim_boundary"]
        self.assertEqual(receipt["schema_version"], 1)
        self.assertEqual(receipt["provider"], "jsdelivr")
        self.assertRegex(source["commit"], r"^[0-9a-f]{40}$")
        self.assertRegex(source["git_blob"], r"^[0-9a-f]{40}$")
        self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(source["commit"], readback["headers"]["x-jsd-version"])
        self.assertEqual(readback["headers"]["x-jsd-version-type"], "commit")
        self.assertEqual(source["sha256"], readback["sha256"])
        self.assertEqual(source["bytes"], readback["bytes"])
        self.assertEqual(readback["http_status"], 200)
        self.assertTrue(all(receipt["verification"].values()))
        self.assertTrue(boundary["measured_cross_provider_read"])
        for unproved in ("moving_main_sync", "provider_writeback", "independent_origin", "canonical_durability"):
            self.assertFalse(boundary[unproved], unproved)

    def test_catalog_points_to_the_same_receipt(self):
        entry = next(row for row in self.mirrors["read"] if row["id"] == "jsdelivr-sha-pinned")
        source = self.receipt["source"]
        readback = self.receipt["readback"]
        self.assertEqual(entry["href"], readback["url"])
        self.assertEqual(entry["source_commit"], source["commit"])
        self.assertEqual(entry["artifact_path"], source["path"])
        self.assertEqual(entry["sha256"], source["sha256"])
        self.assertEqual(entry["receipt"], "./" + RECEIPT_PATH.as_posix())
        self.assertIn(RECEIPT_PATH.name, self.provider_map)
        self.assertIn(source["sha256"], self.provider_map)
        self.assertIn("no moving-main sync, writeback, independent origin, or canonical durability", self.provider_map)

    def test_source_snapshot_matches_when_git_object_is_available(self):
        source = self.receipt["source"]
        spec = f'{source["commit"]}:{source["path"]}'
        probe = subprocess.run(
            ["git", "cat-file", "-e", spec], cwd=ROOT, capture_output=True, check=False
        )
        if probe.returncode != 0:
            self.skipTest("pinned source commit is outside this checkout")
        data = subprocess.check_output(["git", "show", spec], cwd=ROOT)
        blob = subprocess.check_output(["git", "rev-parse", spec], cwd=ROOT, text=True).strip()
        self.assertEqual(len(data), source["bytes"])
        self.assertEqual(sha256(data).hexdigest(), source["sha256"])
        self.assertEqual(blob, source["git_blob"])


if __name__ == "__main__":
    unittest.main()
