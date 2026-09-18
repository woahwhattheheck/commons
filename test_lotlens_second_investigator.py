#!/usr/bin/env python3
"""LotLens second-investigator acceptance — TENON's two unplanned questions, frozen for CI.

CLEAT Order-2 ask: any seat with a shell can ask a different question and post whether
the evidence path was enough. TENON ran these from the branch bytes (2026-09-04 23:49 ET).
This file freezes those measured answers so the battery keeps the cross-harness bar.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("lotlens_engine", ROOT / "lotlens" / "engine.py")
engine = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = engine
SPEC.loader.exec_module(engine)

FIXTURE = ROOT / "lotlens" / "fixtures" / "synthetic_pilot"

# TENON Q1 — backward from the coverage-gap package (8 known contributors).
BACKWARD_FROM_PKG_P4_1 = {
    "pilot-plant/batch/BATCH-P4",
    "pilot-plant/batch/BATCH-P2",
    "pilot-plant/batch/BATCH-P1",
    "sup-acme/lot/LOT-SUGAR-02",
    "sup-aqua/lot/LOT-WATER-01",
    "sup-h2o/lot/LOT-WATER-01",
    "sup-acme/lot/LOT-CITRIC-01A",
    "sup-acme/lot/LOT-CITRIC-01",
}

# TENON Q2 — forward from the Aqua water lot (11 known; not the H2O lot's BATCH-P1).
FORWARD_FROM_AQUA_WATER = {
    "pilot-plant/batch/BATCH-P2",
    "pilot-plant/batch/BATCH-P4",
    "pilot-plant/batch/BATCH-P5",
    "pilot-plant/package/PKG-P2-1",
    "pilot-plant/package/PKG-P2-2",
    "pilot-plant/package/PKG-P4-1",
    "pilot-plant/package/PKG-P5-1",
    "pilot-plant/shipment/SHIP-2",
    "pilot-plant/shipment/SHIP-3",
    "pilot-plant/shipment/SHIP-5",
    "pilot-plant/shipment/SHIP-9",
}


class SecondInvestigatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.ws = engine.Workspace(Path(cls.tmp.name) / "ws")
        cls.info = cls.ws.import_dir(FIXTURE, label="pilot")
        cls.graph = cls.ws.graph()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_tenon_q1_backward_from_coverage_gap_package(self):
        impact = self.graph.impact(("pilot-plant", "package", "PKG-P4-1"), "backward")
        known = {a["key"] for a in impact["affected"] if a["status"] == engine.STATUS_KNOWN}
        self.assertEqual(known, BACKWARD_FROM_PKG_P4_1)
        self.assertEqual(len(known), 8)
        by_key = {a["key"]: a for a in impact["affected"]}
        self.assertEqual(by_key["pilot-plant/batch/BATCH-P4"]["hops"], 1)
        self.assertEqual(by_key["pilot-plant/batch/BATCH-P2"]["hops"], 2)
        self.assertEqual(by_key["pilot-plant/batch/BATCH-P1"]["hops"], 3)
        self.assertEqual(by_key["sup-acme/lot/LOT-SUGAR-02"]["hops"], 2)
        self.assertEqual(by_key["sup-aqua/lot/LOT-WATER-01"]["hops"], 3)
        self.assertEqual(by_key["sup-h2o/lot/LOT-WATER-01"]["hops"], 4)
        self.assertEqual(by_key["sup-acme/lot/LOT-CITRIC-01A"]["hops"], 4)
        self.assertEqual(by_key["sup-acme/lot/LOT-CITRIC-01"]["hops"], 5)
        # Vanilla is unresolved on BATCH-P4, scoped to this package's upstream.
        self.assertTrue(
            any(
                f["code"] == "consumed_input_not_in_records"
                and f["detail"].get("input_ref") == "sup-acme/lot/LOT-VANILLA-09"
                for f in impact["unresolved"]
            )
        )
        # Coverage gap: package has no shipment — "records stop here", not unaffected.
        self.assertTrue(
            any(
                f["code"] == "package_without_shipment" and "pilot-plant/package/PKG-P4-1" in f["nodes"]
                for f in impact["coverage_gaps"]
            )
        )
        # BATCH-P3 over-consumption is not on this path.
        self.assertEqual(impact["contradictions"], [])
        for a in impact["affected"]:
            for e in a["path"]:
                self.assertTrue(e["sources"], "every hop cites a row")

    def test_tenon_q2_forward_from_aqua_water_lot(self):
        impact = self.graph.impact(("sup-aqua", "lot", "LOT-WATER-01"), "forward")
        known = {a["key"] for a in impact["affected"] if a["status"] == engine.STATUS_KNOWN}
        self.assertEqual(known, FORWARD_FROM_AQUA_WATER)
        self.assertEqual(len(known), 11)
        self.assertNotIn("pilot-plant/batch/BATCH-P1", known)
        self.assertNotIn("sup-h2o/lot/LOT-WATER-01", known)
        # SHIP-9 double-link sits on this path.
        self.assertTrue(any(f["code"] == "multiple_shipped_links" for f in impact["contradictions"]))
        water = self.graph.find("LOT-WATER-01")
        self.assertEqual(sorted(n.namespace for n in water), ["sup-aqua", "sup-h2o"])


if __name__ == "__main__":
    unittest.main()
