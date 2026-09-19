"""Tests for the integrated AI decision case.

These assert behaviour, not shape. The ones that matter most are the hostile
cases: an unrecorded effort step, a document nobody accepted, a case not
labelled synthetic, a citation that resolves to nothing, and a quantity stated
with no citation at all. A kit that only passes on its own happy path has
proved nothing.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest

import ai_decision_case
import case as case_mod
import explain
import model
import sensitivity

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")


def fixture(name: str) -> str:
    return os.path.join(FIX, f"{name}.json")


def write_case(payload: dict) -> str:
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(payload, fh)
    fh.close()
    return fh.name


MINIMAL = {
    "case_id": "CASE-SYN-T", "synthetic": True, "workflow": "test (SYNTHETIC)",
    "assumptions": [
        {"id": "ASM-T-1", "name": "analyst_hourly_cost", "value": 80, "low": 80,
         "high": 80, "unit": "currency_per_hour", "basis": "ASSUMED", "source": "t"},
        {"id": "ASM-T-2", "name": "documents_per_month", "value": 10, "low": 10,
         "high": 10, "unit": "documents_per_month", "basis": "ASSUMED", "source": "t"},
        {"id": "ASM-T-3", "name": "evaluation_horizon_months", "value": 12, "low": 12,
         "high": 12, "unit": "months", "basis": "ASSUMED", "source": "t"}],
    "documents": [], "quality_measurements": [],
}


class TestTypes(unittest.TestCase):
    def test_unknown_refuses_arithmetic_by_name(self):
        """A missing measurement must not quietly become a number."""
        with self.assertRaises(model.UnknownError):
            model.UNKNOWN + 5
        with self.assertRaises(model.UnknownError):
            model.UNKNOWN * 2
        with self.assertRaises(model.UnknownError):
            _ = model.UNKNOWN > 0

    def test_units_cannot_be_combined(self):
        with self.assertRaises(model.UnitError):
            model.minutes(10) + model.money(10)
        self.assertEqual((model.minutes(10) + model.minutes(5)).amount, 15)

    def test_scaling_by_a_dimensionless_factor_is_allowed(self):
        self.assertEqual(model.minutes(10).scaled(3).amount, 30)


class TestLoader(unittest.TestCase):
    def test_rejects_case_not_marked_synthetic(self):
        payload = dict(MINIMAL, synthetic=False)
        with self.assertRaises(model.CaseLoadError):
            model.load_case(write_case(payload))

    def test_rejects_quality_measurement_citing_unknown_document(self):
        with self.assertRaises(model.CaseLoadError) as ctx:
            model.load_case(fixture("malformed_case"))
        self.assertIn("DOC-DOES-NOT-EXIST", str(ctx.exception))

    def test_rejects_unknown_event_kind(self):
        payload = dict(MINIMAL, documents=[
            {"id": "DOC-T-1", "variant": "BASELINE",
             "events": [{"id": "EVT-T-1", "kind": "TELEPATHY", "minutes": 5, "day": 1}]}])
        with self.assertRaises(model.CaseLoadError):
            model.load_case(write_case(payload))

    def test_rejects_duplicate_record_id(self):
        payload = dict(MINIMAL, documents=[
            {"id": "DOC-T-1", "variant": "BASELINE", "events": [
                {"id": "EVT-DUP", "kind": "AUTHOR", "minutes": 5, "day": 1},
                {"id": "EVT-DUP", "kind": "CHECK", "minutes": 5, "day": 1}]}])
        with self.assertRaises(model.CaseLoadError):
            model.load_case(write_case(payload))

    def test_rejects_assumption_value_outside_its_own_range(self):
        payload = json.loads(json.dumps(MINIMAL))
        payload["assumptions"][0]["value"] = 500
        with self.assertRaises(model.CaseLoadError):
            model.load_case(write_case(payload))

    def test_absent_minutes_loads_as_unknown_not_zero(self):
        payload = dict(MINIMAL, documents=[
            {"id": "DOC-T-1", "variant": "BASELINE", "events": [
                {"id": "EVT-T-1", "kind": "CHECK", "minutes": None, "day": 1}]}])
        loaded = model.load_case(write_case(payload))
        self.assertIs(loaded.documents[0].events[0].minutes, model.UNKNOWN)


class TestVerdicts(unittest.TestCase):
    def setUp(self):
        self.good = case_mod.decide(model.load_case(fixture("beneficial")))
        self.bad = case_mod.decide(model.load_case(fixture("unfavourable")))
        self.gap = case_mod.decide(model.load_case(fixture("undecidable")))

    def test_beneficial_case_is_beneficial(self):
        self.assertEqual(self.good.verdict, case_mod.BENEFICIAL)
        self.assertGreater(self.good.net_money_over_horizon[0], 0)

    def test_unfavourable_case_is_unfavourable(self):
        self.assertEqual(self.bad.verdict, case_mod.UNFAVOURABLE)
        self.assertLess(self.bad.net_money_over_horizon[1], 0)

    def test_the_losing_case_has_the_better_generation_headline(self):
        """The whole point of the order.

        If the workflow with the faster generation step always won, nobody
        would need a lifecycle model. This asserts the inversion is real and
        produced by the inputs, not by a penalty term.
        """
        self.assertGreater(self.bad.headline_ratio, self.good.headline_ratio)
        self.assertEqual(self.bad.verdict, case_mod.UNFAVOURABLE)
        self.assertEqual(self.good.verdict, case_mod.BENEFICIAL)

    def test_post_acceptance_effort_is_what_turns_it(self):
        assisted_post = self.bad.assisted.mean_component("post_accept")
        baseline_post = self.bad.baseline.mean_component("post_accept")
        self.assertGreater(assisted_post, baseline_post)
        self.assertGreater(assisted_post, 0)

    def test_undecidable_names_the_missing_record(self):
        self.assertEqual(self.gap.verdict, case_mod.UNDECIDABLE)
        joined = " ".join(self.gap.reasons)
        self.assertIn("EVT-D-A1-2", joined)
        self.assertIn("not zero minutes", joined)

    def test_undecidable_offers_no_numbers_at_all(self):
        self.assertFalse(model.is_known(self.gap.net_money_over_horizon[0]))
        self.assertFalse(model.is_known(self.gap.net_minutes_per_doc[1]))
        self.assertIsNone(self.gap.to_dict()["net_money_over_horizon"]["low"])

    def test_document_with_no_accept_event_is_a_gap_not_a_cheap_success(self):
        joined = " ".join(self.gap.reasons)
        self.assertIn("DOC-D-A2", joined)
        self.assertIn("no ACCEPT event", joined)

    def test_case_with_no_documents_is_undecidable(self):
        decision = case_mod.decide(model.load_case(write_case(MINIMAL)))
        self.assertEqual(decision.verdict, case_mod.UNDECIDABLE)
        self.assertTrue(any("nothing to compare" in r or "nothing to evaluate" in r
                            for r in decision.reasons))

    def test_money_interval_spans_every_assumption_corner(self):
        # net minutes 70..89; hourly 70..110; volume 18..30; horizon 12..12
        self.assertAlmostEqual(self.good.net_money_over_horizon[0],
                               70 / 60 * 70 * 18 * 12, places=6)
        self.assertAlmostEqual(self.good.net_money_over_horizon[1],
                               89 / 60 * 110 * 30 * 12, places=6)

    def test_quality_risk_is_reported_independently_of_the_money_verdict(self):
        self.assertTrue(self.bad.quality_risk)
        self.assertFalse(self.good.quality_risk)
        self.assertEqual(self.bad.assisted_quality.fabricated_references_total, 8)


class TestExplanationAudit(unittest.TestCase):
    def setUp(self):
        self.case = model.load_case(fixture("beneficial"))
        self.text = explain.render(self.case, case_mod.decide(self.case))

    def test_every_fixture_renders_a_fully_cited_explanation(self):
        for name in ("beneficial", "unfavourable", "undecidable"):
            c = model.load_case(fixture(name))
            text = explain.render(c, case_mod.decide(c))
            self.assertEqual(explain.audit_explanation(text, c), [],
                             f"{name} explanation failed its own citation audit")

    def test_audit_catches_a_quantity_with_no_citation(self):
        """The hostile case this whole layer exists for."""
        tampered = self.text + "\nAssisted drafting reduced effort by 45 percent.\n"
        problems = explain.audit_explanation(tampered, self.case)
        self.assertTrue(any(p.startswith("UNCITED_QUANTITY") for p in problems),
                        f"unsourced claim was not caught: {problems}")

    def test_audit_catches_a_citation_that_resolves_to_nothing(self):
        tampered = self.text + "\nEffort fell by 12 minutes [EVT-DOES-NOT-EXIST].\n"
        problems = explain.audit_explanation(tampered, self.case)
        self.assertTrue(any(p.startswith("DANGLING_CITATION") for p in problems),
                        f"dangling citation was not caught: {problems}")

    def test_citation_ids_do_not_themselves_count_as_the_quantity(self):
        """A line whose only digits live inside its citation is properly sourced."""
        line = "\nThe checking step was recorded. [EVT-B-A1-2]\n"
        self.assertEqual(explain.audit_explanation(self.text + line, self.case), [])

    def test_undecidable_explanation_states_no_figure(self):
        c = model.load_case(fixture("undecidable"))
        text = explain.render(c, case_mod.decide(c))
        self.assertIn("Still UNKNOWN", text)
        self.assertNotIn("x speed-up", text)


class TestSensitivity(unittest.TestCase):
    def setUp(self):
        self.case = model.load_case(fixture("beneficial"))

    def test_cost_assumptions_scale_but_cannot_flip_the_verdict(self):
        """Measured by re-running at each assumption's own bounds, not asserted."""
        rows = {r["assumption"]: r for r in sensitivity.classify_assumptions(self.case)}
        for name in ("analyst_hourly_cost", "documents_per_month",
                     "evaluation_horizon_months"):
            self.assertEqual(rows[name]["classification"], sensitivity.SCALES_ONLY)
            self.assertEqual(rows[name]["verdict_at_low"], case_mod.BENEFICIAL)
            self.assertEqual(rows[name]["verdict_at_high"], case_mod.BENEFICIAL)

    def test_break_even_margin_is_the_checking_tail(self):
        margin = sensitivity.find_verdict_flip(self.case)
        self.assertEqual(margin["nominal_verdict"], case_mod.BENEFICIAL)
        self.assertAlmostEqual(margin["flip_delta_minutes"], 70.0, delta=0.2)

    def test_unfavourable_case_has_a_thin_margin(self):
        bad = model.load_case(fixture("unfavourable"))
        margin = sensitivity.find_verdict_flip(bad)
        self.assertEqual(margin["nominal_verdict"], case_mod.UNFAVOURABLE)
        self.assertLess(abs(margin["flip_delta_minutes"]), 5.0)

    def test_undecidable_case_has_no_margin_to_measure(self):
        gap = model.load_case(fixture("undecidable"))
        margin = sensitivity.find_verdict_flip(gap)
        self.assertIsNone(margin["flip_delta_minutes"])

    def test_changed_assumption_flows_through_the_explanation(self):
        before = explain.render(self.case, case_mod.decide(self.case))
        moved = sensitivity.with_assumption(self.case, "analyst_hourly_cost", 40)
        after = explain.render(moved, case_mod.decide(moved))
        diff = sensitivity.explanation_diff(before, after)
        self.assertTrue(diff, "moving an assumption changed nothing in the explanation")
        self.assertTrue(any("40" in line for line in diff))

    def test_override_never_leaves_a_value_outside_its_declared_range(self):
        moved = sensitivity.with_assumption(self.case, "analyst_hourly_cost", 400)
        a = moved.assumption("analyst_hourly_cost")
        self.assertLessEqual(a.low, a.value)
        self.assertLessEqual(a.value, a.high)
        self.assertEqual(a.basis, "OVERRIDE")


class TestDeterminismAndCli(unittest.TestCase):
    def test_two_renders_are_byte_identical(self):
        c1 = model.load_case(fixture("unfavourable"))
        c2 = model.load_case(fixture("unfavourable"))
        self.assertEqual(explain.render(c1, case_mod.decide(c1)),
                         explain.render(c2, case_mod.decide(c2)))

    def test_cli_json_run_exits_zero_and_reports_audit_pass(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = ai_decision_case.main(
                ["--case", fixture("beneficial"), "--format", "json", "--sweep"])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["explanation_audit"]["passed"])
        self.assertEqual(payload["decision"]["verdict"], case_mod.BENEFICIAL)
        self.assertIn("assumption_classification", payload)

    def test_cli_reports_a_missing_case_file_instead_of_crashing(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = ai_decision_case.main(["--case", os.path.join(FIX, "nope.json")])
        self.assertEqual(code, 2)
        self.assertIn("could not load case", err.getvalue())

    def test_cli_undecidable_case_still_exits_zero_with_no_numbers(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = ai_decision_case.main(
                ["--case", fixture("undecidable"), "--format", "json"])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["decision"]["verdict"], case_mod.UNDECIDABLE)
        self.assertIsNone(payload["decision"]["headline_generation_speedup_x"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
