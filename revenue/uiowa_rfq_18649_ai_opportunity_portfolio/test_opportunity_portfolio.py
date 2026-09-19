#!/usr/bin/env python3
"""Tests for the UIOWA-072 AI opportunity and value portfolio.

These assert the behaviours that make the difference between a usable
comparison and a misleading one:

  * one-time and recurring effort can never be summed;
  * a missing estimate stays UNKNOWN instead of becoming zero effort;
  * a candidate with UNKNOWN dimensions cannot be ranked or composited;
  * benefit is allowed to come out negative and is not clamped;
  * overlapping ranges are reported as a tie rather than invented precision;
  * the CSV guard does not mangle the negative numbers this tool exists to
    be able to report.
"""

import csv
import io
import json
import os
import tempfile
import unittest

import opportunity_portfolio as op

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "candidates.json")


def load():
    return op.load_portfolio(FIXTURE)


def by_id(result, cid):
    for ev in result["candidates"]:
        if ev["id"] == cid:
            return ev
    raise AssertionError("no candidate %r in result" % cid)


class LedgerSeparationTests(unittest.TestCase):
    """The single guardrail this build exists for."""

    def test_one_time_and_recurring_cannot_be_added(self):
        one_time = op.Quantity(25, 45, 80, op.UNIT_ONE_TIME_HOURS)
        recurring = op.Quantity(0.01, 0.02, 0.04, op.UNIT_RECURRING_FTE)
        with self.assertRaises(op.LedgerUnitError):
            one_time + recurring
        with self.assertRaises(op.LedgerUnitError):
            recurring + one_time

    def test_benefit_cannot_be_added_to_either_effort_ledger(self):
        benefit = op.Quantity(26.4, 68.0, 113.0, op.UNIT_BENEFIT_HOURS_YEAR)
        one_time = op.Quantity(25, 45, 80, op.UNIT_ONE_TIME_HOURS)
        recurring = op.Quantity(0.01, 0.02, 0.04, op.UNIT_RECURRING_FTE)
        # 'hours-per-year released' and 'hours, one-time' are both hours. That
        # is exactly why the unit string, not the dimension, is what is checked.
        with self.assertRaises(op.LedgerUnitError):
            benefit + one_time
        with self.assertRaises(op.LedgerUnitError):
            benefit + recurring

    def test_sum_within_one_ledger_is_allowed(self):
        a = op.Quantity(10, 20, 30, op.UNIT_ONE_TIME_HOURS)
        b = op.Quantity(5, 6, 7, op.UNIT_ONE_TIME_HOURS)
        total = a + b
        self.assertEqual((total.low, total.likely, total.high), (15.0, 26.0, 37.0))
        self.assertEqual(total.unit, op.UNIT_ONE_TIME_HOURS)

    def test_recurring_is_carried_as_fte_per_year_not_hours(self):
        result = op.analyse(load())
        rec = by_id(result, "OPP-IAM-01")["recurring_maintenance"]
        self.assertEqual(rec["unit"], op.UNIT_RECURRING_FTE)
        self.assertLess(rec["high"], 1.0)   # an FTE fraction, not an hour count

    def test_recurring_context_hours_are_labelled_as_context_only(self):
        result = op.analyse(load())
        ctx = by_id(result, "OPP-IAM-01")["recurring_context_hours_per_year"]
        self.assertIn("NOT added to the one-time ledger", ctx["note"])

    def test_upkeep_larger_than_benefit_is_flagged_not_netted(self):
        """IAM-01 is cheap to build and expensive to keep. A tool that netted
        the ledgers would report it as a clear win on a 0.4-year payback."""
        result = op.analyse(load())
        ev = by_id(result, "OPP-IAM-01")
        self.assertTrue(any(f.startswith("RECURRING-LOAD-EXCEEDS-BENEFIT")
                            for f in ev["flags"]))
        # The benefit figure is untouched by the flag -- nothing was subtracted.
        self.assertAlmostEqual(ev["benefit_hours_per_year"]["likely"], 138.25, places=2)


