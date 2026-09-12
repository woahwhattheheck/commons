#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import sys
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import check_historical_ledger as historical


class HistoricalGeminiLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = historical.current.find_repo_root(HERE)
        cls.path = HERE / "GEMINI-HISTORICAL.json"
        cls.doc = historical.current.load_strict_json(cls.path)

    def test_combined_lock_is_exactly_twenty_nine(self):
        result = historical.validate_bundle(HERE, self.repo_root)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["recent_entry_count"], 21)
        self.assertEqual(result["historical_entry_count"], 8)
        self.assertEqual(result["combined_entry_count"], 29)

    def test_historical_ids_are_exact(self):
        result = historical.validate_historical_document(self.doc, self.repo_root)
        self.assertEqual(set(result["ids"]), historical.REQUIRED_IDS)
        self.assertEqual(result["entry_count"], 8)

    def test_missing_old_gemini_lineage_fails_closed(self):
        bad = copy.deepcopy(self.doc)
        bad["entries"] = bad["entries"][1:]
        bad["entry_count"] = len(bad["entries"])
        with self.assertRaises(historical.current.ConvergenceError):
            historical.validate_historical_document(bad, self.repo_root)

    def test_extra_lineage_fails_closed(self):
        bad = copy.deepcopy(self.doc)
        extra = copy.deepcopy(bad["entries"][0])
        extra["id"] = "gemini.unclaimed-parallel-controller"
        bad["entries"].append(extra)
        bad["entries"].sort(key=lambda item: item["id"])
        bad["entry_count"] = len(bad["entries"])
        with self.assertRaises(historical.current.ConvergenceError):
            historical.validate_historical_document(bad, self.repo_root)

    def test_e11_cannot_drop_public_certificate(self):
        bad = copy.deepcopy(self.doc)
        e11 = next(e for e in bad["entries"] if e["id"] == "gemini.legacy-g01-e11")
        e11["canonical_evidence"] = [
            p for p in e11["canonical_evidence"] if p != historical.CERTIFICATE_PATH
        ]
        with self.assertRaises(historical.current.ConvergenceError):
            historical.validate_historical_document(bad, self.repo_root)

    def test_g01_shop_cannot_regress_to_static_weight(self):
        bad = copy.deepcopy(self.doc)
        shop = next(e for e in bad["entries"] if e["id"] == "gemini.legacy-g01-shop")
        shop["canonical_evidence"] = [
            p for p in shop["canonical_evidence"] if p != historical.DEMAND_VELOCITY_PATH
        ]
        with self.assertRaises(historical.current.ConvergenceError):
            historical.validate_historical_document(bad, self.repo_root)

    def test_s33_cannot_promote_pre_pressure_rank_novelty(self):
        bad = copy.deepcopy(self.doc)
        s33 = next(e for e in bad["entries"] if e["id"] == "gemini.s33-stratum")
        s33["disposition"] = "CORRECTED_DESCENDANT"
        s33["activation"] = "RESEARCH_ONLY"
        with self.assertRaises(historical.current.ConvergenceError):
            historical.validate_historical_document(bad, self.repo_root)

    def test_evidence_must_be_current_v4_regular_file(self):
        bad = copy.deepcopy(self.doc)
        flash = next(e for e in bad["entries"] if e["id"] == "gemini.flash-market-goop")
        flash["canonical_evidence"] = ["revenue/kaggriculture/cloud-execution-lab/candidates/v3/legacy.py"]
        with self.assertRaises(historical.current.ConvergenceError):
            historical.validate_historical_document(bad, self.repo_root)


if __name__ == "__main__":
    unittest.main()
