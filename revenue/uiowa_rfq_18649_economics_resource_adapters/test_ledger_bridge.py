#!/usr/bin/env python3
"""Tests for the UIOWA-105C ledger bridge.

The headline assertion is the refusal: recurring load must never reach the
roadmap lane's one-time `effort` field, because that lane has no recurring
ledger and would charge an annual commitment once, inside a single phase
window. Everything else here protects that boundary or the unit conversion
that makes two landed lanes comparable for the first time.
"""

import json
import os
import unittest

import integrate
import ledger_bridge as lb
from ledgers import (ONE_TIME_EFFORT, RECURRING_EFFORT, ONE_TIME_CASH,
                     RECURRING_CASH, RELEASED_CAPACITY, UNKNOWN, Amount)

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
PRIO = integrate.find_component("uiowa_rfq_18649_prioritization")
PORT = integrate.find_component("uiowa_rfq_18649_ai_opportunity_portfolio")
DECK = integrate.find_component("uiowa_rfq_18649_readout_deck")
HAVE = bool(PRIO and PORT)
WHY = ("needs the sibling component lanes; set UIOWA_REPO_ROOT to the "
       "revenue/ directory when running from a staging copy")


def build():
    return integrate.build(
        os.path.join(PRIO, "fixtures", "synthetic-recommendations.json"),
        os.path.join(FIX, "resource_estimates.contract.json"),
        os.path.join(FIX, "economics.contract.json"),
        os.path.join(PORT, "sample_output", "portfolio.json"),
        os.path.join(FIX, "crosswalk.json"))


class RoadmapRefusalTests(unittest.TestCase):
    """Seam 1: the roadmap lane has no recurring field."""

    def test_recurring_load_is_refused_for_the_roadmap_effort_field(self):
        recurring = Amount(0.01, 0.02, 0.04, RECURRING_EFFORT)
        with self.assertRaises(lb.BridgeRefusal) as ctx:
            lb.to_roadmap_effort(recurring)
        message = str(ctx.exception)
        self.assertIn("no recurring ledger", message)
        self.assertIn("charged once", message)

    def test_every_non_one_time_ledger_is_refused(self):
        for ledger in (RECURRING_EFFORT, ONE_TIME_CASH, RECURRING_CASH,
                       RELEASED_CAPACITY):
            with self.assertRaises(lb.BridgeRefusal, msg=ledger):
                lb.to_roadmap_effort(Amount(1, 2, 3, ledger))

    def test_one_time_effort_is_accepted(self):
        out = lb.to_roadmap_effort(Amount(10, 20, 30, ONE_TIME_EFFORT))
        self.assertEqual(out["UNASSIGNED-ROLE"]["likely"], 20.0)

    def test_unknown_passes_through_as_unknown(self):
        self.assertEqual(lb.to_roadmap_effort(UNKNOWN), UNKNOWN)

    def test_role_split_preserves_the_total(self):
        out = lb.to_roadmap_effort(Amount(10, 20, 30, ONE_TIME_EFFORT),
                                   {"pipeline_engineer": 0.6,
                                    "iam_service_owner": 0.4})
        self.assertAlmostEqual(
            sum(v["likely"] for v in out.values()), 20.0, places=6)


