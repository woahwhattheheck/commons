#!/usr/bin/env python3
"""Connector-reval leftover measures; it does not write forbidden roads."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from connector_reval import (
    CLAIMED_CONNECTED,
    catalog_from_row,
    classify,
    classify_service,
    load_catalog,
    measure_from_rows,
    measure_root,
    mcp_state,
    vscdb_plan,
)


class TestConnectorReval(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_secrets_are_not_landed(self):
        row = classify({"measured": True, "secrets": True, "provisioned_ne_live": True})
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("secrets", row["note"])

    def test_live_vacuum_is_not_landed(self):
        row = classify(
            {
                "measured": True,
                "provisioned_ne_live": True,
                "vscdb": {
                    "refuse_live_repair": False,
                    "actuate": True,
                    "plan": ["backup", "clean_shutdown", "checkpoint", "integrity"],
                },
            }
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("vacuum", row["note"])

    def test_census_marks_provisioned_not_live(self):
        measured = measure_from_rows(
            {
                "claimed_connected": list(CLAIMED_CONNECTED),
                "claimed_unverified": ["gitlab", "box"],
                "live": ["github", "slack", "gitbook", "cursor-cloud"],
                "enabled_claim": 39,
                "connected_claim": 23,
                "cache_age_days_claim": 4,
                "mcp_exists": False,
            }
        )
        self.assertTrue(measured["provisioned_ne_live"])
        self.assertTrue(measured["mcp"]["empty"])
        self.assertIn("github", measured["live"])
        self.assertIn("stripe", measured["forbidden"])
        self.assertIn("gmail", measured["forbidden"])
        self.assertIn("gitlab", measured["unverified"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")
        self.assertFalse(measured["secrets"])
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("Provisioned != live", verdict["note"])

    def test_forbidden_classes_skip_writes(self):
        stripe = classify_service({"name": "stripe", "klass": "financial"})
        self.assertEqual(stripe["state"], "FORBIDDEN")
        mail = classify_service({"name": "gmail", "probe_ok": True, "klass": "messaging"})
        self.assertEqual(mail["state"], "FORBIDDEN")
        github = classify_service({"name": "github", "probe_ok": True})
        self.assertEqual(github["state"], "LIVE")

    def test_mcp_absent_is_empty(self):
        row = mcp_state(False, 0, 0)
        self.assertTrue(row["empty"])
        self.assertFalse(row["exists"])

    def test_vscdb_plan_refuses_live_repair(self):
        row = vscdb_plan(False)
        self.assertTrue(row["refuse_live_repair"])
        self.assertFalse(row["actuate"])
        self.assertEqual(row["plan"], ["backup", "clean_shutdown", "checkpoint", "integrity"])

    def test_catalog_has_no_secrets(self):
        catalog_path = os.path.join(ROOT, "ground", "CONNECTOR_REVAL.json")
        with open(catalog_path, encoding="utf-8") as handle:
            text = handle.read()
        catalog = load_catalog(text)
        self.assertEqual(catalog["slack_ts"], "1787637151.916759")
        self.assertIn("github", catalog["claimed_connected"])
        self.assertIn("gitlab", catalog["claimed_unverified"])
        self.assertFalse(json_has_secret_key(text))
        receipt = catalog_from_row(
            {
                "live": ["github"],
                "forbidden": ["stripe"],
                "provisioned_ne_live": True,
                "mcp": {"empty": True},
                "vscdb": {"present": False},
            }
        )
        self.assertFalse(receipt["secrets"])
        self.assertTrue(receipt["vscdb"]["refuse_live_repair"])
        self.assertEqual(receipt["titan"], "NOT_WRITTEN")

    def test_live_tree_measures(self):
        measured = measure_root(ROOT)
        self.assertTrue(measured["measured"])
        self.assertTrue(measured["provisioned_ne_live"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")
        self.assertFalse(measured["secrets"])
        self.assertEqual(classify(measured)["state"], "INTEGRATED")


def json_has_secret_key(text):
    lowered = str(text or "").lower()
    needles = ("api_key", "password=", "authorization: ", "@gmail.com", "sk-")
    return any(needle in lowered for needle in needles)


if __name__ == "__main__":
    unittest.main()