class UnknownNeverBecomesZeroTests(unittest.TestCase):

    def test_missing_estimate_stays_unknown(self):
        result = op.analyse(load())
        ev = by_id(result, "OPP-IAM-02")
        self.assertEqual(ev["benefit_hours_per_year"], op.UNKNOWN)
        self.assertNotEqual(ev["benefit_hours_per_year"], 0)
        self.assertEqual(ev["decision_class"], op.CLASS_BLOCKED)
        self.assertIn("expected_benefit", ev["unknown_dimensions"])
        self.assertIn("input_availability", ev["unknown_dimensions"])

    def test_unknown_candidate_is_unranked_but_still_listed(self):
        result = op.analyse(load())
        ev = by_id(result, "OPP-IAM-02")
        self.assertIsNone(ev["rank"])
        self.assertIn("UNRANKED - pending", ev["rank_note"])
        # Listed, not dropped: silently omitting it would read as 'nothing here'.
        self.assertIn("OPP-IAM-02", result["unranked"])
        self.assertIn("OPP-IAM-02", result["decision_class_index"][op.CLASS_BLOCKED])

    def test_unknown_candidate_carries_an_evidence_request(self):
        result = op.analyse(load())
        self.assertTrue(by_id(result, "OPP-IAM-02")["evidence_requests"])

    def test_partial_range_is_an_error_not_a_filled_in_default(self):
        with self.assertRaises(op.PortfolioDataError) as ctx:
            op._read_range({"low": 1, "high": 3}, "volume_items_per_year", "X-1")
        self.assertIn("likely", str(ctx.exception))

    def test_unbaselined_measure_is_not_recorded_as_zero(self):
        doc = load()
        cand = [c for c in doc["candidates"] if c["id"] == "OPP-IAM-02"][0]
        measure = cand["measures"][0]
        self.assertEqual(measure["baseline_state"], "NOT-BASELINED")
        self.assertIsNone(measure["baseline_value"])
        self.assertEqual(op.measurability_level(cand), "MODERATE")
        report = self._render(load())
        self.assertIn("baseline required", report)

    def _render(self, doc):
        result = op.analyse(doc)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.md")
            op.write_markdown(result, path)
            with open(path, encoding="utf-8") as fh:
                return fh.read()

    def test_composite_is_refused_when_any_dimension_is_unknown(self):
        result = op.analyse(load(), with_composite=True)
        blocked = by_id(result, "OPP-IAM-02")
        self.assertEqual(blocked["composite_score"], op.UNKNOWN)
        self.assertIn("refused", blocked["composite_note"])
        # ...and is computed where everything IS assessed, so the refusal is a
        # real gate rather than the feature being broken.
        self.assertIsInstance(by_id(result, "OPP-ESS-01")["composite_score"], float)


class BenefitArithmeticTests(unittest.TestCase):

    def test_negative_benefit_is_reported_not_clamped(self):
        result = op.analyse(load())
        ev = by_id(result, "OPP-RIS-02")
        self.assertLess(ev["benefit_hours_per_year"]["high"], 0)
        self.assertEqual(ev["decision_class"], op.CLASS_DO_NOT_PURSUE)

    def test_low_suitability_reason_also_reports_the_arithmetic(self):
        result = op.analyse(load())
        reason = by_id(result, "OPP-RIS-02")["decision_reason"]
        self.assertIn("task suitability is LOW", reason)
        self.assertIn("arithmetic agrees independently", reason)

    def test_straddling_zero_is_uncertain_not_positive(self):
        result = op.analyse(load())
        ev = by_id(result, "OPP-ESS-02")
        b = ev["benefit_hours_per_year"]
        self.assertLess(b["low"], 0)
        self.assertGreater(b["high"], 0)
        self.assertEqual(ev["decision_class"], op.CLASS_UNCERTAIN)

    def test_interval_bounds_are_ordered_for_every_candidate(self):
        result = op.analyse(load())
        for ev in result["candidates"]:
            for key in ("benefit_hours_per_year", "one_time_implementation",
                        "recurring_maintenance"):
                q = ev[key]
                if q == op.UNKNOWN:
                    continue
                self.assertLessEqual(q["low"], q["likely"], "%s %s" % (ev["id"], key))
                self.assertLessEqual(q["likely"], q["high"], "%s %s" % (ev["id"], key))

    def test_more_volume_makes_a_losing_workflow_lose_more(self):
        """Interval multiplication has to handle a negative per-item result.
        A naive low = per_item_low * volume_low understates the downside."""
        inputs = {
            "volume_items_per_year": {"low": 100, "likely": 200, "high": 1000},
            "baseline_minutes_per_item": {"low": 1, "likely": 1, "high": 1},
            "assisted_minutes_per_item": {"low": 1, "likely": 1, "high": 1},
            "checking_minutes_per_item": {"low": 2, "likely": 2, "high": 2},
            "repair_minutes_per_reworked_item": {"low": 0, "likely": 0, "high": 0},
            "rework_rate": {"low": 0, "likely": 0, "high": 0},
        }
        q = op.net_benefit_hours_per_year(inputs, "T-1")
        self.assertAlmostEqual(q.low, (-2.0 * 1000) / 60.0)   # worst case is MORE volume
        self.assertAlmostEqual(q.high, (-2.0 * 100) / 60.0)

    def test_payback_uses_the_one_time_ledger_only(self):
        result = op.analyse(load())
        ev = by_id(result, "OPP-ESS-01")
        expected = ev["one_time_implementation"]["likely"] / ev["benefit_hours_per_year"]["likely"]
        self.assertAlmostEqual(ev["simple_payback_years"], round(expected, 2), places=2)

    def test_payback_is_unknown_when_benefit_is_not_positive(self):
        result = op.analyse(load())
        self.assertEqual(by_id(result, "OPP-ESS-02")["simple_payback_years"], op.UNKNOWN)


