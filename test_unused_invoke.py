#!/usr/bin/env python3
"""Unused-invoke leftover is a measurement, not invented usage."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from unused_invoke import (
    classify,
    classify_provider,
    measure_from_rows,
    measure_root,
    references,
    stems_from_listing,
)


class TestUnusedInvoke(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_unused_is_the_finding(self):
        measured = measure_from_rows(
            ["alpha", "beta"],
            [
                ("host/alpha.py", "def main():\n    return 1\n"),
                ("land.html", "python3 host/alpha.py\n"),
                ("host/beta.py", "def main():\n    return 0\n"),
                ("test_beta.py", "import beta\n"),
            ],
        )
        self.assertEqual(measured["unused"], ["beta"])
        self.assertEqual(measured["invoked_count"], 1)
        self.assertEqual(measured["titan"], "NOT_WRITTEN")
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("1 unused", verdict["note"])

    def test_stems_skip_dunders(self):
        self.assertEqual(
            stems_from_listing(["named_builder.py", "__init__.py", "readme.txt"]),
            ["named_builder"],
        )

    def test_references_need_an_invoke_shape(self):
        self.assertTrue(references("named_builder", "python3 host/named_builder.py"))
        self.assertTrue(references("named_builder", "from named_builder import classify"))
        self.assertFalse(references("named_builder", "named builder talk only"))

    def test_provider_config_without_run_stays_unmeasured(self):
        dark = classify_provider(
            {
                "road": "Cirrus",
                "config_present": True,
                "run_url": "",
                "probe_status": "TLS_000",
            }
        )
        self.assertEqual(dark["state"], "UNMEASURED")
        self.assertIn("Do not invent", dark["note"])
        missing = classify_provider({"road": "Oracle", "config_present": False})
        self.assertEqual(missing["state"], "NOT_LANDED")
        gha = classify_provider({"road": "GitHub Actions", "config_present": True})
        self.assertEqual(gha["state"], "LIVE")

    def test_live_host_tree_has_unused_and_invoked(self):
        measured = measure_root(ROOT)
        self.assertTrue(measured["measured"])
        self.assertGreaterEqual(measured["instrument_count"], 1)
        self.assertGreaterEqual(measured["invoked_count"], 1)
        self.assertGreaterEqual(measured["unused_count"], 1)
        self.assertEqual(classify(measured)["state"], "INTEGRATED")
        roads = {row["road"]: row for row in measured["providers"]}
        self.assertTrue(roads["Cirrus"]["config_present"])
        self.assertEqual(roads["Cirrus"]["state"], "UNMEASURED")
        self.assertEqual(roads["GitHub Actions"]["state"], "LIVE")


if __name__ == "__main__":
    unittest.main()
