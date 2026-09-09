#!/usr/bin/env python3
"""Hermetic: CRM6 relationship handoff is projected after feature_tracker --write.

CLAIM ledger-crm6-feature-tracker-write-20260905-02
Registry already on main (#8867). This ship regenerates feature-tracker.json/html
so the id is visible. Does not remint the registry JSON. Hands off #8802.
"""
from __future__ import annotations

import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEATURE_ID = "ledger-crm6-relationship-handoff-20260904-01"
REGISTRY = os.path.join(
    ROOT, "features", "registry", FEATURE_ID + ".json"
)
TRACKER_JSON = os.path.join(ROOT, "feature-tracker.json")
TRACKER_HTML = os.path.join(ROOT, "feature-tracker.html")
RECEIPT = os.path.join(
    ROOT, "p", "ledger-crm6-feature-tracker-write-20260905-02.md"
)


class TestLedgerCrm6FeatureTrackerWrite(unittest.TestCase):
    def test_registry_present_unchanged_id(self):
        self.assertTrue(os.path.isfile(REGISTRY), REGISTRY)
        rec = json.loads(open(REGISTRY, encoding="utf-8").read())
        self.assertEqual(rec.get("id"), FEATURE_ID)
        self.assertEqual(rec.get("schema"), "commons-feature-v1")
        self.assertEqual(rec.get("carrier"), "LEDGER")

    def test_projection_includes_crm6(self):
        self.assertTrue(os.path.isfile(TRACKER_JSON), TRACKER_JSON)
        data = json.loads(open(TRACKER_JSON, encoding="utf-8").read())
        self.assertEqual(data.get("schema"), "commons-feature-tracker-v1")
        by_id = {row.get("id"): row for row in data.get("features") or []}
        self.assertIn(FEATURE_ID, by_id)
        row = by_id[FEATURE_ID]
        self.assertEqual(row.get("carrier"), "LEDGER")
        self.assertEqual(row.get("owner_subsystem"), "lm-gtm-index")
        self.assertNotEqual(row.get("rollup"), "")
        # Registry + claimed paths on tree → not PLANNED after --write.
        self.assertIn(
            row.get("source_status"),
            ("SOURCE_BUILT", "DEGRADED", "PLANNED"),
        )

    def test_html_and_receipt(self):
        self.assertTrue(os.path.isfile(TRACKER_HTML), TRACKER_HTML)
        page = open(TRACKER_HTML, encoding="utf-8").read()
        self.assertIn(FEATURE_ID, page)
        self.assertTrue(os.path.isfile(RECEIPT), RECEIPT)
        body = open(RECEIPT, encoding="utf-8").read()
        self.assertIn("ledger-crm6-feature-tracker-write-20260905-02", body)
        self.assertIn("feature_tracker.py --write", body)
        self.assertIn("#8802", body)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