class UnitConversionTests(unittest.TestCase):
    """Seam 2: two landed lanes state the same quantity in different units."""

    def test_conversion_without_a_declared_constant_is_refused(self):
        with self.assertRaises(lb.BridgeRefusal) as ctx:
            lb.fte_year_to_hours_month(Amount(0.01, 0.02, 0.04, RECURRING_EFFORT),
                                       None)
        self.assertIn("without a declared", str(ctx.exception))

    def test_a_nonsense_constant_is_refused(self):
        for bad in (0, -5, "2080"):
            with self.assertRaises(lb.BridgeRefusal, msg=repr(bad)):
                lb.fte_year_to_hours_month(
                    Amount(0.01, 0.02, 0.04, RECURRING_EFFORT), bad)

    def test_conversion_refuses_an_amount_from_the_wrong_ledger(self):
        with self.assertRaises(lb.BridgeRefusal):
            lb.fte_year_to_hours_month(Amount(1, 2, 3, ONE_TIME_EFFORT), 2080.0)

    def test_round_trip_is_the_identity(self):
        original = Amount(0.01, 0.023, 0.05, RECURRING_EFFORT)
        as_hours = lb.fte_year_to_hours_month(original, 2080.0)
        back = lb.hours_month_to_fte_year(as_hours["low"], as_hours["likely"],
                                          as_hours["high"], 2080.0)
        for attr in ("low", "likely", "high"):
            # 6dp display rounding on the way out bounds the round trip.
            self.assertAlmostEqual(getattr(back, attr), getattr(original, attr),
                                   places=6)

    def test_the_conversion_factor_is_recorded_in_the_output(self):
        out = lb.fte_year_to_hours_month(
            Amount(0.01, 0.02, 0.04, RECURRING_EFFORT), 2080.0)
        self.assertIn("2080", out["conversion"])
        self.assertEqual(out["unit"], lb.DECK_RECURRING_UNIT)

    def test_agreement_is_detected(self):
        # 4 staff-hours per month is 48 h/yr, which at 2080 h/FTE-yr is 0.023077.
        verdict, detail = lb.recurring_figures_agree(
            Amount(0.02, 0.023077, 0.03, RECURRING_EFFORT), 4, 2080.0)
        self.assertEqual(verdict, "AGREE", detail)

    def test_disagreement_is_detected_and_named(self):
        verdict, detail = lb.recurring_figures_agree(
            Amount(0.1, 0.18, 0.3, RECURRING_EFFORT), 4, 2080.0)
        self.assertEqual(verdict, "DIFFER")
        self.assertIn("will not agree", detail)

    def test_either_side_unknown_gives_unknown_not_agreement(self):
        verdict, _ = lb.recurring_figures_agree(UNKNOWN, 4, 2080.0)
        self.assertEqual(verdict, UNKNOWN)
        verdict, _ = lb.recurring_figures_agree(
            Amount(0.01, 0.02, 0.04, RECURRING_EFFORT), UNKNOWN, 2080.0)
        self.assertEqual(verdict, UNKNOWN)


class IdentifierIslandTests(unittest.TestCase):
    """Seam 3: report the split, never invent the mapping."""

    def test_two_conventions_are_reported_as_unjoinable(self):
        out = lb.identifier_islands({
            "a": ["REC-SYN-ESS-DEP-001"], "b": ["R-001"]})
        self.assertFalse(out["joinable"])
        self.assertEqual(len(out["islands"]), 2)
        self.assertIn("CANNOT be joined", out["verdict"])
        self.assertIn("inventing the mapping", out["verdict"])

    def test_one_convention_is_reported_as_joinable(self):
        out = lb.identifier_islands({
            "a": ["REC-SYN-ESS-DEP-001"], "b": ["REC-SYN-IAM-SEC-001"]})
        self.assertTrue(out["joinable"])

    def test_no_mapping_between_conventions_is_produced(self):
        out = lb.identifier_islands({"a": ["REC-SYN-X-001"], "b": ["R-001"]})
        blob = json.dumps(out)
        # Nothing anywhere should pair an id from one island with the other.
        for island in out["islands"]:
            self.assertNotIn("maps_to", island)
            self.assertNotIn("equivalent", blob)


