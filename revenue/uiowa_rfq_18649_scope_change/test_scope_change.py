#!/usr/bin/env python3
"""Regression tests for the scope-change impact calculator.

Organized around the distinctions the work order says must hold:

* `DefectVersusAddedWorkTests` -- correcting an in-scope deliverable defect must
  stay distinguishable from added work. This is the hard requirement.
* `NotQuotableTests`           -- some requests have no price at any effort.
* `MissingEstimateTests`       -- an unestimated task is not zero hours.
* `MoneyTests`                 -- integer cents, exact reconciliation, no floats.
* `BaselineIntegrityTests`     -- no scenario moves the $24,000 base.
* `HostileInputTests`          -- malformed input is refused by name.

Run:  python3 -m unittest -v test_scope_change.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

import scope_change
from scope_change import (
    CHANGE_QUOTE,
    NEEDS_INPUT,
    NOT_QUOTABLE,
    NO_CHARGE_CURE,
    UNKNOWN,
    Baseline,
    ChangeRequest,
    ScopeChangeError,
    cents_to_dollars,
    dollars_to_cents,
    evaluate,
    load_requests,
    quote,
    read_json,
    render_markdown,
    sweep_assumption,
    to_csv_rows,
)

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE_FIXTURE = os.path.join(HERE, "fixtures", "baseline.json")
REQUESTS_FIXTURE = os.path.join(HERE, "fixtures", "change_requests.json")


def baseline_payload():
    return read_json(BASELINE_FIXTURE)


def baseline():
    return Baseline(baseline_payload())


def make_request(request_id="CR-T-001", **overrides):
    payload = {
        "request_id": request_id,
        "title": "test request",
        "basis": "added_scope",
        "summary": "",
        "work_items": [
            {"task": "do the thing", "role": "assessment_engineer", "hours": 10}
        ],
        "dependencies": [],
        "schedule_effect": {"calendar_days_added": 1, "on_critical_path": False},
    }
    payload.update(overrides)
    return payload


def one(payload, base=None):
    return quote(ChangeRequest(payload), base or baseline())


# ---------------------------------------------------------------------------
# The hard requirement
# ---------------------------------------------------------------------------


class DefectVersusAddedWorkTests(unittest.TestCase):
    """A correction of our own nonconformance is never added work."""

    def test_defect_cure_is_zero_fee_but_not_zero_hours(self):
        """The single most important assertion in this suite.

        Both halves matter. Zero fee, because billing the buyer to fix a
        deliverable that failed an agreed criterion is charging for our own
        defect. Non-zero hours, because the work is real and costs time --
        reporting it as zero effort would hide it from anyone trying to see what
        corrections are costing.
        """
        record = one(
            make_request(
                basis="deliverable_defect",
                failed_criterion="every unassessed cell states the reason it is on HOLD",
                work_items=[
                    {"task": "fix it", "role": "assessment_engineer", "hours": 5},
                    {"task": "reissue", "role": "assessment_engineer", "hours": 2},
                ],
            )
        )
        self.assertEqual(record["disposition"], NO_CHARGE_CURE)
        self.assertEqual(record["fee_cents"], 0)
        self.assertEqual(record["fee"], "$0.00")
        self.assertEqual(record["hours_estimated"], 7)
        self.assertGreater(record["hours_estimated"], 0)
        # The internal cost is tracked, and clearly marked as not a charge.
        self.assertEqual(record["internal_cost_cents"], 7 * 150 * 100)
        self.assertIn("not a charge", record["internal_cost_note"])
        self.assertIn("not billed", record["fee_basis"])

    def test_identical_work_is_billable_as_added_scope_and_free_as_a_cure(self):
        """Same hours, same roles. The grounds decide, and only the grounds."""
        work = [{"task": "same work", "role": "assessment_engineer", "hours": 6}]
        added = one(make_request("CR-T-ADD", basis="added_scope", work_items=work))
        cure = one(
            make_request(
                "CR-T-CURE",
                basis="deliverable_defect",
                failed_criterion="the draft matrix covers all twelve cells",
                work_items=work,
            )
        )
        self.assertEqual(added["hours_estimated"], cure["hours_estimated"])
        self.assertEqual(added["disposition"], CHANGE_QUOTE)
        self.assertEqual(cure["disposition"], NO_CHARGE_CURE)
        self.assertGreater(added["fee_cents"], 0)
        self.assertEqual(cure["fee_cents"], 0)

    def test_wording_does_not_move_a_cure_into_billable_work(self):
        """Titles and summaries are not inputs to the disposition.

        A cure described in the language of new work is still a cure. This is the
        pressure a real engagement applies, so it is the one the code refuses to
        feel.
        """
        record = one(
            make_request(
                basis="deliverable_defect",
                failed_criterion="the draft matrix covers all twelve cells",
                title="ADDITIONAL WORK: substantial new analysis effort required",
                summary="This is new scope and should be treated as a change order.",
            )
        )
        self.assertEqual(record["disposition"], NO_CHARGE_CURE)
        self.assertEqual(record["fee_cents"], 0)

    def test_cure_raised_during_acceptance_review_is_still_a_cure(self):
        """Timing is not a reclassification lever.

        The exhibit says a correction is not a new scope item "merely because it
        occurs during acceptance review", so the cure path carries no date or
        phase condition at all.
        """
        record = one(
            make_request(
                basis="deliverable_defect",
                failed_criterion="every unassessed cell states the reason it is on HOLD",
                requested_by="prime, during acceptance review",
            )
        )
        self.assertEqual(record["disposition"], NO_CHARGE_CURE)
        self.assertIn("acceptance review", record["fee_basis"])

    def test_unsubstantiated_defect_claim_is_neither_free_nor_billable(self):
        """A vague complaint stops and asks.

        Defaulting to free absorbs unlimited rework. Defaulting to billable
        charges for what may be our own defect. Neither is acceptable, so the
        request is held until somebody names the criterion.
        """
        record = one(
            make_request(
                basis="deliverable_defect",
                summary="the findings don't read right",
            )
        )
        self.assertEqual(record["disposition"], NEEDS_INPUT)
        self.assertIsNone(record["fee_cents"])
        self.assertEqual(record["fee"], "UNKNOWN")
        self.assertNotEqual(record["fee"], "$0.00")
        self.assertEqual(record["missing_inputs"], ["failed_criterion"])
        self.assertIn("guessing in either direction", record["fee_basis"])

    def test_cures_contribute_nothing_to_the_buyer_facing_total(self):
        requests = load_requests(read_json(REQUESTS_FIXTURE))
        result = evaluate(requests, baseline())
        cures = [q for q in result["quotes"] if q["disposition"] == NO_CHARGE_CURE]
        self.assertTrue(cures, "fixture must contain a cure")
        self.assertEqual(result["totals"]["no_charge_cure_fee"], "$0.00")
        # The quoted-change total is exactly the sum of the CHANGE_QUOTE fees,
        # so no cure cost can have leaked into it.
        quoted = [q for q in result["quotes"] if q["disposition"] == CHANGE_QUOTE]
        self.assertEqual(
            result["totals"]["quoted_changes_cents"],
            sum(q["fee_cents"] for q in quoted),
        )
        self.assertTrue(result["integrity"]["cures_are_all_zero_fee"])

    def test_cure_hours_are_reported_separately_and_are_not_lost(self):
        requests = load_requests(read_json(REQUESTS_FIXTURE))
        result = evaluate(requests, baseline())
        self.assertEqual(result["hours"]["no_charge_cure_hours"], 7)
        self.assertGreater(result["hours"]["quoted_change_hours"], 0)
        # Correction hours are not folded into the billable hours figure.
        self.assertNotEqual(
            result["hours"]["quoted_change_hours"],
            result["hours"]["quoted_change_hours"]
            + result["hours"]["no_charge_cure_hours"],
        )

    def test_no_rate_makes_a_cure_billable(self):
        """Zero by policy, not by arithmetic."""
        sweep = sweep_assumption(
            load_requests(read_json(REQUESTS_FIXTURE)),
            baseline_payload(),
            role="assessment_engineer",
            multipliers=(0.5, 1.0, 4.0, 100.0),
        )
        self.assertTrue(sweep["cures_stay_zero"])
        self.assertTrue(sweep["changes_move"], "quotes must respond to the rate")
        for row in sweep["rows"]:
            self.assertEqual(row["no_charge_cure_fee"], "$0.00")

    def test_markdown_separates_the_two_categories_by_heading(self):
        requests = load_requests(read_json(REQUESTS_FIXTURE))
        text = render_markdown(evaluate(requests, baseline()))
        self.assertIn("## Separately priced changes", text)
        self.assertIn("## No-charge corrections (not added work)", text)
        self.assertIn("**Charge to the buyer: $0.00**", text)


# ---------------------------------------------------------------------------
# Not quotable
# ---------------------------------------------------------------------------


class NotQuotableTests(unittest.TestCase):
    """Some requests are outside the solicitation, not merely expensive."""

    def test_excluded_request_gets_no_fee_however_large_the_effort(self):
        for hours in (1, 40, 4000):
            with self.subTest(hours=hours):
                record = one(
                    make_request(
                        basis="excluded_by_solicitation",
                        exclusion_reference="ACCEPTANCE_EXHIBIT.md section 7",
                        work_items=[
                            {
                                "task": "market scan",
                                "role": "assessment_engineer",
                                "hours": hours,
                            }
                        ],
                    )
                )
                self.assertEqual(record["disposition"], NOT_QUOTABLE)
                self.assertIsNone(record["fee_cents"])
                self.assertEqual(record["fee"], "NOT QUOTED")
                self.assertNotEqual(record["fee"], "$0.00")

    def test_exclusion_is_checked_before_effort_is_priced(self):
        """Order of operations is the policy: no price is ever computed."""
        record = one(
            make_request(
                basis="excluded_by_solicitation",
                exclusion_reference="ACCEPTANCE_EXHIBIT.md section 7",
            )
        )
        self.assertNotIn("labour_subtotal_cents", record)
        self.assertNotIn("computed_fee_cents", record)

    def test_effort_is_still_shown_so_the_refusal_is_not_a_brush_off(self):
        record = one(
            make_request(
                basis="excluded_by_solicitation",
                exclusion_reference="ACCEPTANCE_EXHIBIT.md section 7",
                work_items=[
                    {"task": "scan", "role": "assessment_engineer", "hours": 30},
                    {"task": "memo", "role": "lead_reviewer", "hours": 10},
                ],
            )
        )
        self.assertEqual(record["hours_estimated"], 40)
        self.assertIn("not for sale at any price", record["fee_basis"])
        self.assertIn("amendment", record["fee_basis"])

    def test_refusals_carry_no_fee_across_the_whole_worksheet(self):
        result = evaluate(load_requests(read_json(REQUESTS_FIXTURE)), baseline())
        self.assertTrue(result["integrity"]["refusals_carry_no_fee"])
        self.assertEqual(result["totals"]["not_quotable_count"], 1)


# ---------------------------------------------------------------------------
# Missing estimates
# ---------------------------------------------------------------------------


class MissingEstimateTests(unittest.TestCase):
    """An unestimated task is an open question, not zero effort."""

    def test_missing_hours_blocks_the_quote_rather_than_pricing_around_it(self):
        record = one(
            make_request(
                work_items=[
                    {"task": "known", "role": "assessment_engineer", "hours": 10},
                    {"task": "unknown", "role": "assessment_engineer"},
                ]
            )
        )
        self.assertEqual(record["disposition"], NEEDS_INPUT)
        self.assertIsNone(record["fee_cents"])
        self.assertEqual(record["fee"], "UNKNOWN")
        self.assertEqual(record["hours_unestimated_tasks"], ["unknown"])
        # The known part is still reported: the gap is one line, not the request.
        self.assertEqual(record["hours_estimated"], 10)

    def test_every_spelling_of_missing_is_unknown(self):
        for value in (None, "", "UNKNOWN", "tbd", "n/a", "?"):
            with self.subTest(value=value):
                record = one(
                    make_request(
                        work_items=[
                            {
                                "task": "t",
                                "role": "assessment_engineer",
                                "hours": value,
                            }
                        ]
                    )
                )
                self.assertEqual(record["disposition"], NEEDS_INPUT)
                self.assertIsNone(record["fee_cents"])

    def test_unestimated_line_is_not_priced_at_zero(self):
        record = one(
            make_request(
                work_items=[{"task": "t", "role": "assessment_engineer"}]
            )
        )
        line = record["work_items"][0]
        self.assertIsNone(line["hours"])
        self.assertIsNone(line["cost_cents"])
        self.assertEqual(line["cost"], "UNKNOWN")
        self.assertNotEqual(line["cost"], "$0.00")
        self.assertIn("Not priced at zero", line["arithmetic"])

    def test_unknown_sentinel_has_no_arithmetic(self):
        with self.assertRaises(TypeError):
            UNKNOWN * 2  # type: ignore[operator]
        with self.assertRaises(ScopeChangeError):
            bool(UNKNOWN)

    def test_unestimated_schedule_stays_unknown_not_zero_days(self):
        record = one(
            make_request(schedule_effect={"calendar_days_added": None})
        )
        self.assertIsNone(record["schedule_effect"]["calendar_days_added"])
        rows = to_csv_rows({"quotes": [record]})
        days_col = rows[0].index("calendar_days_added")
        self.assertEqual(rows[1][days_col], "UNKNOWN")
        self.assertNotEqual(rows[1][days_col], "0")


# ---------------------------------------------------------------------------
# Money
# ---------------------------------------------------------------------------


class MoneyTests(unittest.TestCase):
    """Integer cents, exact reconciliation, no floating-point dollars."""

    def test_every_quote_reconciles_to_the_cent(self):
        result = evaluate(load_requests(read_json(REQUESTS_FIXTURE)), baseline())
        self.assertTrue(result["integrity"]["all_quotes_reconcile"])
        for record in result["quotes"]:
            if record["disposition"] != CHANGE_QUOTE:
                continue
            if record.get("price_source") == "PUBLISHED":
                continue
            line_total = sum(
                line["cost_cents"]
                for line in record["work_items"]
                if line["cost_cents"] is not None
            )
            self.assertEqual(
                record["fee_cents"],
                line_total + record["coordination_overhead_cents"],
                f"{record['request_id']} does not reconcile",
            )

    def test_float_money_is_refused(self):
        """A float dollar amount in a quotation is a defect, not a convenience."""
        with self.assertRaises(ScopeChangeError) as ctx:
            dollars_to_cents(187.5, field="rate")
        self.assertIn("float", str(ctx.exception))

    def test_decimal_strings_are_exact(self):
        self.assertEqual(dollars_to_cents("187.50", field="r"), 18750)
        self.assertEqual(dollars_to_cents("0.01", field="r"), 1)
        self.assertEqual(dollars_to_cents("$1,234.56", field="r"), 123456)
        self.assertEqual(dollars_to_cents(24000, field="r"), 2400000)

    def test_sub_cent_precision_is_refused(self):
        with self.assertRaises(ScopeChangeError) as ctx:
            dollars_to_cents("1.005", field="r")
        self.assertIn("sub-cent", str(ctx.exception))

    def test_unknown_money_never_renders_as_zero(self):
        self.assertEqual(cents_to_dollars(None), "UNKNOWN")
        self.assertEqual(cents_to_dollars(0), "$0.00")
        self.assertNotEqual(cents_to_dollars(None), cents_to_dollars(0))

    def test_a_published_price_governs_and_the_delta_is_disclosed(self):
        record = one(
            make_request(
                published_price=4000,
                published_price_ref="exhibit section 4.4",
                work_items=[
                    {"task": "prep", "role": "lead_reviewer", "hours": 10},
                    {"task": "deliver", "role": "lead_reviewer", "hours": 4},
                    {"task": "capture", "role": "evidence_analyst", "hours": 4},
                ],
            )
        )
        self.assertEqual(record["disposition"], CHANGE_QUOTE)
        self.assertEqual(record["price_source"], "PUBLISHED")
        self.assertEqual(record["fee_cents"], 400000)
        # Computed bottom-up: 14h x $195 + 4h x $120 = $3,210, +8% = $3,466.80
        self.assertEqual(record["computed_fee_cents"], 346680)
        self.assertEqual(record["computed_vs_published_delta_cents"], 346680 - 400000)
        self.assertIn("contradicting itself", record["fee_basis"])

    def test_non_committable_costs_are_excluded_from_the_fee(self):
        record = one(
            make_request(
                work_items=[
                    {"task": "onsite", "role": "lead_reviewer", "hours": 8}
                ],
                non_committable_costs=[
                    {"item": "Travel", "reason": "excluded by COMMERCIAL.md"}
                ],
            )
        )
        # The fee is exactly the labour plus overhead -- travel adds nothing.
        self.assertEqual(record["fee_cents"], round(8 * 19500 * 1.08))
        self.assertEqual(len(record["non_committable_costs"]), 1)
        self.assertTrue(record["non_committable_costs"][0]["excluded_from_fee"])

    def test_csv_marks_the_zero_fee_as_policy_not_arithmetic(self):
        result = evaluate(load_requests(read_json(REQUESTS_FIXTURE)), baseline())
        rows = to_csv_rows(result)
        header = rows[0]
        disp = header.index("disposition")
        fee = header.index("fee")
        flag = header.index("fee_is_zero_by_policy")
        hours = header.index("hours_estimated")
        seen = {"cure": 0, "refused": 0, "blocked": 0}
        for row in rows[1:]:
            if row[disp] == NO_CHARGE_CURE:
                seen["cure"] += 1
                self.assertEqual(row[fee], "$0.00")
                self.assertEqual(row[flag], "YES")
                # Hours must survive into the spreadsheet.
                self.assertNotEqual(row[hours], "0")
                self.assertNotEqual(row[hours], "")
            elif row[disp] == NOT_QUOTABLE:
                seen["refused"] += 1
                self.assertEqual(row[fee], "NOT QUOTED")
                self.assertEqual(row[flag], "NO")
            elif row[disp] == NEEDS_INPUT:
                seen["blocked"] += 1
                self.assertEqual(row[fee], "UNKNOWN")
                self.assertEqual(row[flag], "NO")
        self.assertEqual(seen, {"cure": 1, "refused": 1, "blocked": 2})
        self.assertEqual(len(rows) - 1, 8)


# ---------------------------------------------------------------------------
# Baseline integrity
# ---------------------------------------------------------------------------


class BaselineIntegrityTests(unittest.TestCase):
    """No scenario moves the proposed baseline."""

    def test_baseline_is_unchanged_by_every_scenario(self):
        base = baseline()
        before = base.to_public_dict()
        result = evaluate(load_requests(read_json(REQUESTS_FIXTURE)), base)
        self.assertEqual(result["totals"]["baseline_base_fee"], "$24,000.00")
        self.assertEqual(result["totals"]["baseline_base_fee_cents"], 2400000)
        self.assertTrue(result["totals"]["baseline_unchanged"])
        self.assertEqual(base.to_public_dict(), before)
        # Milestones still 40/40/20 of the unchanged base.
        amounts = [m["amount"] for m in result["baseline"]["milestones"]]
        self.assertEqual(amounts, ["$9,600.00", "$9,600.00", "$4,800.00"])

    def test_milestones_must_reconcile_to_the_base_fee(self):
        payload = baseline_payload()
        payload["commercial"]["milestones"][0]["amount"] = 9999
        with self.assertRaises(ScopeChangeError) as ctx:
            Baseline(payload)
        self.assertIn("must reconcile", str(ctx.exception))

    def test_combined_total_is_labelled_as_arithmetic_not_an_offer(self):
        result = evaluate(load_requests(read_json(REQUESTS_FIXTURE)), baseline())
        self.assertIn("not an offer", result["totals"]["combined_note"])
        self.assertEqual(
            result["totals"]["combined_if_all_authorized"],
            cents_to_dollars(2400000 + result["totals"]["quoted_changes_cents"]),
        )

    def test_every_output_carries_the_proposed_estimate_banner(self):
        result = evaluate(load_requests(read_json(REQUESTS_FIXTURE)), baseline())
        self.assertEqual(result["status"], "PROPOSED_ESTIMATE_NOT_A_COMMITMENT")
        for record in result["quotes"]:
            self.assertEqual(
                record["status"], "PROPOSED_ESTIMATE_NOT_A_COMMITMENT"
            )
        text = render_markdown(result)
        self.assertIn("PROPOSED ESTIMATES, NOT COMMITMENTS", text)
        self.assertIn("not an offer", text)

    def test_every_request_is_dispositioned_exactly_once(self):
        requests = load_requests(read_json(REQUESTS_FIXTURE))
        result = evaluate(requests, baseline())
        self.assertTrue(result["integrity"]["all_requests_dispositioned"])
        self.assertEqual(result["integrity"]["requests_in"], len(requests))
        ids = [q["request_id"] for q in result["quotes"]]
        self.assertEqual(sorted(ids), sorted({r.request_id for r in requests}))

    def test_fixture_demonstrates_all_four_dispositions(self):
        result = evaluate(load_requests(read_json(REQUESTS_FIXTURE)), baseline())
        found = {q["disposition"] for q in result["quotes"]}
        self.assertEqual(
            found, {CHANGE_QUOTE, NO_CHARGE_CURE, NOT_QUOTABLE, NEEDS_INPUT}
        )


# ---------------------------------------------------------------------------
# Hostile input
# ---------------------------------------------------------------------------


class HostileInputTests(unittest.TestCase):
    def test_missing_basis_is_refused_not_inferred(self):
        payload = make_request()
        del payload["basis"]
        with self.assertRaises(ScopeChangeError) as ctx:
            ChangeRequest(payload)
        self.assertIn("basis", str(ctx.exception))
        self.assertIn("cannot be left to inference", str(ctx.exception))

    def test_invented_basis_is_refused(self):
        with self.assertRaises(ScopeChangeError):
            ChangeRequest(make_request(basis="goodwill"))

    def test_unknown_role_is_refused_with_the_known_roles_listed(self):
        with self.assertRaises(ScopeChangeError) as ctx:
            one(
                make_request(
                    work_items=[
                        {"task": "t", "role": "wizard", "hours": 4}
                    ]
                )
            )
        self.assertIn("wizard", str(ctx.exception))
        self.assertIn("assessment_engineer", str(ctx.exception))

    def test_negative_hours_are_refused(self):
        with self.assertRaises(ScopeChangeError) as ctx:
            ChangeRequest(
                make_request(
                    work_items=[
                        {"task": "t", "role": "assessment_engineer", "hours": -4}
                    ]
                )
            )
        self.assertIn("negative", str(ctx.exception))

    def test_boolean_hours_are_refused(self):
        with self.assertRaises(ScopeChangeError):
            ChangeRequest(
                make_request(
                    work_items=[
                        {"task": "t", "role": "assessment_engineer", "hours": True}
                    ]
                )
            )

    def test_duplicate_request_ids_are_refused(self):
        with self.assertRaises(ScopeChangeError) as ctx:
            load_requests([make_request("CR-T-DUP"), make_request("CR-T-DUP")])
        self.assertIn("CR-T-DUP", str(ctx.exception))

    def test_missing_request_id_is_refused(self):
        with self.assertRaises(ScopeChangeError):
            load_requests([{"basis": "added_scope"}])

    def test_baseline_without_roles_is_refused(self):
        payload = baseline_payload()
        payload["roles"] = {}
        with self.assertRaises(ScopeChangeError):
            Baseline(payload)

    def test_negative_overhead_is_refused(self):
        payload = baseline_payload()
        payload["effort_model"]["coordination_overhead_pct"] = -5
        with self.assertRaises(ScopeChangeError):
            Baseline(payload)

    def test_empty_request_set_produces_an_empty_but_valid_worksheet(self):
        result = evaluate([], baseline())
        self.assertEqual(result["quotes"], [])
        self.assertEqual(result["totals"]["quoted_changes"], "$0.00")
        self.assertEqual(result["totals"]["baseline_base_fee"], "$24,000.00")
        self.assertTrue(result["integrity"]["all_requests_dispositioned"])

    def test_malformed_json_names_the_file(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as handle:
            handle.write("{nope")
            path = handle.name
        try:
            with self.assertRaises(ScopeChangeError) as ctx:
                read_json(path)
            self.assertIn(path, str(ctx.exception))
        finally:
            os.unlink(path)

    def test_a_request_with_no_work_breakdown_is_unquoted_not_free(self):
        """An empty breakdown is an unestimated change, not a costless one.

        The same error as pricing a missing line at zero, moved up a level: a
        $0.00 quote here would read as "this change is free" when what actually
        happened is that nobody broke the work down.
        """
        record = one(make_request(work_items=[]))
        self.assertEqual(record["disposition"], NEEDS_INPUT)
        self.assertIsNone(record["fee_cents"])
        self.assertEqual(record["fee"], "UNKNOWN")
        self.assertNotEqual(record["fee"], "$0.00")
        self.assertEqual(record["missing_inputs"], ["work_items"])


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------


class EndToEndTests(unittest.TestCase):
    def test_output_is_deterministic(self):
        requests = load_requests(read_json(REQUESTS_FIXTURE))
        first = json.dumps(evaluate(requests, baseline()), sort_keys=True)
        second = json.dumps(evaluate(requests, baseline()), sort_keys=True)
        self.assertEqual(first, second)

    def test_cli_writes_all_three_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_out = os.path.join(tmp, "o.json")
            csv_out = os.path.join(tmp, "o.csv")
            md_out = os.path.join(tmp, "o.md")
            code = scope_change.main(
                [
                    "--baseline", BASELINE_FIXTURE,
                    "--requests", REQUESTS_FIXTURE,
                    "--json-out", json_out,
                    "--csv-out", csv_out,
                    "--markdown-out", md_out,
                ]
            )
            self.assertEqual(code, 0)
            bundle = read_json(json_out)
            self.assertEqual(
                bundle["result"]["content_class"],
                "SYNTHETIC_DRAFT_NOT_A_COMMITMENT",
            )
            self.assertTrue(bundle["result"]["integrity"]["cures_are_all_zero_fee"])
            self.assertTrue(bundle["assumption_sensitivity"]["cures_stay_zero"])
            self.assertTrue(bundle["assumption_sensitivity"]["changes_move"])
            with open(md_out, encoding="utf-8") as handle:
                self.assertIn("No-charge corrections", handle.read())

    def test_cli_reports_a_bad_path_without_a_traceback(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "scope_change.py"),
             "--baseline", "/nonexistent/baseline.json"],
            capture_output=True, text=True, cwd=HERE,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("$", proc.stdout)

    def test_module_runs_under_python_O(self):
        proc = subprocess.run(
            [sys.executable, "-O", "-m", "unittest",
             "test_scope_change.DefectVersusAddedWorkTests"],
            capture_output=True, text=True, cwd=HERE,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
