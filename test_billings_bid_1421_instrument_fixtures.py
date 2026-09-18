#!/usr/bin/env python3
"""Binary test for Bid 1421 Attachment F mock-adapter fixtures."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
PACK = ROOT / "revenue" / "billings_bid_1421" / "instrument_fixtures"
FINDER_UNVERIFIED = "FINDER UNVERIFIED"


def _load_runner():
    path = PACK / "runner.py"
    spec = importlib.util.spec_from_file_location("billings_bid_1421_instrument_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BillingsBid1421InstrumentFixturesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = _load_runner()
        cls.manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        cls.expected = json.loads((PACK / "expected_receipts.json").read_text(encoding="utf-8"))
        cls.result = cls.runner.run_pack(str(PACK))
        cls.summary = cls.runner.summarize(cls.result, cls.expected)

    def test_pack_files_exist(self):
        for name in (
            "manifest.json",
            "events.jsonl",
            "expected_receipts.json",
            "runner.py",
            "source.json",
            "README.md",
        ):
            self.assertTrue((PACK / name).is_file(), name)

    def test_thirty_events_match_expected_receipts(self):
        self.assertEqual(self.result["event_count"], 30)
        self.assertEqual(len(self.result["receipts"]), 30)
        self.assertEqual(len(self.expected["receipts"]), 30)
        self.assertTrue(self.summary["ok"], self.summary["failures"])

    def test_duplicate_and_timeout_do_not_create_second_commit(self):
        created = {}
        for rec in self.result["receipts"]:
            created.setdefault(rec["delivery_id"], 0)
            created[rec["delivery_id"]] += rec["commits_created"]
        self.assertEqual([did for did, n in created.items() if n > 1], [])
        dup = [r for r in self.result["receipts"] if r["scenario"] == "duplicate_delivery"]
        timeout = [r for r in self.result["receipts"] if r["scenario"] == "timeout_after_commit"]
        self.assertEqual(len(dup), 6)
        self.assertEqual(len(timeout), 2)
        for rec in dup:
            self.assertEqual(rec["status"], "DUPLICATE_SUPPRESSED")
            self.assertEqual(rec["commits_created"], 0)
            self.assertEqual(rec["total_commits_for_delivery"], 1)
            self.assertIsNotNone(rec["commit_id"])
        for rec in timeout:
            self.assertEqual(rec["status"], "TIMEOUT_AFTER_COMMIT")
            self.assertEqual(rec["commits_created"], 0)
            self.assertEqual(rec["total_commits_for_delivery"], 1)
            self.assertIsNotNone(rec["commit_id"])

    def test_out_of_order_is_held_not_silently_applied(self):
        held = [r for r in self.result["receipts"] if r["scenario"] == "out_of_order"]
        self.assertEqual(len(held), 5)
        for rec in held:
            self.assertEqual(rec["status"], "HELD_OUT_OF_ORDER")
            self.assertTrue(rec["held"])
            self.assertIsNone(rec["commit_id"])
            self.assertEqual(rec["commits_created"], 0)

    def test_bad_qc_fails_closed(self):
        bad = [r for r in self.result["receipts"] if r["scenario"] == "bad_qc"]
        self.assertEqual(len(bad), 5)
        for rec in bad:
            self.assertEqual(rec["status"], "FAIL_CLOSED")
            self.assertIsNone(rec["commit_id"])
            self.assertEqual(rec["commits_created"], 0)
            self.assertFalse(rec["held"])

    def test_finder_unverified_never_reported_as_zero(self):
        adapters = self.runner.adapter_index(self.manifest)
        cal = self.runner.find_adapter(adapters, "mock-ph-meter-1")
        self.assertEqual(cal["status"], "HIT")
        miss = self.runner.find_adapter(adapters, "no-such-adapter")
        self.assertEqual(miss["status"], FINDER_UNVERIFIED)
        self.assertNotEqual(miss.get("count"), 0)
        self.assertFalse(miss.get("zero"))
        self.assertIn("search_space", miss)
        self.assertEqual(
            miss["search_space"]["path"],
            "revenue/billings_bid_1421/instrument_fixtures/manifest.json",
        )
        analytes = self.runner.analyte_index(self.manifest)
        analyte_miss = self.runner.find_analyte(analytes, "no-such-analyte")
        self.assertEqual(analyte_miss["status"], FINDER_UNVERIFIED)
        self.assertNotEqual(analyte_miss.get("count"), 0)
        probe = self.result["finder_probe"]
        self.assertEqual(probe["status"], FINDER_UNVERIFIED)
        dumped = json.dumps(probe)
        self.assertNotIn('"count": 0', dumped)
        self.assertNotRegex(dumped, r"\b0/N\b")

    def test_manifest_is_attachment_f_mock_only(self):
        self.assertEqual(self.manifest["id"], "billings-bid-1421-instrument-fixtures-20260831-01")
        self.assertEqual(self.manifest["cash_usd"], 0)
        self.assertEqual(self.manifest["kind"], "mock_adapter_manifest")
        self.assertEqual(self.manifest["status"], "SYNTHETIC_MOCK_ONLY")
        names = {row["rfp_name"] for row in self.manifest["instrumentation_for_integration"]}
        self.assertEqual(
            names,
            {
                "pH Meters",
                "Analytical Balances",
                "PerkinElmer Furnace AA",
                "Metrohm Ion Chromatograph",
                "Sievers TOC Analyzer",
                "Seal Discrete Analyzer",
            },
        )
        self.assertEqual(len(self.manifest["analysis_list"]), 37)
        self.assertIn("aquatrace-lims-proof/", self.manifest["cite_do_not_remint"])
        self.assertFalse((ROOT / "aquatrace-lims-proof").exists())

    def test_cli_binary_pass(self):
        import subprocess

        proc = subprocess.run(
            ["python3", str(PACK / "runner.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        self.assertIn("PASS", proc.stdout)
        self.assertNotIn("FAIL", proc.stdout.splitlines()[-1] if proc.stdout else "")


if __name__ == "__main__":
    unittest.main()
