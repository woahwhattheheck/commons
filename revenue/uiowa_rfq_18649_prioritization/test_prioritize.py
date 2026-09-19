#!/usr/bin/env python3
"""Regression tests for the recommendation prioritization worksheet.

The suite is organized around the three things this tool is only worth having if
it gets right:

* `MissingEstimateTests`  -- a missing estimate must never become a zero, a pass,
  or a bottom rank. This is the hard requirement; it gets the most tests.
* `SensitivityTests`      -- the weight sweep has to actually reorder the list,
  and the reordering has to be reported with the weight it happens at.
* `TieTests`              -- tied priorities stay legible and are never broken
  silently by list position.

Run:  python3 -m unittest -v test_prioritize.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

import prioritize
from prioritize import (
    NEEDS_ESTIMATE,
    NOT_RANKED,
    RANKED,
    UNKNOWN,
    PrioritizationError,
    Recommendation,
    Weights,
    find_crossovers,
    load_recommendations,
    load_scenarios,
    rank,
    read_json,
    render_markdown,
    score_recommendation,
    sweep_scenarios,
    to_csv_rows,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "synthetic-recommendations.json")
SCENARIOS = os.path.join(HERE, "fixtures", "weight-scenarios.json")

BASELINE = {"quality": 0.35, "security": 0.40, "delivery": 0.25}


def make_rec(rec_id="REC-T-001", **overrides):
    """A complete, valid recommendation that individual tests damage on purpose."""
    payload = {
        "recommendation_id": rec_id,
        "title": "test recommendation",
        "group": "ESS",
        "area": "SD",
        "finding_ids": ["FND-T-001"],
        "effects": {"quality": 3, "security": 3, "delivery": 3},
        "complexity": 3,
    }
    payload.update(overrides)
    return payload


def one(payload, weights=None):
    """Score a single recommendation payload under a weight vector."""
    return score_recommendation(
        Recommendation(payload), Weights(weights or BASELINE, name="t")
    )


# ---------------------------------------------------------------------------
# The hard requirement
# ---------------------------------------------------------------------------


class MissingEstimateTests(unittest.TestCase):
    """A missing estimate is an UNKNOWN that propagates. It is never a zero."""

    def test_zero_and_missing_are_not_the_same_outcome(self):
        """The single most important assertion in this suite.

        An estimate of 0 means "assessed, no expected effect" and is scored.
        An absent estimate means "nobody has said" and is NOT scored. If these
        two ever collapse into the same output, the tool is lying about what it
        knows, and this test fails.
        """
        explicit_zero = one(
            make_rec(effects={"quality": 0, "security": 3, "delivery": 3})
        )
        missing = one(make_rec(effects={"security": 3, "delivery": 3}))

        self.assertEqual(explicit_zero["status"], RANKED)
        self.assertEqual(missing["status"], NEEDS_ESTIMATE)

        # The zero is scored, and scored correctly. Compared with a tolerance
        # because the reported benefit is rounded to SCORE_PRECISION places,
        # which is deliberate: an unrounded 1.9500000000000002 in a worksheet
        # reads as false precision.
        self.assertAlmostEqual(
            explicit_zero["benefit"], 0.4 * 3 + 0.25 * 3, places=6
        )
        self.assertIsNotNone(explicit_zero["priority_score"])
        # The 0 contributed a term of exactly 0.0 -- it was multiplied by its
        # weight like any other estimate, not skipped.
        self.assertEqual(
            explicit_zero["contributions"]["quality"]["contribution"], 0.0
        )
        self.assertEqual(explicit_zero["contributions"]["quality"]["estimate"], 0)
        self.assertFalse(
            explicit_zero["contributions"]["quality"]["estimate_is_unknown"]
        )
        # Whereas the missing one contributed no term at all.
        self.assertIsNone(missing["contributions"]["quality"]["contribution"])
        self.assertIsNone(missing["contributions"]["quality"]["estimate"])
        self.assertTrue(missing["contributions"]["quality"]["estimate_is_unknown"])

        # The missing one has no score at all -- not 0, not None-that-sorts-low.
        self.assertIsNone(missing["priority_score"])
        self.assertIsNone(missing["benefit"])
        self.assertIsNone(missing["rank"])
        self.assertEqual(missing["blocking_unknowns"], ["effects.quality"])
        self.assertIn("not scored as 0", missing["arithmetic"])

    def test_every_spelling_of_missing_becomes_unknown(self):
        """Absent key, null, empty string, "UNKNOWN", "n/a", "TBD" all agree."""
        spellings = [
            {"security": 3, "delivery": 3},  # key absent entirely
            {"quality": None, "security": 3, "delivery": 3},
            {"quality": "", "security": 3, "delivery": 3},
            {"quality": "UNKNOWN", "security": 3, "delivery": 3},
            {"quality": "unknown", "security": 3, "delivery": 3},
            {"quality": "n/a", "security": 3, "delivery": 3},
            {"quality": "TBD", "security": 3, "delivery": 3},
            # An estimate object carrying a justification but no number is
            # still no number.
            {
                "quality": {"basis": "we never measured this"},
                "security": 3,
                "delivery": 3,
            },
        ]
        for effects in spellings:
            with self.subTest(effects=effects):
                record = one(make_rec(effects=effects))
                self.assertEqual(record["status"], NEEDS_ESTIMATE)
                self.assertIsNone(record["priority_score"])
                self.assertEqual(record["blocking_unknowns"], ["effects.quality"])

    def test_unknown_sentinel_refuses_arithmetic_and_truthiness(self):
        """UNKNOWN cannot be coerced into a number by accident.

        This is the guard that caught a real bug during development: a
        zero-weight dimension was still being read in the benefit sum. Because
        UNKNOWN has no __mul__, it raised instead of silently contributing.
        """
        with self.assertRaises(TypeError):
            0.4 * UNKNOWN  # type: ignore[operator]
        with self.assertRaises(PrioritizationError):
            bool(UNKNOWN)
        self.assertIsNot(UNKNOWN, 0)
        self.assertNotEqual(UNKNOWN, 0)

    def test_missing_complexity_blocks_even_with_every_effect_known(self):
        """Unknown effort is as blocking as unknown benefit."""
        record = one(make_rec(complexity=None))
        self.assertEqual(record["status"], NEEDS_ESTIMATE)
        self.assertEqual(record["blocking_unknowns"], ["complexity"])
        self.assertIsNone(record["priority_score"])
        # All three effects were supplied, so none of them is blocking.
        self.assertEqual(
            [f for f in record["blocking_unknowns"] if f.startswith("effects.")], []
        )

    def test_complexity_zero_is_refused_not_accepted_as_free(self):
        """"Zero effort" is never a real estimate.

        Accepting it would divide the item straight to the top of the list, which
        is the mirror image of the bug this tool exists to prevent.
        """
        with self.assertRaises(PrioritizationError) as ctx:
            Recommendation(make_rec(complexity=0))
        message = str(ctx.exception)
        self.assertIn("complexity", message)
        self.assertIn("no zero", message)

    def test_unranked_items_never_appear_in_the_ranked_list(self):
        recs = load_recommendations(read_json(FIXTURE))
        result = rank(recs, Weights(BASELINE, name="baseline"))
        ranked_ids = {r["recommendation_id"] for r in result["ranked"]}
        unranked_ids = {r["recommendation_id"] for r in result["needs_estimate"]}
        self.assertTrue(ranked_ids.isdisjoint(unranked_ids))
        self.assertEqual(
            len(ranked_ids) + len(unranked_ids),
            len(recs),
            "every recommendation must land in exactly one bucket",
        )
        for record in result["needs_estimate"]:
            self.assertIsNone(record["rank"])
            self.assertIsNone(record["priority_score"])

    def test_missing_estimate_is_not_ranked_last_either(self):
        """Being unranked is not the same as being deprioritized.

        A strong recommendation with one unestimated field must not end up below
        a weak but fully-estimated one. It is out of the ordering entirely, and
        its bound is reported so a reader can see it could have led the list.
        """
        strong_but_incomplete = make_rec(
            "REC-T-STRONG",
            effects={"quality": 5, "security": 5, "delivery": 5},
            complexity=None,
        )
        weak_but_complete = make_rec(
            "REC-T-WEAK",
            effects={"quality": 1, "security": 0, "delivery": 0},
            complexity=5,
        )
        result = rank(
            [Recommendation(strong_but_incomplete), Recommendation(weak_but_complete)],
            Weights(BASELINE, name="baseline"),
        )
        self.assertEqual(
            [r["recommendation_id"] for r in result["ranked"]], ["REC-T-WEAK"]
        )
        blocked = result["needs_estimate"][0]
        self.assertEqual(blocked["recommendation_id"], "REC-T-STRONG")
        self.assertEqual(blocked["estimate_urgency"], "DECISION_BLOCKING")
        # Its ceiling is far above the ranked item's score, which is exactly why
        # leaving it out of the list -- rather than at the bottom of it -- is the
        # honest representation.
        self.assertGreater(
            blocked["score_bounds"]["score_if_unknowns_highest"],
            result["ranked"][0]["priority_score"],
        )

    def test_decision_blocking_versus_not_blocking(self):
        """The bound answers 'does this gap change the decision?' both ways."""
        recs = load_recommendations(read_json(FIXTURE))
        result = rank(recs, Weights(BASELINE, name="baseline"))
        urgency = {
            r["recommendation_id"]: r["estimate_urgency"]
            for r in result["needs_estimate"]
        }
        self.assertEqual(urgency["REC-SYN-IAM-SD-001"], "DECISION_BLOCKING")
        self.assertEqual(urgency["REC-SYN-ESS-AI-001"], "DECISION_BLOCKING")
        self.assertEqual(urgency["REC-SYN-RIS-DEP-001"], "NOT_DECISION_BLOCKING")
        # "Not decision blocking" must never be mistaken for "resolved".
        not_blocking = next(
            r
            for r in result["needs_estimate"]
            if r["recommendation_id"] == "REC-SYN-RIS-DEP-001"
        )
        self.assertEqual(not_blocking["status"], NEEDS_ESTIMATE)
        self.assertIsNone(not_blocking["priority_score"])
        self.assertEqual(not_blocking["blocking_unknowns"], ["effects.security"])

    def test_bounds_are_a_range_not_a_substituted_value(self):
        record = one(make_rec(complexity="UNKNOWN"))
        bounds = record["score_bounds"]
        self.assertIn("bound, not a score", bounds["basis"])
        # benefit 3.0 over complexity 5 (worst) .. 1 (best)
        self.assertEqual(bounds["score_if_unknowns_lowest"], 0.6)
        self.assertEqual(bounds["score_if_unknowns_highest"], 3.0)
        self.assertNotEqual(
            bounds["score_if_unknowns_lowest"],
            bounds["score_if_unknowns_highest"],
            "a real unknown must produce a range, not a point estimate",
        )

    def test_non_material_unknown_stays_ranked_but_stays_reported(self):
        """An unknown in a zero-weight dimension cannot change this order.

        It is therefore not blocking -- but it is still missing, and the record
        has to say so. Silence here would be the tool quietly deciding the gap
        did not exist.
        """
        payload = make_rec(effects={"security": 3, "delivery": 3})  # no quality
        record = one(payload, weights={"quality": 0, "security": 1, "delivery": 1})
        self.assertEqual(record["status"], RANKED)
        self.assertEqual(record["blocking_unknowns"], [])
        self.assertEqual(record["non_material_unknowns"], ["effects.quality"])
        self.assertEqual(record["unknown_fields"], ["effects.quality"])
        self.assertIsNone(record["contributions"]["quality"]["estimate"])
        self.assertTrue(record["contributions"]["quality"]["estimate_is_unknown"])
        self.assertIn("zero weight, not read: quality", record["arithmetic"])

    def test_materiality_flips_when_the_weight_flips(self):
        """The same item, the same gap, two weightings, two buckets."""
        payload = make_rec(effects={"security": 3, "delivery": 3})
        rec = Recommendation(payload)

        ignored = score_recommendation(
            rec, Weights({"quality": 0, "security": 1, "delivery": 1}, name="ignore-q")
        )
        counted = score_recommendation(
            rec, Weights({"quality": 1, "security": 1, "delivery": 1}, name="count-q")
        )
        self.assertEqual(ignored["status"], RANKED)
        self.assertEqual(counted["status"], NEEDS_ESTIMATE)
        # In neither case is the gap invented away.
        self.assertEqual(ignored["unknown_fields"], ["effects.quality"])
        self.assertEqual(counted["unknown_fields"], ["effects.quality"])

    def test_csv_never_writes_a_zero_or_blank_for_an_unknown(self):
        """The spreadsheet is where a missing estimate usually turns into a 0.

        An empty rank cell sorts as 0 in most tools and a blank score reads as
        nothing-to-see. Both are refused: unknowns are written as words.
        """
        recs = load_recommendations(read_json(FIXTURE))
        result = rank(recs, Weights(BASELINE, name="baseline"))
        rows = to_csv_rows(result)
        header = rows[0]
        rank_col = header.index("rank")
        score_col = header.index("priority_score")
        benefit_col = header.index("benefit")
        status_col = header.index("status")
        blocked_col = header.index("blocked_by")

        seen_unranked = 0
        for row in rows[1:]:
            if row[status_col] != NEEDS_ESTIMATE:
                continue
            seen_unranked += 1
            self.assertEqual(row[rank_col], NOT_RANKED)
            self.assertNotEqual(row[rank_col], "")
            self.assertNotEqual(row[rank_col], "0")
            self.assertEqual(row[score_col], "UNKNOWN")
            self.assertEqual(row[benefit_col], "UNKNOWN")
            self.assertTrue(row[blocked_col], "the blocking field must be named")
        self.assertEqual(seen_unranked, 3, "fixture should carry three gaps")

        # And the row count is preserved: nothing is dropped to tidy the table.
        self.assertEqual(len(rows) - 1, len(recs))

    def test_a_real_zero_still_scores_and_still_ranks(self):
        """Under a security-only weighting one fixture item scores exactly 0.0.

        That is a legitimate result of a real estimate, and it must stay in the
        ranked list -- visibly different from the unranked bucket.
        """
        recs = load_recommendations(read_json(FIXTURE))
        result = rank(
            recs, Weights({"quality": 0, "security": 1, "delivery": 0}, name="sec-only")
        )
        zero_scored = next(
            r
            for r in result["ranked"]
            if r["recommendation_id"] == "REC-SYN-ESS-DEP-001"
        )
        self.assertEqual(zero_scored["priority_score"], 0.0)
        self.assertEqual(zero_scored["status"], RANKED)
        self.assertIsNotNone(zero_scored["rank"])
        unranked_ids = {r["recommendation_id"] for r in result["needs_estimate"]}
        self.assertNotIn("REC-SYN-ESS-DEP-001", unranked_ids)

    def test_markdown_states_the_rule_and_lists_the_bucket(self):
        recs = load_recommendations(read_json(FIXTURE))
        result = rank(recs, Weights(BASELINE, name="baseline"))
        text = render_markdown(result)
        self.assertIn("Needs estimate (not ranked, not scored zero)", text)
        self.assertIn("A blank estimate is **UNKNOWN**, which is not 0.", text)
        self.assertIn("bound, not a score", text)
        for record in result["needs_estimate"]:
            self.assertIn(record["recommendation_id"], text)


# ---------------------------------------------------------------------------
# Sensitivity
# ---------------------------------------------------------------------------


class SensitivityTests(unittest.TestCase):
    """Changing the assumptions has to visibly change the ranking."""

    def setUp(self):
        self.recs = load_recommendations(read_json(FIXTURE))
        self.scenarios = load_scenarios(read_json(SCENARIOS))

    def test_the_weight_sweep_reorders_the_list(self):
        sweep = sweep_scenarios(self.recs, self.scenarios)
        self.assertFalse(
            sweep["top_item_stable"],
            "the fixture is built so the leader changes; if this passes as True "
            "the sweep is not exercising anything",
        )
        leaders = sweep["leader_by_scenario"]
        self.assertEqual(leaders["baseline"], ["REC-SYN-IAM-DEP-001"])
        self.assertEqual(leaders["quality-led"], ["REC-SYN-ESS-SD-001"])
        self.assertEqual(leaders["delivery-led"], ["REC-SYN-ESS-SD-001"])
        self.assertNotEqual(leaders["baseline"], leaders["quality-led"])
        self.assertIn("argument about priorities", sweep["interpretation"])

    def test_orderings_actually_differ_not_just_scores(self):
        baseline = rank(self.recs, Weights(BASELINE, name="baseline"))
        quality_led = rank(
            self.recs,
            Weights({"quality": 0.60, "security": 0.25, "delivery": 0.15}, name="q"),
        )
        order_a = [r["recommendation_id"] for r in baseline["ranked"]]
        order_b = [r["recommendation_id"] for r in quality_led["ranked"]]
        self.assertEqual(sorted(order_a), sorted(order_b), "same population")
        self.assertNotEqual(order_a, order_b, "different order")

    def test_rank_stability_labels_are_earned(self):
        sweep = sweep_scenarios(self.recs, self.scenarios)
        by_id = {r["recommendation_id"]: r for r in sweep["rank_stability"]}

        moves = by_id["REC-SYN-ESS-SD-001"]
        self.assertEqual(moves["stability"], "MOVES")
        self.assertGreater(moves["rank_spread"], 0)
        self.assertEqual(moves["best_rank"], min(moves["best_rank"], moves["worst_rank"]))

        never = by_id["REC-SYN-IAM-SD-001"]
        self.assertEqual(never["stability"], "NEVER_RANKED")
        self.assertIsNone(never["rank_spread"])
        self.assertTrue(
            all(v == NOT_RANKED for v in never["rank_by_scenario"].values())
        )

        # Ranked under one weighting, unranked under others, because of a gap.
        flips = by_id["REC-SYN-ESS-AI-001"]
        self.assertEqual(flips["stability"], "ENTERS_UNKNOWN_BUCKET")
        self.assertEqual(flips["rank_by_scenario"]["baseline"], NOT_RANKED)
        self.assertNotEqual(
            flips["rank_by_scenario"]["security-only-stress"], NOT_RANKED
        )

    def test_crossover_sweep_finds_the_weight_where_the_leader_changes(self):
        sweep = find_crossovers(
            self.recs, "security", steps=100, base=Weights(BASELINE, name="baseline")
        )
        self.assertTrue(sweep["reorders"])
        self.assertTrue(sweep["leader_changes"], "the leader must change somewhere")
        change = sweep["leader_changes"][0]
        self.assertEqual(change["leader_before"], "REC-SYN-ESS-SD-001")
        self.assertEqual(change["leader_after"], "REC-SYN-IAM-DEP-001")
        # Solved by hand: benefit_IAM = 3 + 2w, benefit_ESS = 4.1667(1-w) + 2w,
        # both over complexity 2 -> they cross at w = 0.28, so the first step at
        # which the new leader is strictly ahead is 0.29.
        self.assertAlmostEqual(change["at_weight"], 0.29, places=6)
        # And the baseline weight sits above the crossover, which is why the
        # security-led item leads at baseline.
        self.assertGreater(BASELINE["security"], change["at_weight"])

    def test_crossover_sweep_reports_where_a_gap_starts_and_stops_mattering(self):
        sweep = find_crossovers(
            self.recs, "security", steps=100, base=Weights(BASELINE, name="baseline")
        )
        left = {
            (c["at_weight"], rid)
            for c in sweep["materiality_changes"]
            for rid in c["left_ranked_list"]
        }
        entered = {
            (c["at_weight"], rid)
            for c in sweep["materiality_changes"]
            for rid in c["entered_ranked_list"]
        }
        # Security weight becomes non-zero: the item that never estimated
        # security stops being rankable.
        self.assertIn((0.01, "REC-SYN-RIS-DEP-001"), left)
        # Security takes all the weight, so quality drops to zero: the item that
        # never estimated quality becomes rankable.
        self.assertIn((1.0, "REC-SYN-ESS-AI-001"), entered)

    def test_a_sweep_that_does_not_reorder_says_so(self):
        """No false drama: an insensitive ranking is reported as insensitive."""
        flat = [
            Recommendation(
                make_rec(
                    "REC-T-A",
                    effects={"quality": 5, "security": 5, "delivery": 5},
                    complexity=1,
                )
            ),
            Recommendation(
                make_rec(
                    "REC-T-B",
                    effects={"quality": 1, "security": 1, "delivery": 1},
                    complexity=5,
                )
            ),
        ]
        sweep = find_crossovers(flat, "security", steps=20)
        self.assertFalse(sweep["reorders"])
        self.assertEqual(sweep["crossovers"], [])
        self.assertEqual(sweep["leader_changes"], [])
        text = render_markdown(
            rank(flat, Weights(BASELINE, name="b")), crossover=sweep
        )
        self.assertIn("No reordering", text)

    def test_normalization_is_reported_not_hidden(self):
        weights = Weights({"quality": 1, "security": 1, "delivery": 1}, name="equal")
        public = weights.to_public_dict()
        self.assertTrue(public["was_normalized"])
        self.assertEqual(public["raw_total"], 3.0)
        self.assertAlmostEqual(public["normalized"]["quality"], 1 / 3, places=5)
        self.assertIn("0.333xquality", public["formula"])
        text = render_markdown(rank([], weights))
        self.assertIn("normalized to 1.0", text)

        exact = Weights(BASELINE, name="baseline")
        self.assertFalse(exact.to_public_dict()["was_normalized"])

    def test_weights_summing_to_zero_are_refused(self):
        with self.assertRaises(PrioritizationError) as ctx:
            Weights({"quality": 0, "security": 0, "delivery": 0}, name="empty")
        self.assertIn("at least one dimension must carry weight", str(ctx.exception))


# ---------------------------------------------------------------------------
# Ties
# ---------------------------------------------------------------------------


class TieTests(unittest.TestCase):
    """Tied priorities stay understandable and are never silently broken."""

    def setUp(self):
        self.recs = load_recommendations(read_json(FIXTURE))
        self.result = rank(self.recs, Weights(BASELINE, name="baseline"))

    def test_equal_scores_share_a_rank_and_the_next_rank_skips(self):
        ranks = [r["rank"] for r in self.result["ranked"]]
        self.assertEqual(ranks, [1, 2, 3, 4, 4, 6, 7, 8])
        self.assertNotIn(5, ranks, "competition ranking skips the consumed position")

    def test_tie_group_is_reported_with_the_inputs_that_produced_it(self):
        self.assertEqual(len(self.result["tie_groups"]), 1)
        group = self.result["tie_groups"][0]
        self.assertEqual(group["rank"], 4)
        self.assertEqual(
            group["members"], ["REC-SYN-ESS-SEC-001", "REC-SYN-RIS-SD-001"]
        )
        self.assertEqual(group["shared_priority_score"], 1.0)
        # Every member's raw inputs are shown, so the tie can be understood
        # rather than just observed.
        for member in group["member_inputs"]:
            self.assertIn("benefit", member)
            self.assertIn("complexity", member)
            self.assertEqual(set(member["effects"]), {"quality", "security", "delivery"})
        self.assertIn("cancel at these weights", group["why_tied"])

    def test_tie_report_computes_what_would_separate_them(self):
        group = self.result["tie_groups"][0]
        probe = {p["dimension"]: p for p in group["corner_probe"]}
        # 0/3 quality over equal complexity 3 -> 0.0 vs 1.0: separates.
        self.assertTrue(probe["quality"]["separates"])
        self.assertEqual(
            probe["quality"]["scores_at_full_weight"]["REC-SYN-ESS-SEC-001"], 0.0
        )
        self.assertEqual(
            probe["quality"]["scores_at_full_weight"]["REC-SYN-RIS-SD-001"], 1.0
        )
        self.assertTrue(any("weight quality alone" in a for a in group["what_would_separate_them"]))

    def test_tie_members_are_marked_and_order_disclaims_priority(self):
        tied = [r for r in self.result["ranked"] if r["is_tied"]]
        self.assertEqual(len(tied), 2)
        for record in tied:
            self.assertEqual(record["tie_group_size"], 2)
            self.assertTrue(record["display_order_is_not_priority"])
        untied = [r for r in self.result["ranked"] if not r["is_tied"]]
        for record in untied:
            self.assertEqual(record["tie_group_size"], 1)
            self.assertFalse(record["display_order_is_not_priority"])

    def test_a_tie_can_be_an_artifact_of_the_weights(self):
        """The rank-4 tie is not a property of the work, only of the weighting."""
        security_led = rank(
            self.recs,
            Weights({"quality": 0.20, "security": 0.65, "delivery": 0.15}, name="s"),
        )
        scores = {
            r["recommendation_id"]: r["priority_score"] for r in security_led["ranked"]
        }
        self.assertNotEqual(
            scores["REC-SYN-ESS-SEC-001"], scores["REC-SYN-RIS-SD-001"]
        )

    def test_tie_ordering_is_deterministic_across_input_order(self):
        """Shuffling the input must not change who is printed first in a tie."""
        forward = rank(self.recs, Weights(BASELINE, name="b"))
        backward = rank(list(reversed(self.recs)), Weights(BASELINE, name="b"))
        self.assertEqual(
            [r["recommendation_id"] for r in forward["ranked"]],
            [r["recommendation_id"] for r in backward["ranked"]],
        )
        self.assertEqual(
            [r["rank"] for r in forward["ranked"]],
            [r["rank"] for r in backward["ranked"]],
        )

    def test_markdown_renders_the_tie_legibly(self):
        text = render_markdown(self.result)
        self.assertIn("**Rank 4 is shared**", text)
        self.assertIn("4 (tied)", text)
        self.assertIn("carries no priority meaning", text)


# ---------------------------------------------------------------------------
# Hostile and malformed input
# ---------------------------------------------------------------------------


class HostileInputTests(unittest.TestCase):
    """Bad input is refused by name. Nothing is repaired by substitution."""

    def test_out_of_range_estimates_are_refused(self):
        for effects in (
            {"quality": 9, "security": 3, "delivery": 3},
            {"quality": -1, "security": 3, "delivery": 3},
        ):
            with self.subTest(effects=effects):
                with self.assertRaises(PrioritizationError) as ctx:
                    Recommendation(make_rec(effects=effects))
                self.assertIn("effects.quality", str(ctx.exception))
                self.assertIn("0-5", str(ctx.exception))

    def test_complexity_above_scale_is_refused(self):
        with self.assertRaises(PrioritizationError) as ctx:
            Recommendation(make_rec(complexity=12))
        self.assertIn("1-5", str(ctx.exception))

    def test_booleans_are_not_quietly_ones_and_zeros(self):
        with self.assertRaises(PrioritizationError) as ctx:
            Recommendation(make_rec(effects={"quality": True, "security": 3, "delivery": 3}))
        self.assertIn("boolean", str(ctx.exception))

    def test_unparseable_text_is_refused_not_treated_as_unknown(self):
        """"high" is somebody's estimate, not an absence. Refuse, do not guess."""
        with self.assertRaises(PrioritizationError) as ctx:
            Recommendation(make_rec(effects={"quality": "high", "security": 3, "delivery": 3}))
        message = str(ctx.exception)
        self.assertIn("'high'", message)
        self.assertIn("effects.quality", message)

    def test_fractional_estimates_are_refused(self):
        with self.assertRaises(PrioritizationError):
            Recommendation(make_rec(effects={"quality": 3.5, "security": 3, "delivery": 3}))

    def test_unrecognized_dimension_is_refused(self):
        with self.assertRaises(PrioritizationError) as ctx:
            Recommendation(
                make_rec(effects={"quality": 3, "security": 3, "delivery": 3, "cost": 2})
            )
        self.assertIn("cost", str(ctx.exception))

    def test_duplicate_recommendation_ids_are_refused(self):
        with self.assertRaises(PrioritizationError) as ctx:
            load_recommendations([make_rec("REC-T-DUP"), make_rec("REC-T-DUP")])
        self.assertIn("REC-T-DUP", str(ctx.exception))

    def test_missing_recommendation_id_is_refused(self):
        with self.assertRaises(PrioritizationError):
            load_recommendations([{"title": "no id"}])

    def test_empty_recommendation_set_does_not_crash(self):
        result = rank([], Weights(BASELINE, name="b"))
        self.assertEqual(result["ranked"], [])
        self.assertEqual(result["counts"]["total"], 0)
        self.assertIn("Nothing is rankable", render_markdown(result))

    def test_every_item_unknown_reports_all_gaps_as_blocking(self):
        """With nothing rankable, no gap can be called unimportant."""
        recs = [
            Recommendation(make_rec("REC-T-A", complexity=None)),
            Recommendation(make_rec("REC-T-B", complexity="UNKNOWN")),
        ]
        result = rank(recs, Weights(BASELINE, name="b"))
        self.assertEqual(result["ranked"], [])
        self.assertEqual(len(result["needs_estimate"]), 2)
        for record in result["needs_estimate"]:
            self.assertEqual(record["estimate_urgency"], "DECISION_BLOCKING")
            self.assertIn("nothing is rankable", record["estimate_urgency_basis"])

    def test_malformed_json_names_the_file(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as handle:
            handle.write("{not json")
            path = handle.name
        try:
            with self.assertRaises(PrioritizationError) as ctx:
                read_json(path)
            self.assertIn(path, str(ctx.exception))
        finally:
            os.unlink(path)

    def test_recommendations_must_be_a_list(self):
        with self.assertRaises(PrioritizationError):
            load_recommendations({"nope": 1})

    def test_negative_weight_is_refused(self):
        with self.assertRaises(PrioritizationError) as ctx:
            Weights({"quality": -1, "security": 2, "delivery": 1}, name="bad")
        self.assertIn("negative", str(ctx.exception))


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------


class EndToEndTests(unittest.TestCase):
    def test_fixture_demonstrates_both_a_strength_and_a_gap(self):
        """The fixture has to be worth running, not just valid."""
        recs = load_recommendations(read_json(FIXTURE))
        result = rank(recs, Weights(BASELINE, name="baseline"))
        self.assertGreaterEqual(result["counts"]["ranked"], 5, "a usable ranking")
        self.assertGreaterEqual(result["counts"]["needs_estimate"], 2, "real gaps")
        self.assertGreaterEqual(result["counts"]["decision_blocking_unknowns"], 1)
        self.assertTrue(result["tie_groups"], "a tie to keep legible")
        # A real 0 and a real UNKNOWN both present, so they can be contrasted.
        zeros = [
            r
            for r in result["ranked"]
            if 0 in [r["contributions"][d]["estimate"] for d in prioritize.DIMENSIONS]
        ]
        self.assertTrue(zeros, "fixture must contain a genuine zero estimate")
        # And an untraceable recommendation, reported rather than dropped.
        untraceable = [
            r for r in result["ranked"] if not r["traceable_to_finding"]
        ]
        self.assertTrue(untraceable)
        self.assertIn("Not traceable to a finding", render_markdown(result))

    def test_output_is_deterministic(self):
        recs = load_recommendations(read_json(FIXTURE))
        scenarios = load_scenarios(read_json(SCENARIOS))
        first = json.dumps(
            {
                "rank": rank(recs, Weights(BASELINE, name="b")),
                "sweep": sweep_scenarios(recs, scenarios),
            },
            sort_keys=True,
        )
        second = json.dumps(
            {
                "rank": rank(recs, Weights(BASELINE, name="b")),
                "sweep": sweep_scenarios(recs, scenarios),
            },
            sort_keys=True,
        )
        self.assertEqual(first, second)

    def test_cli_writes_all_three_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_out = os.path.join(tmp, "out.json")
            csv_out = os.path.join(tmp, "out.csv")
            md_out = os.path.join(tmp, "out.md")
            code = prioritize.main(
                [
                    "--recommendations", FIXTURE,
                    "--scenarios", SCENARIOS,
                    "--weights", "baseline",
                    "--json-out", json_out,
                    "--csv-out", csv_out,
                    "--markdown-out", md_out,
                ]
            )
            self.assertEqual(code, 0)
            bundle = read_json(json_out)
            self.assertEqual(
                bundle["content_class"],
                "SYNTHETIC_DRAFT_NOT_A_UNIVERSITY_FINDING",
            )
            self.assertFalse(bundle["sensitivity"]["top_item_stable"])
            self.assertTrue(os.path.getsize(csv_out) > 0)
            with open(md_out, encoding="utf-8") as handle:
                self.assertIn("Needs estimate", handle.read())

    def test_cli_accepts_inline_weights_and_changes_the_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "a.json")
            b = os.path.join(tmp, "b.json")
            prioritize.main(
                ["--recommendations", FIXTURE, "--scenarios", SCENARIOS,
                 "--weights", "quality=1,security=0,delivery=0",
                 "--no-sensitivity", "--json-out", a]
            )
            prioritize.main(
                ["--recommendations", FIXTURE, "--scenarios", SCENARIOS,
                 "--weights", "security=1,quality=0,delivery=0",
                 "--no-sensitivity", "--json-out", b]
            )
            order_a = [
                r["recommendation_id"]
                for r in read_json(a)["active_ranking"]["ranked"]
            ]
            order_b = [
                r["recommendation_id"]
                for r in read_json(b)["active_ranking"]["ranked"]
            ]
            self.assertNotEqual(order_a, order_b)

    def test_cli_reports_a_bad_scenario_name_without_traceback(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, "prioritize.py"),
             "--weights", "no-such-scenario"],
            capture_output=True, text=True, cwd=HERE,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("no scenario named", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_module_runs_under_python_O(self):
        """The assert-free build must behave identically (no logic in asserts)."""
        proc = subprocess.run(
            [sys.executable, "-O", "-m", "unittest",
             "test_prioritize.MissingEstimateTests"],
            capture_output=True, text=True, cwd=HERE,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
