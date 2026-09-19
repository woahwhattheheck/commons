"""Tests for the base-fee economics model (UIOWA-003).

The claims this package makes, each turned into an assertion:

  "a missing estimate never becomes a zero"   -> blank vs 0 produce different results
  "margins are exact"                          -> Decimal cents, reconciliation to the fee
  "it reconciles to the commercial facts"      -> a wrong milestone is an ERROR
  "rates are assumptions"                      -> a rate claiming to be real is refused
  "sensitivity is real"                        -> the sweep changes the answer and says how
  "reproducible"                               -> render twice, compare bytes

Run:  python3 -m unittest -v test_cost_model
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from decimal import Decimal

import analyze
import cost_model
import money
import sensitivity
from money import UNKNOWN, is_unknown

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "base_fee_model.json")
RESOLUTION = {"WP5.correction_hours": {"low": 14, "expected": 22, "high": 40}}


def load_raw() -> dict:
    with open(FIXTURE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build() -> cost_model.Model:
    return cost_model.Model.from_json_file(FIXTURE)


class TestMoneyArithmetic(unittest.TestCase):
    def test_cents_are_exact(self):
        total = money.add(*[money.money("0.10")] * 10)
        self.assertEqual(total, Decimal("1.00"))
        self.assertEqual(money.fmt_money(total), "$1.00")

    def test_float_input_does_not_drift(self):
        self.assertEqual(money.money(1234.56), Decimal("1234.56"))
        self.assertEqual(money.money("$24,000.00"), Decimal("24000.00"))

    def test_negative_hours_refused(self):
        with self.assertRaises(ValueError):
            money.hours(-1)

    def test_unknown_is_not_zero_and_says_so(self):
        self.assertIsNot(UNKNOWN, 0)
        self.assertNotEqual(UNKNOWN, Decimal("0"))
        self.assertEqual(money.fmt_money(UNKNOWN), "UNKNOWN")

    def test_unknown_propagates_through_arithmetic(self):
        self.assertTrue(is_unknown(money.add(money.money("10"), UNKNOWN)))
        self.assertTrue(is_unknown(money.mul(UNKNOWN, Decimal("3"))))
        self.assertTrue(is_unknown(UNKNOWN + Decimal("5")))
        self.assertTrue(is_unknown(Decimal("5") - UNKNOWN))

    def test_unknown_refuses_to_be_truthy_or_compared(self):
        """The two ways an absent estimate sneaks in as a decision."""
        with self.assertRaises(TypeError):
            bool(UNKNOWN)
        with self.assertRaises(TypeError):
            UNKNOWN < Decimal("100")
        with self.assertRaises(TypeError):
            UNKNOWN >= Decimal("0")


class TestMissingEstimateIsNeverZero(unittest.TestCase):
    """The guardrail that matters most: a zero cost inflates margin."""

    def test_blank_and_zero_produce_different_results(self):
        zeroed = copy.deepcopy(load_raw())
        for case in cost_model.CASES:
            pkg = next(p for p in zeroed["packages"] if p["key"] == "WP5")
            pkg["effort"][case]["correction_hours"] = 0

        blank_model = build()                      # correction_hours is null
        zero_model = cost_model.Model(zeroed)      # correction_hours is 0

        blank = blank_model.case_summary("expected")
        zero = zero_model.case_summary("expected")

        self.assertTrue(is_unknown(blank["total_cost"]))
        self.assertFalse(is_unknown(zero["total_cost"]))
        self.assertTrue(is_unknown(blank["contribution_margin"]))
        self.assertFalse(is_unknown(zero["contribution_margin"]))
        self.assertEqual(blank_model.verdict("expected")["verdict"],
                         "LOSS_CERTAIN_DESPITE_UNKNOWNS")
        self.assertEqual(zero_model.verdict("expected")["verdict"], "MARGIN_COMPUTED")

    def test_treating_the_gap_as_zero_would_overstate_margin(self):
        """Shows the direction of the error, which is why it matters."""
        zeroed = copy.deepcopy(load_raw())
        for case in cost_model.CASES:
            pkg = next(p for p in zeroed["packages"] if p["key"] == "WP5")
            pkg["effort"][case]["correction_hours"] = 0
        zero_margin = cost_model.Model(zeroed).case_summary("expected")["contribution_margin"]
        real_margin = build().resolve(RESOLUTION).case_summary("expected")["contribution_margin"]
        self.assertGreater(zero_margin, real_margin,
                           "zeroing a missing cost should flatter the margin; if it does not, "
                           "this test is no longer demonstrating the hazard")

    def test_empty_string_is_refused_rather_than_guessed(self):
        raw = copy.deepcopy(load_raw())
        pkg = next(p for p in raw["packages"] if p["key"] == "WP1")
        pkg["effort"]["expected"]["production_hours"] = "   "
        with self.assertRaises(cost_model.ModelError) as ctx:
            cost_model.Model(raw)
        self.assertIn("too easy to read as zero", str(ctx.exception))

    def test_an_unknown_package_is_excluded_not_counted_low(self):
        s = build().case_summary("expected")
        self.assertEqual(s["incomplete_packages"], ["WP5"])
        self.assertFalse(s["computable"])
        # the floor counts only the four costable packages
        rows = [r for r in s["rows"] if not is_unknown(r["total"])]
        self.assertEqual(len(rows), 4)
        self.assertEqual(s["known_subtotal"], money.add(*[r["total"] for r in rows]))


class TestReasoningUnderPartialInformation(unittest.TestCase):
    """A missing estimate does not always mean nothing can be concluded."""

    def test_a_floor_above_revenue_proves_a_loss(self):
        m = build()
        v = m.verdict("expected")
        self.assertEqual(v["verdict"], "LOSS_CERTAIN_DESPITE_UNKNOWNS")
        self.assertGreater(v["floor_cost"], m.base_fee)
        self.assertEqual(v["minimum_loss"], v["floor_cost"] - m.base_fee)
        self.assertTrue(is_unknown(v["margin"]),
                        "the exact margin is still unknown; only its sign is known")
        self.assertIn("can only add cost", v["explanation"])

    def test_a_floor_below_revenue_stays_undecided(self):
        m = build()
        v = m.verdict("low")
        self.assertEqual(v["verdict"], "NOT_COMPUTABLE")
        self.assertLess(v["floor_cost"], m.base_fee)
        self.assertTrue(is_unknown(v["margin"]))
        self.assertIn("would be a guess", v["explanation"])

    def test_resolving_the_unknown_completes_the_model(self):
        r = build().resolve(RESOLUTION)
        for case in cost_model.CASES:
            self.assertEqual(r.verdict(case)["verdict"], "MARGIN_COMPUTED")
            self.assertFalse(is_unknown(r.case_summary(case)["contribution_margin"]))
        self.assertEqual(r.resolved_targets, ("WP5.correction_hours",))

    def test_verdicts_are_from_the_declared_set(self):
        m = build()
        for case in cost_model.CASES:
            self.assertIn(m.verdict(case)["verdict"], cost_model.Model.VERDICTS)

    def test_resolution_cannot_overwrite_a_real_estimate(self):
        with self.assertRaises(cost_model.ModelError) as ctx:
            build().resolve({"WP1.production_hours": {"low": 1, "expected": 2, "high": 3}})
        self.assertIn("already has an estimate", str(ctx.exception))

    def test_partial_resolution_is_refused(self):
        with self.assertRaises(cost_model.ModelError) as ctx:
            build().resolve({"WP5.correction_hours": {"expected": 22}})
        self.assertIn("all three cases", str(ctx.exception))

    def test_resolution_targets_are_validated(self):
        for bad in ({"WP9.correction_hours": {"low": 1, "expected": 2, "high": 3}},
                    {"WP5.magic_hours": {"low": 1, "expected": 2, "high": 3}},
                    {"nonsense": {"low": 1, "expected": 2, "high": 3}}):
            with self.assertRaises(cost_model.ModelError):
                build().resolve(bad)


class TestReconciliation(unittest.TestCase):
    """The quoted commercial facts are inputs; disagreeing is an error."""

    def test_the_supplied_model_reconciles(self):
        m = build()
        self.assertEqual(m.errors, [])
        self.assertEqual(m.base_fee, Decimal("24000.00"))
        self.assertEqual(money.add(*[x["amount"] for x in m.milestones]), m.base_fee)

    def test_milestone_shares_are_40_40_20(self):
        m = build()
        self.assertEqual([x["share_pct"] for x in m.milestones],
                         [Decimal("40"), Decimal("40"), Decimal("20")])
        self.assertEqual([x["amount"] for x in m.milestones],
                         [Decimal("9600.00"), Decimal("9600.00"), Decimal("4800.00")])

    def test_a_milestone_that_does_not_sum_is_an_error(self):
        raw = copy.deepcopy(load_raw())
        raw["commercial"]["milestones"][0]["amount"] = "9000.00"
        errors = cost_model.Model(raw).errors
        self.assertTrue(errors)
        self.assertTrue(any("but the base fee is" in e for e in errors))

    def test_a_share_that_is_not_its_amount_is_an_error(self):
        raw = copy.deepcopy(load_raw())
        raw["commercial"]["milestones"][0]["share_pct"] = 50
        raw["commercial"]["milestones"][2]["share_pct"] = 10
        errors = cost_model.Model(raw).errors
        self.assertTrue(any("is not" in e and "% of the base fee" in e for e in errors))

    def test_a_package_billing_to_an_unknown_milestone_is_an_error(self):
        raw = copy.deepcopy(load_raw())
        raw["packages"][0]["milestone"] = "M9"
        self.assertTrue(any("unknown milestone" in e for e in cost_model.Model(raw).errors))

    def test_cli_check_exits_nonzero_on_a_broken_reconciliation(self):
        raw = copy.deepcopy(load_raw())
        raw["commercial"]["milestones"][0]["amount"] = "1.00"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "broken.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(raw, fh)
            self.assertEqual(analyze.main(["--data", path, "--check"]), 1)


class TestRatesAreAssumptions(unittest.TestCase):
    def test_every_rate_declares_an_assumed_basis(self):
        for rate in build().rates.values():
            self.assertIn(rate.basis, ("ASSUMED", "SYNTHETIC-FIXTURE"))

    def test_a_rate_claiming_to_be_real_is_refused(self):
        """Quoting a margin off an invented rate card is the live hazard."""
        for claim in ("AGREED", "CONTRACTUAL", "OBSERVED", "UNIVERSITY-EVIDENCE"):
            raw = copy.deepcopy(load_raw())
            raw["rates"]["production"]["basis"] = claim
            with self.assertRaises(cost_model.ModelError) as ctx:
                cost_model.Model(raw)
            self.assertIn("no agreed rate card", str(ctx.exception))

    def test_rate_assignment_must_point_somewhere_real(self):
        raw = copy.deepcopy(load_raw())
        raw["rate_assignment"]["review_hours"] = "imaginary"
        with self.assertRaises(cost_model.ModelError) as ctx:
            cost_model.Model(raw)
        self.assertIn("unknown rate", str(ctx.exception))

    def test_blended_rate_is_weighted_by_hours_not_a_plain_average(self):
        r = build().resolve(RESOLUTION)
        blended = r.blended_rate()
        plain = sum(x.amount for x in r.rates.values()) / len(r.rates)
        self.assertNotEqual(blended, plain.quantize(money.CENT))
        # must sit inside the range of the card
        self.assertGreater(blended, min(x.amount for x in r.rates.values()))
        self.assertLess(blended, max(x.amount for x in r.rates.values()))


class TestSensitivity(unittest.TestCase):
    def test_the_sweep_actually_moves_the_answer(self):
        r = build().resolve(RESOLUTION)
        sw = sensitivity.sweep(r)
        self.assertEqual(sw["counts"]["total"], 15)
        margins = {s["margin"] for s in sw["scenarios"]}
        self.assertGreater(len(margins), 1, "a sweep that changes nothing is not a sweep")

    def test_a_corner_result_is_labelled_as_one(self):
        r = build().resolve(RESOLUTION)
        sw = sensitivity.sweep(r)
        self.assertTrue(sw["profitable_only_at_optimistic_corner"])
        self.assertIn("corner result, not a margin", sw["conclusion"])

    def test_unresolved_model_reports_certain_losses_separately(self):
        sw = sensitivity.sweep(build())
        self.assertEqual(sw["counts"]["profitable"], 0)
        self.assertGreater(sw["counts"]["loss_certain"], 0)
        self.assertGreater(sw["counts"]["not_computable"], 0)
        self.assertEqual(sw["counts"]["loss_certain"] + sw["counts"]["not_computable"],
                         sw["counts"]["total"])

    def test_rate_breakeven_finds_the_flip_point(self):
        r = build().resolve(RESOLUTION)
        flip = sensitivity.rate_breakeven(r, "expected", "production")
        self.assertIn("flips_at_amount", flip)
        self.assertLess(flip["flips_at_amount"], r.rates["production"].amount)
        # verify it really is the flip point, by evaluating either side
        below = sensitivity._scaled(r, flip["flips_at_factor"] - Decimal("0.05"))
        above = sensitivity._scaled(r, flip["flips_at_factor"] + Decimal("0.05"))
        self.assertGreater(below.case_summary("expected")["contribution_margin"], 0)
        self.assertLess(above.case_summary("expected")["contribution_margin"], 0)

    def test_rate_breakeven_refuses_when_an_estimate_is_missing(self):
        flip = sensitivity.rate_breakeven(build(), "expected", "production")
        self.assertTrue(is_unknown(flip["flips_at"]))
        self.assertIn("Resolve", flip["reason"])

    def test_unknown_rate_key_is_refused(self):
        with self.assertRaises(KeyError):
            sensitivity.rate_breakeven(build(), "expected", "nonexistent")


class TestBreakEven(unittest.TestCase):
    def test_break_even_hours_are_computed_when_possible(self):
        r = build().resolve(RESOLUTION)
        be = r.break_even_hours("expected")
        self.assertFalse(is_unknown(be["break_even_hours"]))
        self.assertLess(be["break_even_hours"], be["planned_hours"],
                        "this fixture is modelled as over-committed at the expected case")
        self.assertEqual(be["headroom_hours"],
                         be["break_even_hours"] - be["planned_hours"])

    def test_break_even_refuses_on_an_incomplete_model(self):
        be = build().break_even_hours("expected")
        self.assertTrue(is_unknown(be["break_even_hours"]))
        self.assertTrue(is_unknown(be["headroom_hours"]))
        self.assertIn("missing", be["reason"])


class TestHostileAndMissingInput(unittest.TestCase):
    def _expect(self, mutate, fragment):
        raw = copy.deepcopy(load_raw())
        mutate(raw)
        with self.assertRaises(cost_model.ModelError) as ctx:
            cost_model.Model(raw)
        self.assertIn(fragment, str(ctx.exception))

    def test_a_missing_effort_case_is_refused(self):
        def mutate(raw):
            del raw["packages"][0]["effort"]["high"]
        self._expect(mutate, "a single-point estimate hides the range")

    def test_unordered_low_expected_high_is_refused(self):
        def mutate(raw):
            raw["packages"][0]["effort"]["low"]["production_hours"] = 999
        self._expect(mutate, "not ordered low <= expected <= high")

    def test_duplicate_package_key_refused(self):
        def mutate(raw):
            raw["packages"].append(copy.deepcopy(raw["packages"][0]))
        self._expect(mutate, "duplicate package key")

    def test_no_packages_refused(self):
        self._expect(lambda raw: raw.update(packages=[]), "no work packages supplied")

    def test_negative_overhead_refused(self):
        self._expect(lambda raw: raw["overheads"].update(contingency_pct=-5),
                     "cannot be negative")

    def test_garbage_hours_refused(self):
        def mutate(raw):
            raw["packages"][0]["effort"]["expected"]["production_hours"] = "about forty"
        self._expect(mutate, "not a valid hours figure")

    def test_missing_required_block_refused(self):
        self._expect(lambda raw: raw.pop("commercial"), "missing required field")

    def test_malformed_json_is_rejected_with_the_path(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("{ nope ")
            path = fh.name
        try:
            with self.assertRaises(cost_model.ModelError) as ctx:
                cost_model.Model.from_json_file(path)
            self.assertIn("not valid JSON", str(ctx.exception))
        finally:
            os.unlink(path)

    def test_cli_rejects_bad_data_with_exit_code_2(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"title": "x"}, fh)
            self.assertEqual(analyze.main(["--data", path, "--out", d]), 2)

    def test_cli_reports_a_missing_file(self):
        self.assertEqual(analyze.main(["--data", "/nonexistent.json", "--out", "/tmp"]), 2)


class TestOutputAndReproducibility(unittest.TestCase):
    def test_render_is_byte_identical_across_runs(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            self.assertEqual(analyze.main(["--data", FIXTURE, "--out", d1]), 0)
            self.assertEqual(analyze.main(["--data", FIXTURE, "--out", d2]), 0)
            for name in sorted(os.listdir(d1)):
                with open(os.path.join(d1, name), "rb") as a, \
                     open(os.path.join(d2, name), "rb") as b:
                    self.assertEqual(a.read(), b.read(), name)

    def test_the_workbook_prints_unknown_rather_than_a_number(self):
        md = analyze.full_markdown(build())
        self.assertIn("UNKNOWN", md)
        self.assertIn("LOSS_CERTAIN_DESPITE_UNKNOWNS", md)
        self.assertIn("No margin is reported for this case", md)

    def test_every_rate_in_the_workbook_is_marked_assumed(self):
        md = analyze.full_markdown(build())
        self.assertIn("`ASSUMED`", md)
        self.assertIn("not an agreed or observed value", md)

    def test_csv_writes_the_word_unknown_not_an_empty_cell(self):
        csv = analyze.package_csv(build())
        wp5 = [line for line in csv.splitlines() if line.startswith("WP5,")]
        self.assertEqual(len(wp5), 3)
        for line in wp5:
            self.assertIn("UNKNOWN", line)
            self.assertNotIn(",,", line, "an empty cell reads as zero in a spreadsheet")

    def test_json_is_machine_readable_and_keeps_unknown(self):
        payload = json.loads(analyze.model_json(build()))
        self.assertEqual(payload["cases"]["expected"]["total_cost"], "UNKNOWN")
        self.assertEqual(payload["cases"]["expected"]["verdict"],
                         "LOSS_CERTAIN_DESPITE_UNKNOWNS")
        self.assertEqual(payload["commercial"]["base_fee"], "24000.00")
        for rate in payload["assumptions"]["rates"].values():
            self.assertEqual(rate["basis"], "ASSUMED")

    def test_no_certification_or_maturity_language_anywhere(self):
        blob = analyze.full_markdown(build()).lower()
        for forbidden in ("maturity", "certified", "compliant", "percentile", "benchmark score"):
            self.assertNotIn(forbidden, blob, f"unsupported claim: {forbidden}")

    def test_fiction_is_labelled_in_every_artifact(self):
        m = build()
        self.assertIn("SYNTHETIC", analyze.full_markdown(m))
        self.assertIn("SYNTHETIC", analyze.model_json(m))
        self.assertIn("ASSUMPTION", m.disclaimer.upper())


if __name__ == "__main__":
    unittest.main(verbosity=2)
