#!/usr/bin/env python3
"""Tests for UIOWA-105 - economics and resource estimates joined to recommendations.

The assertions that matter:
  * the five ledgers can never be combined;
  * shared work is counted once in the programme roll-up and still shown under
    every recommendation that needs it, with the difference published;
  * a missing estimate stays UNKNOWN and never becomes zero cost, zero effort
    or zero benefit -- while an assessed real zero stays a zero;
  * ranges, bases and source record ids survive the mapping;
  * a reference to a recommendation that does not exist is reported and does
    not inflate any total.
"""

import csv
import json
import os
import tempfile
import unittest

import adapters
import integrate
from ledgers import (
    ONE_TIME_EFFORT, RECURRING_EFFORT, ONE_TIME_CASH, RECURRING_CASH,
    RELEASED_CAPACITY, ALL_LEDGERS, UNKNOWN, Amount, AdapterError,
    LedgerUnitError, read_amount,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
RESOURCE = os.path.join(FIX, "resource_estimates.contract.json")
ECONOMICS = os.path.join(FIX, "economics.contract.json")
CROSSWALK = os.path.join(FIX, "crosswalk.json")

PRIO = integrate.find_component("uiowa_rfq_18649_prioritization")
PORT = integrate.find_component("uiowa_rfq_18649_ai_opportunity_portfolio")
REGISTER = os.path.join(PRIO, "fixtures", "synthetic-recommendations.json") if PRIO else None
PORTFOLIO = os.path.join(PORT, "sample_output", "portfolio.json") if PORT else None

HAVE_REAL = bool(REGISTER and os.path.exists(REGISTER)
                 and PORTFOLIO and os.path.exists(PORTFOLIO))
WHY_SKIPPED = ("needs the sibling component lanes; set UIOWA_REPO_ROOT to the "
               "revenue/ directory when running from a staging copy")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def built():
    return integrate.build(REGISTER, RESOURCE, ECONOMICS, PORTFOLIO, CROSSWALK)


def rec(result, rid):
    for entry in result["recommendations"]:
        if entry["recommendation_id"] == rid:
            return entry
    raise AssertionError("no recommendation %r" % rid)


def item(result, wid):
    for entry in result["work_items"]:
        if entry["work_item_id"] == wid:
            return entry
    raise AssertionError("no work item %r" % wid)


class LedgerSeparationTests(unittest.TestCase):

    def test_no_two_ledgers_can_be_added(self):
        made = {l: Amount(1, 2, 3, l) for l in ALL_LEDGERS}
        for a in ALL_LEDGERS:
            for b in ALL_LEDGERS:
                if a == b:
                    continue
                with self.assertRaises(LedgerUnitError,
                                       msg="%s + %s must be refused" % (a, b)):
                    made[a] + made[b]

    def test_hours_ledgers_do_not_add_despite_sharing_a_unit(self):
        """One-time effort hours and released-capacity hours are both hours.
        Checking the unit STRING rather than the dimension is what stops them
        combining into a number that means nothing."""
        with self.assertRaises(LedgerUnitError):
            Amount(10, 20, 30, ONE_TIME_EFFORT) + Amount(1, 2, 3, RELEASED_CAPACITY)

    def test_sum_within_one_ledger_is_allowed(self):
        total = Amount(10, 20, 30, ONE_TIME_CASH) + Amount(1, 2, 3, ONE_TIME_CASH)
        self.assertEqual((total.low, total.likely, total.high), (11.0, 22.0, 33.0))


class ReadAmountTests(unittest.TestCase):

    def test_absent_and_explicit_unknowns_stay_unknown(self):
        for raw in (None, "", "UNKNOWN", "unknown", "n/a", "TBD", "?",
                    {"basis": "nobody has decided", "value": None}):
            self.assertEqual(
                read_amount(raw, ONE_TIME_CASH, "c", "R-1", "f"), UNKNOWN,
                "%r should stay UNKNOWN" % (raw,))

    def test_unknown_is_never_a_zero_amount(self):
        result = read_amount({"basis": "not decided", "value": None},
                             ONE_TIME_EFFORT, "c", "R-1", "f")
        self.assertEqual(result, UNKNOWN)
        self.assertNotIsInstance(result, Amount)

    def test_real_zero_is_kept_as_a_zero(self):
        z = read_amount({"low": 0, "likely": 0, "high": 0, "basis": "assessed"},
                        ONE_TIME_CASH, "c", "R-1", "f")
        self.assertIsInstance(z, Amount)
        self.assertEqual(z.likely, 0.0)

    def test_partial_range_is_refused_not_completed(self):
        with self.assertRaises(AdapterError) as ctx:
            read_amount({"low": 1, "high": 3}, ONE_TIME_EFFORT, "c", "R-9", "f")
        self.assertIn("R-9", str(ctx.exception))
        self.assertIn("partial range", str(ctx.exception))

    def test_estimate_written_in_words_is_refused(self):
        with self.assertRaises(AdapterError):
            read_amount("high", ONE_TIME_EFFORT, "c", "R-1", "f")

    def test_boolean_is_refused_rather_than_read_as_one(self):
        with self.assertRaises(AdapterError):
            read_amount(True, ONE_TIME_EFFORT, "c", "R-1", "f")

    def test_mid_is_accepted_as_the_middle_bound(self):
        a = read_amount({"low": 1, "mid": 2, "high": 4}, ONE_TIME_CASH,
                        "c", "R-1", "f")
        self.assertEqual(a.likely, 2.0)

    def test_point_estimate_is_widened_and_says_so(self):
        a = read_amount(7, ONE_TIME_EFFORT, "c", "R-1", "f")
        self.assertEqual((a.low, a.likely, a.high), (7.0, 7.0, 7.0))
        self.assertIn("no bounds", a.basis)


class AdapterTests(unittest.TestCase):

    def test_resource_adapter_preserves_range_basis_and_source(self):
        items = adapters.adapt_resource_estimates(load(RESOURCE))
        wi = [i for i in items if i["work_item_id"] == "WI-ESS-RELNOTES-001"][0]
        a = wi["amounts"][ONE_TIME_EFFORT]
        self.assertEqual((a.low, a.likely, a.high), (60.0, 90.0, 140.0))
        self.assertIn("estimator build-up", a.basis)
        self.assertEqual(a.source_record_id, "WI-ESS-RELNOTES-001")
        self.assertEqual(a.source_component, "uiowa-086-resource-estimate")

    def test_resource_adapter_does_not_claim_cash(self):
        """Cash belongs to the economics adapter. Two adapters claiming the
        same money is one of the double counts this component prevents."""
        items = adapters.adapt_resource_estimates(load(RESOURCE))
        for wi in items:
            self.assertNotIn(ONE_TIME_CASH, wi["amounts"])
            self.assertNotIn(RECURRING_CASH, wi["amounts"])

    def test_economics_adapter_does_not_claim_effort(self):
        items, _ = adapters.adapt_economics(load(ECONOMICS))
        for entry in items:
            self.assertNotIn(ONE_TIME_EFFORT, entry["amounts"])
            self.assertNotIn(RECURRING_EFFORT, entry["amounts"])

    def test_economics_without_a_currency_is_refused(self):
        doc = load(ECONOMICS)
        del doc["currency"]
        with self.assertRaises(AdapterError) as ctx:
            adapters.adapt_economics(doc)
        self.assertIn("currency", str(ctx.exception))

    def test_duplicate_work_item_id_is_refused(self):
        doc = load(RESOURCE)
        doc["work_items"].append(dict(doc["work_items"][0]))
        with self.assertRaises(AdapterError):
            adapters.adapt_resource_estimates(doc)

    def test_wrong_schema_version_is_refused(self):
        doc = load(RESOURCE)
        doc["schema_version"] = "uiowa-086-resource-estimate/99"
        with self.assertRaises(AdapterError):
            adapters.adapt_resource_estimates(doc)

    @unittest.skipUnless(HAVE_REAL, WHY_SKIPPED)
    def test_portfolio_adapter_does_not_guess_the_crosswalk(self):
        items = adapters.adapt_opportunity_portfolio(load(PORTFOLIO), {})
        self.assertTrue(items)
        for entry in items:
            self.assertEqual(entry["recommendation_ids"], [])
            self.assertIn("not guessed", entry["unmapped_reason"])

    @unittest.skipUnless(HAVE_REAL, WHY_SKIPPED)
    def test_portfolio_adapter_carries_a_negative_released_capacity(self):
        """The portfolio is allowed to report a workflow that costs more than
        it saves. The adapter must not clamp that on the way through."""
        crosswalk = load(CROSSWALK)["candidates"]
        items = adapters.adapt_opportunity_portfolio(load(PORTFOLIO), crosswalk)
        ess2 = [i for i in items if i["source_record_id"] == "OPP-ESS-02"][0]
        self.assertLess(ess2["amounts"][RELEASED_CAPACITY].low, 0)

    @unittest.skipUnless(HAVE_REAL, WHY_SKIPPED)
    def test_portfolio_unknown_survives_the_mapping(self):
        crosswalk = load(CROSSWALK)["candidates"]
        items = adapters.adapt_opportunity_portfolio(load(PORTFOLIO), crosswalk)
        iam2 = [i for i in items if i["source_record_id"] == "OPP-IAM-02"][0]
        self.assertEqual(iam2["amounts"][RELEASED_CAPACITY], UNKNOWN)


class MergeTests(unittest.TestCase):

    def _item(self, wid, ledger, low, likely, high, component, record):
        return {
            "work_item_id": wid, "label": "l", "recommendation_ids": ["R-1"],
            "source_component": component, "source_record_id": record,
            "amounts": {ledger: Amount(low, likely, high, ledger,
                                       source_component=component,
                                       source_record_id=record)},
            "specialist_roles": [], "notes": "", "unmapped_reason": "",
        }

    def test_different_ledgers_of_one_work_item_merge_into_one_item(self):
        merged, conflicts = integrate.merge_work_items(
            [self._item("WI-1", ONE_TIME_EFFORT, 1, 2, 3, "resource", "A")],
            [self._item("WI-1", ONE_TIME_CASH, 10, 20, 30, "economics", "B")])
        self.assertEqual(len(merged), 1)
        self.assertEqual(conflicts, [])
        self.assertEqual(merged[0]["amounts"][ONE_TIME_EFFORT].likely, 2.0)
        self.assertEqual(merged[0]["amounts"][ONE_TIME_CASH].likely, 20.0)

    def test_two_sources_disagreeing_on_one_ledger_is_reported_not_resolved(self):
        merged, conflicts = integrate.merge_work_items(
            [self._item("WI-1", ONE_TIME_EFFORT, 60, 90, 140, "resource", "A")],
            [self._item("WI-1", ONE_TIME_EFFORT, 25, 45, 80, "portfolio", "B")])
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["ledger"], ONE_TIME_EFFORT)
        # Neither value silently wins.
        self.assertEqual(merged[0]["amounts"][ONE_TIME_EFFORT], UNKNOWN)

    def test_two_sources_agreeing_is_corroboration_not_a_conflict(self):
        merged, conflicts = integrate.merge_work_items(
            [self._item("WI-1", RECURRING_EFFORT, 0.01, 0.02, 0.04, "resource", "A")],
            [self._item("WI-1", RECURRING_EFFORT, 0.01, 0.02, 0.04, "portfolio", "B")])
        self.assertEqual(conflicts, [])
        self.assertEqual(merged[0]["amounts"][RECURRING_EFFORT].likely, 0.02)