@unittest.skipUnless(HAVE, WHY)
class AgainstLandedComponentsTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.result = build()
        cls.bridge = lb.roadmap_items_from_integration(cls.result)

    def test_no_recurring_figure_appears_inside_any_item_effort(self):
        """The whole point, asserted against real data: every recurring value
        in the integration must be absent from the emitted effort fields."""
        recurring_values = set()
        for entry in self.result["recommendations"]:
            r = entry["ledgers"][RECURRING_EFFORT]
            if r["state"] != UNKNOWN:
                recurring_values.update([r["low"], r["likely"], r["high"]])
        self.assertTrue(recurring_values, "fixture must exercise this")
        emitted = set()
        for item in self.bridge["items"]:
            for band in item["effort"].values():
                emitted.update(band.values())
        self.assertEqual(recurring_values & emitted, set())

    def test_recurring_load_is_returned_separately_with_its_reason(self):
        sidecar = self.bridge["recurring_not_representable"]
        self.assertTrue(sidecar)
        for row in sidecar:
            self.assertIn("charge an annual commitment once",
                          row["why_it_is_not_in_effort"])

    def test_unestimated_recommendations_are_named_not_emitted_as_zero(self):
        unestimated = {u["rec"] for u in self.bridge["unestimated"]}
        self.assertIn("REC-SYN-IAM-AI-001", unestimated)
        emitted = {i["rec"] for i in self.bridge["items"]}
        self.assertEqual(unestimated & emitted, set())
        for u in self.bridge["unestimated"]:
            self.assertIn("not zero capacity consumed", u["handling"])

    def test_a_floor_only_estimate_is_marked_rather_than_presented_as_complete(self):
        """A total built from some known and some unestimated contributors is a
        floor. The bridge must carry that marker through, or the roadmap plans
        against a number it believes is the whole cost."""
        partial = {
            "recommendations": [{
                "recommendation_id": "REC-SYN-TEST-001", "title": "t",
                "ledgers": {
                    ONE_TIME_EFFORT: {
                        "state": "PARTIAL", "low": 10.0, "likely": 20.0,
                        "high": 30.0, "complete": False,
                        "note": "floor only: 1 contributor supplied no estimate "
                                "and is NOT counted as zero"},
                    RECURRING_EFFORT: {"state": UNKNOWN, "low": UNKNOWN,
                                       "likely": UNKNOWN, "high": UNKNOWN,
                                       "complete": False, "note": ""},
                }}]}
        bridge = lb.roadmap_items_from_integration(partial)
        item = bridge["items"][0]
        self.assertFalse(item["effort_complete"])
        self.assertIn("NOT counted as zero", item["effort_note"])
        self.assertIn("FLOOR ONLY", lb.render(bridge))

    def test_emitted_meta_keeps_the_receiving_lane_s_no_individuals_rule(self):
        meta = self.bridge["meta"]
        self.assertIn("No named individual", meta["no_individuals_notice"])
        self.assertIn("recurring_ledger_warning", meta)
        self.assertEqual(meta["effort_unit"], lb.ROADMAP_EFFORT_UNIT)

    @unittest.skipUnless(DECK, WHY)
    def test_the_real_deck_recurring_figure_is_restated_in_fte_per_year(self):
        with open(os.path.join(DECK, "data", "example-report.json"),
                  encoding="utf-8") as fh:
            deck = json.load(fh)
        rows = {r["id"]: r for r in lb.deck_recurring_in_fte_year(deck, 2080.0)}
        self.assertEqual(rows["RES-001"]["stated"], 4)
        self.assertAlmostEqual(rows["RES-001"]["fte_per_year"], 0.02308, places=5)

    @unittest.skipUnless(DECK, WHY)
    def test_a_deck_unknown_stays_unknown_and_is_not_converted_to_zero(self):
        with open(os.path.join(DECK, "data", "example-report.json"),
                  encoding="utf-8") as fh:
            deck = json.load(fh)
        rows = {r["id"]: r for r in lb.deck_recurring_in_fte_year(deck, 2080.0)}
        self.assertEqual(rows["RES-002"]["fte_per_year"], UNKNOWN)
        self.assertNotEqual(rows["RES-002"]["fte_per_year"], 0)

    def test_report_renders_the_warning_and_the_island_split(self):
        islands = lb.identifier_islands({
            "prioritization": [e["recommendation_id"]
                               for e in self.result["recommendations"]],
            "readout_deck": ["R-001", "R-002"]})
        text = lb.render(self.bridge, None, islands)
        self.assertIn("cannot represent", text)
        self.assertIn("CANNOT be joined", text)
        self.assertIn("must not treat these as free", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