class RankingHonestyTests(unittest.TestCase):

    def test_overlapping_intervals_share_a_rank(self):
        result = op.analyse(load())
        iam1, ris1 = by_id(result, "OPP-IAM-01"), by_id(result, "OPP-RIS-01")
        self.assertEqual(iam1["rank"], ris1["rank"])
        self.assertIn("TIED - not separable", iam1["rank_note"])
        self.assertIn("TIED - not separable", ris1["rank_note"])

    def test_competition_ranking_skips_after_a_tie(self):
        result = op.analyse(load())
        # two candidates tied at 1 means the next distinct group is 3, not 2.
        self.assertEqual(by_id(result, "OPP-ESS-01")["rank"], 3)

    def test_non_overlapping_candidate_is_separated(self):
        result = op.analyse(load())
        ess1, ess2 = by_id(result, "OPP-ESS-01"), by_id(result, "OPP-ESS-02")
        self.assertNotEqual(ess1["rank"], ess2["rank"])
        self.assertEqual(ess2["rank_note"], "")

    def test_tie_grouping_does_not_chain_the_whole_portfolio(self):
        """Grouping against the group LEADER rather than the previous member
        stops a run of slight overlaps collapsing into one meaningless tie."""
        result = op.analyse(load())
        ranks = sorted({ev["rank"] for ev in result["candidates"]
                        if ev["rank"] is not None})
        self.assertGreater(len(ranks), 1)

    def test_every_candidate_appears_in_the_class_index(self):
        result = op.analyse(load())
        indexed = sorted(c for ids in result["decision_class_index"].values() for c in ids)
        self.assertEqual(indexed, sorted(ev["id"] for ev in result["candidates"]))


class RevisabilityTests(unittest.TestCase):

    def test_revision_impact_names_decision_critical_assumptions(self):
        result = op.analyse(load())
        crit = result["decision_critical_assumptions"]
        self.assertTrue(crit)
        for f in crit:
            self.assertTrue(f["changes"])
            self.assertTrue(f["decision_critical"])
        # and it genuinely separates: not everything is critical.
        self.assertLess(len(crit), len(result["revision_impact"]))

    def test_every_ranged_assumption_carries_a_basis(self):
        result = op.analyse(load())
        for f in result["revision_impact"]:
            self.assertIn(f["basis"], ("ASSUMED", "SYNTHETIC-FIXTURE",
                                       "UNIVERSITY-EVIDENCE"))

    def test_unknown_inputs_are_not_swept(self):
        """IAM-02's volume is UNKNOWN. Sweeping it would require inventing
        bounds, which is the fabrication this model refuses."""
        result = op.analyse(load())
        swept = {(f["candidate"], f["assumption"]) for f in result["revision_impact"]}
        self.assertNotIn(("OPP-IAM-02", "volume_items_per_year"), swept)
        self.assertIn(("OPP-IAM-02", "one_time_implementation_hours"), swept)