class TotalTests(unittest.TestCase):

    def _wi(self, wid, amount):
        return {"work_item_id": wid, "amounts": {ONE_TIME_EFFORT: amount}}

    def test_total_with_an_unknown_contributor_is_a_floor_not_a_sum_with_zero(self):
        t = integrate.total([
            self._wi("A", Amount(10, 20, 30, ONE_TIME_EFFORT, source_record_id="A")),
            self._wi("B", UNKNOWN)], ONE_TIME_EFFORT)
        self.assertEqual(t["state"], "PARTIAL")
        self.assertFalse(t["complete"])
        self.assertEqual(t["unknown_contributors"], ["B"])
        self.assertIn("NOT counted as zero", t["note"])
        self.assertEqual(t["likely"], 20.0)     # the known part, labelled a floor

    def test_total_with_no_known_contributor_is_unknown_not_zero(self):
        t = integrate.total([self._wi("A", UNKNOWN)], ONE_TIME_EFFORT)
        self.assertEqual(t["state"], UNKNOWN)
        self.assertEqual(t["likely"], UNKNOWN)
        self.assertNotEqual(t["likely"], 0)

    def test_assessed_zero_is_a_complete_total_of_zero(self):
        t = integrate.total([
            self._wi("A", Amount(0, 0, 0, ONE_TIME_EFFORT, source_record_id="A"))],
            ONE_TIME_EFFORT)
        self.assertEqual(t["state"], "COMPLETE")
        self.assertTrue(t["complete"])
        self.assertEqual(t["likely"], 0.0)


