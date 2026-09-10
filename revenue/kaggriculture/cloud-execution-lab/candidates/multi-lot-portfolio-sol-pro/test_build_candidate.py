# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import io
import json
import tarfile
import unittest

import build_candidate


class BuildContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload, cls.receipt = build_candidate.render()

    def test_render_is_deterministic(self):
        payload, receipt = build_candidate.render()
        self.assertEqual(payload, self.payload)
        self.assertEqual(receipt, self.receipt)

    def test_archive_verifies_and_declares_nonmutation(self):
        build_candidate.verify_archive(self.payload, self.receipt)
        self.assertFalse(self.receipt["canonical_release_mutated"])

    def test_manifest_binds_overlay_and_scheduler(self):
        with tarfile.open(fileobj=io.BytesIO(self.payload), mode="r:gz") as archive:
            manifest = json.load(archive.extractfile("SOURCE.json"))
        self.assertIn("multi_lot_portfolio.py", manifest["runtime"])
        self.assertIn("+multi-lot-patch-v1", manifest["runtime"]["scheduler.py"]["source_path"])


if __name__ == "__main__":
    unittest.main()
