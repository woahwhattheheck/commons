#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))
import open_work as ow  # noqa: E402

WORK_ID = "bm-hive-20260908-047"
RECEIPT = os.path.join("p", WORK_ID + ".md")
MERGE_SHA = "5501f4bd89b0a77dabcd0dda0e97195b86d929a6"
STALE_SHA = "f47a69a20a0e193c350a5234f84b0ee7baee48a3"
MACHINE_REL = os.path.join("ground", "open-work-structured-ids-on-current-main.json")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


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


class ProjectorFreshnessContract(unittest.TestCase):
    def test_projector_sha_is_current_main_ish_and_bm_hive_landed(self):
        path = os.path.join(ROOT, MACHINE_REL)
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        sha = str(data.get("main_sha") or "").strip().lower()
        self.assertRegex(sha, SHA_RE.pattern)
        self.assertNotEqual(sha, STALE_SHA)
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip().lower()
        subprocess.check_call(
            ["git", "merge-base", "--is-ancestor", sha, head],
            cwd=ROOT,
        )
        by_id = {item["id"]: item for item in data.get("items") or []}
        row = by_id.get(WORK_ID)
        self.assertIsNotNone(row)
        self.assertEqual(row["class"], "LANDED")
        self.assertEqual(row["receipt"], RECEIPT.replace(os.sep, "/"))
        subprocess.check_call(
            ["git", "cat-file", "-e", "%s:%s" % (sha, RECEIPT.replace(os.sep, "/"))],
            cwd=ROOT,
        )
        change = by_id.get("change-order")
        unclaimed = by_id.get("unclaimed")
        if change is not None and not os.path.isfile(os.path.join(ROOT, "p", "change-order.md")):
            self.assertEqual(change["class"], "OPEN")
            self.assertEqual(change["receipt"], "404")
        if unclaimed is not None and not os.path.isfile(os.path.join(ROOT, "p", "unclaimed.md")):
            self.assertEqual(unclaimed["class"], "OPEN")
            self.assertEqual(unclaimed["receipt"], "404")


if __name__ == "__main__":
    unittest.main()
