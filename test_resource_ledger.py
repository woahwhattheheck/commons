#!/usr/bin/env python3
"""Resource ledger leftover measures; it does not count cache as capacity."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from resource_ledger import (
    REQUIRED_FIELDS,
    catalog_from_row,
    classify,
    classify_surface,
    load_catalog,
    local_probes,
    measure_from_rows,
    measure_root,
)


LIVE_FIELDS = {
    "evidence_ts": "2026-08-25T06:10:00Z",
    "auth_surface": "GitHub MCP",
    "exact_safe_probe": "get_me",
    "rate_plan_boundary": "one app",
    "assigned_backlog": "current-main writes",
    "last_receipt": "rivet-ship-resource-ledger-20260825-01",
}


class TestResourceLedger(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_secrets_are_not_landed(self):
        row = classify({"measured": True, "secrets": True, "live": ["github"]})
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("secrets", row["note"])

    def test_cache_as_capacity_is_not_landed(self):
        row = classify({"measured": True, "cache_as_capacity": True, "live": ["github"]})
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("cache was counted as capacity", row["note"])

    def test_huggingface_cache_is_not_live(self):
        row = classify_surface(
            {"name": "huggingface", "capacity": "LIVE", "cache_counted": True},
            {},
        )
        self.assertEqual(row["capacity"], "NOT_VERIFIED")
        self.assertIn("NOT verified", row["note"])

    def test_vercel_production_write_is_forbidden(self):
        row = classify_surface(
            {"name": "vercel", "capacity": "LIVE", "production_write": True},
            {},
        )
        self.assertEqual(row["capacity"], "FORBIDDEN")
        self.assertIn("production write", row["note"])

    def test_census_separates_live_from_cache(self):
        github = dict(LIVE_FIELDS)
        github["name"] = "github"
        github["capacity"] = "LIVE"
        measured = measure_from_rows(
            {
                "surfaces": [
                    github,
                    {"name": "huggingface", "capacity": "LIVE", "cache_counted": True},
                    {"name": "zapier", "capacity": "CACHE", "cache_counted": True},
                ],
                "probes": {"hf_token_files": [], "hf_cli": False},
            }
        )
        self.assertIn("github", measured["live"])
        self.assertIn("huggingface", measured["not_verified"])
        self.assertIn("zapier", measured["cache"])
        self.assertFalse(measured["cache_as_capacity"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")
        self.assertFalse(measured["secrets"])
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("Cache is not capacity", verdict["note"])

    def test_live_rows_need_ledger_fields(self):
        measured = measure_from_rows(
            {"surfaces": [{"name": "github", "capacity": "LIVE"}]}
        )
        self.assertTrue(measured["missing_fields"])
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_catalog_has_required_fields_and_no_secrets(self):
        catalog_path = os.path.join(ROOT, "ground", "RESOURCE_LEDGER.json")
        with open(catalog_path, encoding="utf-8") as handle:
            text = handle.read()
        catalog = load_catalog(text)
        self.assertEqual(catalog["slack_ts"], "1787637936.134649")
        self.assertFalse(catalog["cache_as_capacity"])
        self.assertFalse(catalog["secrets"])
        names = [row["name"] for row in catalog["surfaces"]]
        self.assertIn("github", names)
        self.assertIn("huggingface", names)
        self.assertIn("vercel", names)
        for row in catalog["surfaces"]:
            if row["capacity"] == "LIVE":
                for field in REQUIRED_FIELDS:
                    self.assertTrue(row[field], field)
        self.assertFalse(json_has_secret_key(text))
        receipt = catalog_from_row({"live": ["github"], "not_verified": ["huggingface"]})
        self.assertFalse(receipt["secrets"])
        self.assertFalse(receipt["cache_as_capacity"])
        self.assertEqual(receipt["titan"], "NOT_WRITTEN")

    def test_local_probes_see_absent_hf(self):
        probes = local_probes(os.path.join(ROOT, "does-not-exist-home"))
        self.assertEqual(probes["hf_token_files"], [])
        self.assertFalse(probes["hf_cli"])

    def test_live_tree_measures(self):
        measured = measure_root(ROOT)
        self.assertTrue(measured["measured"])
        self.assertIn("github", measured["live"])
        self.assertIn("huggingface", measured["not_verified"])
        self.assertNotIn("huggingface", measured["live"])
        self.assertFalse(measured["cache_as_capacity"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")
        self.assertFalse(measured["secrets"])
        self.assertEqual(classify(measured)["state"], "INTEGRATED")


def json_has_secret_key(text):
    lowered = str(text or "").lower()
    needles = ("api_key", "password=", "authorization: ", "@gmail.com", "sk-")
    return any(needle in lowered for needle in needles)


if __name__ == "__main__":
    unittest.main()
