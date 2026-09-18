#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))
import open_work as ow  # noqa: E402

WORK_ID = "bm-hive-20260908-047"
RECEIPT = os.path.join("p", WORK_ID + ".md")
MERGE_SHA = "5501f4bd89b0a77dabcd0dda0e97195b86d929a6"


class BmHiveLandingReceiptContract(unittest.TestCase):
    def test_canonical_receipt_closes_open_projection(self):
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip().lower()
        row = ow.classify_id(
            WORK_ID,
            ROOT,
            record={"work": True},
            main_sha=head,
        )
        self.assertEqual(row["class"], "LANDED")
        self.assertEqual(row["receipt"], RECEIPT)
        self.assertEqual(row["last_sha"], head)

    def test_receipt_binds_existing_provider_landing(self):
        path = os.path.join(ROOT, RECEIPT)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("WORK ORDER: " + WORK_ID, text)
        self.assertIn("woahwhattheheck/commons#10455", text)
        self.assertIn(MERGE_SHA, text)
        self.assertIn("p/astra-hive-multilingual-catalog-publisher-20260908-01.md", text)
        self.assertIn("does not remint", text)


if __name__ == "__main__":
    unittest.main()