@unittest.skipUnless(HAVE_REAL, WHY_SKIPPED)
class IntegrationTests(unittest.TestCase):
    """Run against the components actually on main: the prioritization
    register and the opportunity portfolio's published output."""

    @classmethod
    def setUpClass(cls):
        cls.result = built()

    def test_every_register_recommendation_appears(self):
        register = load(REGISTER)
        self.assertEqual(
            sorted(e["recommendation_id"] for e in self.result["recommendations"]),
            sorted(r["recommendation_id"] for r in register["recommendations"]))

    def test_shared_work_is_counted_once_in_the_rollup(self):
        rollup = self.result["portfolio_rollup"][ONE_TIME_CASH]
        # The training is the only one-time cash above zero and it is shared by
        # two recommendations. The programme pays for it once.
        self.assertEqual(rollup["likely"], 3800.0)

    def test_shared_work_is_still_visible_under_each_recommendation(self):
        for rid in ("REC-SYN-RIS-SEC-001", "REC-SYN-IAM-SEC-001"):
            entry = rec(self.result, rid)
            self.assertIn("WI-TRAIN-ACCESSREV-001", entry["work_item_ids"])
            self.assertIn("WI-TRAIN-ACCESSREV-001", entry["shared_work_item_ids"])
            self.assertEqual(entry["ledgers"][ONE_TIME_CASH]["likely"], 3800.0)

    def test_per_recommendation_sum_exceeds_the_rollup_by_the_published_delta(self):
        for ledger in ALL_LEDGERS:
            roll = self.result["portfolio_rollup"][ledger]
            per = self.result["sum_of_per_recommendation"][ledger]
            delta = self.result["shared_work_not_double_counted"][ledger]
            if roll["state"] == UNKNOWN or per["state"] == UNKNOWN:
                continue
            self.assertAlmostEqual(delta["likely"], per["likely"] - roll["likely"],
                                   places=4, msg=ledger)
            self.assertGreaterEqual(per["likely"], roll["likely"], ledger)

    def test_the_delta_is_actually_non_zero_somewhere(self):
        """A test that only checks the arithmetic would pass on a fixture with
        no shared work at all. Prove the case is exercised."""
        deltas = [self.result["shared_work_not_double_counted"][l]["likely"]
                  for l in ALL_LEDGERS
                  if self.result["shared_work_not_double_counted"][l] != UNKNOWN]
        self.assertTrue(any(d > 0 for d in deltas))

    def test_recommendation_with_no_resourcing_is_not_costed_at_zero(self):
        entry = rec(self.result, "REC-SYN-IAM-AI-001")
        self.assertEqual(entry["resourcing_state"], "NO_RESOURCING_DATA")
        for ledger in ALL_LEDGERS:
            self.assertEqual(entry["ledgers"][ledger]["state"], UNKNOWN)
            self.assertNotEqual(entry["ledgers"][ledger]["likely"], 0)
        self.assertIn("REC-SYN-IAM-AI-001",
                      self.result["recommendations_without_resourcing"])

    def test_cross_component_disagreement_is_surfaced(self):
        conflicts = self.result["component_conflicts"]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["work_item_id"], "WI-ESS-RELNOTES-001")
        self.assertEqual(conflicts[0]["ledger"], ONE_TIME_EFFORT)
        # ...and the affected recommendation shows UNKNOWN rather than a
        # quietly-chosen winner.
        self.assertEqual(
            rec(self.result, "REC-SYN-ESS-DEP-001")["ledgers"][ONE_TIME_EFFORT]["state"],
            UNKNOWN)

    def test_dangling_reference_is_reported(self):
        self.assertIn("REC-SYN-ESS-XX-999", self.result["dangling_recommendation_ids"])

    def test_dangling_reference_does_not_inflate_any_total(self):
        """Regression: a work item naming a recommendation that does not exist
        was being treated as shared, which repeated it in the per-recommendation
        sum even though no row in the table ever charges it."""
        shared_ids = [s["work_item_id"] for s in self.result["shared_work_items"]]
        self.assertNotIn("WI-RIS-WINDOW-DOC-001", shared_ids)
        wi = item(self.result, "WI-RIS-WINDOW-DOC-001")
        self.assertEqual(wi["known_recommendation_ids"], ["REC-SYN-RIS-DEP-001"])
        per = self.result["sum_of_per_recommendation"][ONE_TIME_EFFORT]
        roll = self.result["portfolio_rollup"][ONE_TIME_EFFORT]
        self.assertAlmostEqual(per["likely"] - roll["likely"], 190.0, places=4)

    def test_unmapped_work_items_are_carried_not_dropped(self):
        unmapped = {i["work_item_id"] for i in self.result["unmapped_work_items"]}
        self.assertIn("WI-UNSCOPED-DISCOVERY-001", unmapped)
        self.assertIn("WI-FROM-OPP-RIS-01", unmapped)
        for entry in self.result["unmapped_work_items"]:
            self.assertTrue(entry["reason"])

    def test_unknown_recurring_effort_survives_into_the_recommendation_row(self):
        entry = rec(self.result, "REC-SYN-ESS-SEC-001")
        self.assertEqual(entry["ledgers"][RECURRING_EFFORT]["state"], UNKNOWN)
        self.assertEqual(entry["resourcing_state"], "PARTIAL")

    def test_original_ranges_are_still_present_in_the_output(self):
        wi = item(self.result, "WI-TRAIN-ACCESSREV-001")
        a = wi["amounts"][ONE_TIME_EFFORT]
        self.assertEqual((a["low"], a["likely"], a["high"]), (70.0, 110.0, 160.0))
        self.assertTrue(a["basis"])
        self.assertTrue(a["source_record_id"])

    def test_specialist_roles_are_carried(self):
        wi = item(self.result, "WI-TRAIN-ACCESSREV-001")
        roles = sorted(r["role"] for r in wi["specialist_roles"])
        self.assertEqual(roles, ["IAM analyst", "Training"])

    def test_output_is_deterministic(self):
        self.assertEqual(built()["content_digest"], self.result["content_digest"])

    def test_writers_produce_readable_files(self):
        with tempfile.TemporaryDirectory() as d:
            integrate.write_resourcing_table(self.result, os.path.join(d, "t.csv"))
            integrate.write_rollup(self.result, os.path.join(d, "r.csv"))
            integrate.write_report(self.result, os.path.join(d, "r.md"))
            with open(os.path.join(d, "t.csv"), encoding="utf-8", newline="") as fh:
                rows = {r["recommendation_id"]: r for r in csv.DictReader(fh)}
            with open(os.path.join(d, "r.md"), encoding="utf-8") as fh:
                report = fh.read()
        self.assertEqual(rows["REC-SYN-IAM-AI-001"]["one_time_effort_hours_likely"],
                         UNKNOWN)
        self.assertEqual(rows["REC-SYN-RIS-SEC-001"]["one_time_cash_likely"], "3800.0")
        self.assertIn("shared_work_not_double_counted", report)
        self.assertIn("Not costed at all", report)


class CsvGuardTests(unittest.TestCase):

    def test_negative_numbers_survive(self):
        self.assertEqual(integrate.csv_cell("-256.6667"), "-256.6667")
        self.assertEqual(integrate.csv_cell(-11.0), "-11.0")

    def test_formulas_are_neutralised(self):
        self.assertEqual(integrate.csv_cell("=1+1"), "'=1+1")
        self.assertEqual(integrate.csv_cell("@ref"), "'@ref")


class CliTests(unittest.TestCase):

    def test_missing_input_file_is_reported_not_crashed(self):
        with tempfile.TemporaryDirectory() as d:
            code = integrate.main([
                "--register", os.path.join(d, "nope.json"),
                "--resource-estimates", RESOURCE, "--economics", ECONOMICS,
                "--portfolio", "", "--crosswalk", CROSSWALK, "--out", d])
        self.assertEqual(code, 2)

    def test_malformed_json_is_reported_not_crashed(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.json")
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write("{not json")
            code = integrate.main([
                "--register", bad, "--resource-estimates", RESOURCE,
                "--economics", ECONOMICS, "--portfolio", "",
                "--crosswalk", CROSSWALK, "--out", d])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