class OutputTests(unittest.TestCase):

    def test_csv_guard_preserves_negative_numbers(self):
        self.assertEqual(op.csv_cell("-346.0"), "-346.0")
        self.assertEqual(op.csv_cell(-346.0), "-346.0")
        self.assertEqual(op.csv_cell("-1041.6667"), "-1041.6667")

    def test_csv_guard_neutralises_formulas(self):
        self.assertEqual(op.csv_cell("=SUM(A1:A9)"), "'=SUM(A1:A9)")
        self.assertEqual(op.csv_cell("@cmd"), "'@cmd")
        self.assertEqual(op.csv_cell("-- note"), "'-- note")

    def test_written_csv_round_trips_a_negative_benefit(self):
        result = op.analyse(load())
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.csv")
            op.write_csv(result, path)
            with open(path, encoding="utf-8", newline="") as fh:
                rows = {r["candidate_id"]: r for r in csv.DictReader(fh)}
        self.assertEqual(float(rows["OPP-RIS-02"]["benefit_hours_per_year_high"]), -11.0)
        self.assertEqual(rows["OPP-IAM-02"]["benefit_hours_per_year_low"], op.UNKNOWN)

    def test_output_is_deterministic(self):
        first = op.analyse(load())["content_digest"]
        second = op.analyse(load())["content_digest"]
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("sha256:"))

    def test_report_states_the_ledger_rule_and_the_fiction_notice(self):
        result = op.analyse(load())
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.md")
            op.write_markdown(result, path)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        self.assertIn("never summed", text)
        self.assertIn("FICTION", text.upper())
        self.assertIn("UNKNOWN", text)


class HostileInputTests(unittest.TestCase):

    def _write(self, doc):
        fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8")
        json.dump(doc, fh)
        fh.close()
        return fh.name

    def test_missing_required_field_is_reported_with_the_candidate_id(self):
        doc = load()
        del doc["candidates"][0]["dimensions"]
        path = self._write(doc)
        try:
            with self.assertRaises(op.PortfolioDataError) as ctx:
                op.load_portfolio(path)
            self.assertIn("OPP-ESS-01", str(ctx.exception))
            self.assertIn("dimensions", str(ctx.exception))
        finally:
            os.unlink(path)

    def test_duplicate_candidate_id_is_rejected(self):
        doc = load()
        doc["candidates"].append(dict(doc["candidates"][0]))
        path = self._write(doc)
        try:
            with self.assertRaises(op.PortfolioDataError):
                op.load_portfolio(path)
        finally:
            os.unlink(path)

    def test_inverted_range_is_rejected_rather_than_silently_sorted(self):
        doc = load()
        doc["candidates"][0]["inputs"]["one_time_implementation_hours"] = {
            "low": 80, "likely": 45, "high": 25}
        path = self._write(doc)
        try:
            op.load_portfolio(path)   # load only validates shape
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
            with self.assertRaises(op.PortfolioDataError):
                op.analyse(doc)
        finally:
            os.unlink(path)

    def test_non_numeric_estimate_is_rejected_not_coerced(self):
        doc = load()
        doc["candidates"][0]["inputs"]["rework_rate"] = {
            "low": "n/a", "likely": 0.2, "high": 0.3}
        path = self._write(doc)
        try:
            with self.assertRaises(op.PortfolioDataError):
                op.load_portfolio(path)
        finally:
            os.unlink(path)

    def test_wrong_schema_version_is_refused(self):
        doc = load()
        doc["schema_version"] = "something-else/9"
        path = self._write(doc)
        try:
            with self.assertRaises(op.PortfolioDataError):
                op.load_portfolio(path)
        finally:
            os.unlink(path)

    def test_candidate_with_no_measures_declared_is_unknown_not_low(self):
        """'measures' absent means nobody said. An empty list means somebody
        looked and there are none. Those are different and stay different."""
        self.assertEqual(op.measurability_level({}), op.UNKNOWN)
        self.assertEqual(op.measurability_level({"measures": []}), "LOW")

    def test_cli_reports_a_data_error_instead_of_crashing(self):
        doc = load()
        doc["candidates"][0]["inputs"]["volume_items_per_year"] = {"low": 1}
        path = self._write(doc)
        try:
            with tempfile.TemporaryDirectory() as d:
                code = op.main(["--candidates", path, "--out", d])
            self.assertEqual(code, 2)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
