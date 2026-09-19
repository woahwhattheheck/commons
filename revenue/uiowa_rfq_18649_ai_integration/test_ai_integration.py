"""Tests for UIOWA-080: reference patterns, portability scoring, worksheet, swap demo.

Run:  python3 -m unittest -v test_ai_integration

These assert behavior, not shape. The ones that matter most are the hostile and
missing-data cases: an absent input must never come out the other side as a zero, a
pass, a band, or a supported pattern.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import patterns as patterns_mod
import portability
import worksheet as worksheet_mod
from portlib import caller
from portlib.port import (
    Classification,
    Document,
    ProviderContractViolation,
    ProviderTimeout,
    ProviderUnavailable,
    RoutingPolicy,
    check_conformance,
)
from portlib.providers.fake_alpha import AlphaClassificationAdapter
from portlib.providers.fake_beta import BetaClassificationAdapter
from unknowns import UNKNOWN, UnknownArithmeticError, coerce, partition, render

POLICY = RoutingPolicy()
DOCS = [
    Document("doc-1", "My card was declined paying the housing deposit."),
    Document("doc-2", "I am locked out, my badge stopped working."),
    Document("doc-3", "There is a leak above the elevator lobby."),
]


# ------------------------------------------------------------------- UNKNOWN

class TestUnknownCannotBecomeANumber(unittest.TestCase):

    def test_arithmetic_is_blocked_in_both_directions(self):
        for operation in (lambda: UNKNOWN + 1, lambda: 1 + UNKNOWN,
                          lambda: UNKNOWN * 2, lambda: 2 * UNKNOWN,
                          lambda: UNKNOWN - 1, lambda: UNKNOWN / 2):
            with self.assertRaises(UnknownArithmeticError):
                operation()

    def test_coercion_to_number_is_blocked(self):
        with self.assertRaises(UnknownArithmeticError):
            float(UNKNOWN)
        with self.assertRaises(UnknownArithmeticError):
            int(UNKNOWN)

    def test_ordering_comparison_is_blocked(self):
        # An unmeasured value must not silently sort below a measured one.
        with self.assertRaises(UnknownArithmeticError):
            _ = UNKNOWN < 5

    def test_partition_separates_and_names_the_unknowns(self):
        known, unknown_keys = partition({"a": 3, "b": "unknown", "c": None, "d": "TBD"})
        self.assertEqual(known, {"a": 3})
        self.assertEqual(unknown_keys, ["b", "c", "d"])

    def test_render_never_prints_zero_for_unknown(self):
        self.assertEqual(render(UNKNOWN), "UNKNOWN")
        self.assertEqual(render(coerce("n/a")), "UNKNOWN")
        self.assertEqual(render(0), "0")


# ------------------------------------------------------------- portability

class TestSwapBlastRadius(unittest.TestCase):

    COMPLETE_CONTAINED = {
        "direct_call_sites": 1, "wire_shape_reads": 0, "vendor_error_handlers": 0,
        "prompt_or_param_constructions": 0, "auth_config_points": 1,
        "sdk_type_imports_outside_adapter": 0,
        "unit_or_taxonomy_conversions_outside_adapter": 0,
        "observability_fields_bound_to_vendor_schema": 0,
    }

    def test_complete_inventory_produces_a_real_band(self):
        score = portability.swap_blast_radius(self.COMPLETE_CONTAINED, "sys-contained")
        self.assertEqual(score["edit_points"], 2)
        self.assertEqual(score["band"], "CONTAINED")
        self.assertFalse(score["total_is_floor"])
        self.assertEqual(score["uncounted_surfaces_unknown"], [])

    def test_propagating_surfaces_are_weighted_above_one(self):
        inventory = dict(self.COMPLETE_CONTAINED,
                         sdk_type_imports_outside_adapter=3)
        score = portability.swap_blast_radius(inventory, "sys-typed")
        self.assertEqual(score["counted_surfaces"]
                         ["sdk_type_imports_outside_adapter"]["edit_points"], 6)
        self.assertEqual(score["band"], "PARTIAL")

    def test_empty_inventory_is_not_contained_and_is_not_zero_evidence(self):
        """The single most important assertion in this file.

        An un-inventoried system scores 0 edit points. It must NOT come out as
        CONTAINED -- 'we counted nothing' and 'there is nothing to count' are
        different facts, and conflating them is how a swap gets sold as cheap.
        """
        score = portability.swap_blast_radius({}, "sys-uninventoried")
        self.assertEqual(score["edit_points"], 0)
        self.assertTrue(score["total_is_floor"])
        self.assertEqual(score["band"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(len(score["uncounted_surfaces_unknown"]),
                         len(portability.SURFACES))

    def test_partial_inventory_reports_a_floor_not_a_total(self):
        score = portability.swap_blast_radius(
            {"direct_call_sites": 2, "auth_config_points": 1}, "sys-partial")
        self.assertEqual(score["edit_points"], 3)
        self.assertTrue(score["total_is_floor"])
        self.assertEqual(score["band"], "INSUFFICIENT_EVIDENCE")
        self.assertIn("wire_shape_reads", score["uncounted_surfaces_unknown"])

    def test_malformed_count_raises_rather_than_coercing(self):
        with self.assertRaises(ValueError):
            portability.swap_blast_radius({"direct_call_sites": "not counted yet"}, "x")
        with self.assertRaises(ValueError):
            portability.swap_blast_radius({"direct_call_sites": -1}, "x")

    def test_unexpected_keys_are_reported_not_silently_dropped(self):
        score = portability.swap_blast_radius(
            dict(self.COMPLETE_CONTAINED, made_up_surface=4), "sys-extra")
        self.assertEqual(score["unexpected_keys_ignored"], ["made_up_surface"])


class TestStaticIndependenceScan(unittest.TestCase):

    def test_portable_caller_is_clean(self):
        result = portability.scan_module_independence(
            os.path.join(HERE, "portlib", "caller.py"))
        self.assertTrue(result["independent"], result["violations"])
        self.assertEqual(result["violation_count"], 0)

    def test_leaky_negative_control_is_caught(self):
        """A scanner that has never caught anything is not evidence."""
        result = portability.scan_module_independence(
            os.path.join(HERE, "portlib", "caller_leaky.py"))
        self.assertFalse(result["independent"])
        self.assertGreaterEqual(result["violation_count"], 4)
        self.assertIn("fake_alpha", result["distinct_symbols"])
        self.assertIn("AlphaTimeout", result["distinct_symbols"])
        for violation in result["violations"]:
            self.assertGreater(violation["line"], 0)


# ------------------------------------------------------- the worked swap

class TestProviderSwapRequiresNoCallerChange(unittest.TestCase):

    def test_same_caller_source_serves_both_providers(self):
        before = caller.caller_source_sha256()
        alpha = caller.route_documents(
            AlphaClassificationAdapter(POLICY), DOCS, POLICY)
        middle = caller.caller_source_sha256()
        beta = caller.route_documents(
            BetaClassificationAdapter(POLICY), DOCS, POLICY)
        after = caller.caller_source_sha256()
        self.assertEqual(before, middle)
        self.assertEqual(middle, after)
        self.assertEqual(len(alpha), len(DOCS))
        self.assertEqual(len(beta), len(DOCS))

    def test_both_providers_satisfy_the_same_contract(self):
        for factory in (AlphaClassificationAdapter, BetaClassificationAdapter):
            with self.subTest(provider=factory.__name__):
                result = check_conformance(factory(POLICY), POLICY)
                self.assertTrue(result["conformant"], result["findings"])

    def test_adapters_normalize_confidence_to_the_same_scale(self):
        """BETA speaks percent, ALPHA speaks fraction. Callers must never know."""
        probe = Document("p", "my badge stopped working")
        for factory in (AlphaClassificationAdapter, BetaClassificationAdapter):
            with self.subTest(provider=factory.__name__):
                result = factory(POLICY).classify(probe)
                self.assertIsInstance(result, Classification)
                self.assertIsInstance(result.confidence, float)
                self.assertTrue(0.0 <= result.confidence <= 1.0)
                self.assertEqual(result.category, "access")

    def test_beta_provider_taxonomy_is_mapped_not_leaked(self):
        result = BetaClassificationAdapter(POLICY).classify(
            Document("p", "there is a leak in the lobby"))
        self.assertEqual(result.category, "facilities")
        self.assertNotIn("BUILDING_OPS", result.category)

    def test_unmappable_answer_raises_instead_of_guessing(self):
        with self.assertRaises(ProviderContractViolation):
            BetaClassificationAdapter(POLICY, fail_mode="garbage").classify(DOCS[0])
        with self.assertRaises(ProviderContractViolation):
            AlphaClassificationAdapter(POLICY, fail_mode="garbage").classify(DOCS[0])


class TestFailureBehavior(unittest.TestCase):
    """What happens when the capability is slow, unavailable, or answers nonsense."""

    def test_vendor_exceptions_are_translated_at_the_wall(self):
        with self.assertRaises(ProviderTimeout):
            AlphaClassificationAdapter(POLICY, fail_mode="timeout").classify(DOCS[0])
        with self.assertRaises(ProviderUnavailable):
            AlphaClassificationAdapter(POLICY, fail_mode="refused").classify(DOCS[0])
        with self.assertRaises(ProviderTimeout):
            BetaClassificationAdapter(POLICY, fail_mode="slow").classify(DOCS[0])
        with self.assertRaises(ProviderUnavailable):
            BetaClassificationAdapter(POLICY, fail_mode="down").classify(DOCS[0])

    def test_slow_capability_routes_everything_to_a_person_and_raises_nothing(self):
        decisions = caller.route_documents(
            AlphaClassificationAdapter(POLICY, fail_mode="timeout"), DOCS, POLICY)
        self.assertEqual(len(decisions), len(DOCS))
        for decision in decisions:
            self.assertTrue(decision.degraded)
            self.assertTrue(decision.needs_human_review)
            self.assertEqual(decision.queue, POLICY.human_review_queue)

    def test_unavailable_capability_never_fabricates_a_category(self):
        decisions = caller.route_documents(
            BetaClassificationAdapter(POLICY, fail_mode="down"), DOCS, POLICY)
        queues = {d.queue for d in decisions}
        self.assertEqual(queues, {POLICY.human_review_queue})
        for category in POLICY.categories:
            self.assertNotIn(f"queue.{category}", queues)
        self.assertIn("retry after", decisions[0].reason)

    def test_contract_violation_is_degraded_not_a_low_confidence_guess(self):
        decisions = caller.route_documents(
            AlphaClassificationAdapter(POLICY, fail_mode="garbage"), DOCS, POLICY)
        for decision in decisions:
            self.assertTrue(decision.degraded)
            self.assertIn("missing evidence", decision.reason)

    def test_healthy_run_does_auto_route_so_degradation_is_distinguishable(self):
        summary = caller.summarize_run(
            caller.route_documents(AlphaClassificationAdapter(POLICY), DOCS, POLICY))
        self.assertGreater(summary["auto_routed"], 0)
        self.assertEqual(summary["degraded"], 0)

    def test_always_review_policy_overrides_high_confidence(self):
        decisions = caller.route_documents(
            AlphaClassificationAdapter(POLICY), [DOCS[0]], POLICY)
        self.assertTrue(decisions[0].needs_human_review)
        self.assertFalse(decisions[0].degraded)  # policy, not a failure
        self.assertIn("always reviewed by policy", decisions[0].reason)


# -------------------------------------------------------------- worksheet

class TestWorksheet(unittest.TestCase):

    BASE = {
        "answer_useful_within": "only_in_session", "consequential": False,
        "degraded_answer_exists": True, "peak_items_per_hour": 100,
        "reviewer_capacity_items_per_hour": 200, "staged_copies_permitted": True,
        "durable_queue_available": True,
        "single_owner_for_deadline_and_fallback": True,
        "payload_contains_restricted_content": False, "baseline_measured": True,
    }

    def _evaluate(self, **overrides):
        answers = dict(self.BASE)
        for key, value in overrides.items():
            if value is None:
                answers.pop(key, None)
            else:
                answers[key] = value
        return worksheet_mod.evaluate({"workflow_id": "T", "name": "T",
                                       "answers": answers})

    def test_missing_decisive_answer_yields_undetermined_not_supported(self):
        """Missing evidence is not a pass. This is the worksheet's core rule."""
        result = self._evaluate(degraded_answer_exists=None)
        pattern_a = result["patterns"]["A_SYNCHRONOUS_IN_REQUEST"]
        self.assertEqual(pattern_a["fit"], "UNDETERMINED")
        self.assertIn("degraded_answer_exists", pattern_a["blocked_by_unknown"])

    def test_missing_evidence_is_also_not_a_failure(self):
        """UNDETERMINED must be distinct from DISQUALIFIED in both directions."""
        result = self._evaluate(answer_useful_within="days",
                                staged_copies_permitted=None)
        pattern_b = result["patterns"]["B_ASYNCHRONOUS_QUEUED_BATCH"]
        self.assertEqual(pattern_b["fit"], "UNDETERMINED")
        self.assertIn("staged_copies_permitted", pattern_b["blocked_by_unknown"])

    def test_explicit_no_disqualifies_where_unknown_only_blocks(self):
        stated = self._evaluate(answer_useful_within="hours",
                                staged_copies_permitted=False)
        self.assertEqual(stated["patterns"]["B_ASYNCHRONOUS_QUEUED_BATCH"]["fit"],
                         "DISQUALIFIED")

    def test_measured_capacity_overrun_disqualifies_the_review_pattern(self):
        result = self._evaluate(consequential=True, peak_items_per_hour=30,
                                reviewer_capacity_items_per_hour=12)
        pattern_c = result["patterns"]["C_HUMAN_IN_THE_LOOP_REVIEW"]
        self.assertEqual(pattern_c["fit"], "DISQUALIFIED")
        self.assertTrue(any("rubber stamp" in d["reason"]
                            for d in pattern_c["disqualifiers"]))

    def test_unknown_capacity_does_not_become_capacity_is_fine(self):
        result = self._evaluate(consequential=True,
                                reviewer_capacity_items_per_hour=None)
        pattern_c = result["patterns"]["C_HUMAN_IN_THE_LOOP_REVIEW"]
        self.assertEqual(result["derived_review_capacity_overrun"], "UNKNOWN")
        self.assertEqual(pattern_c["fit"], "UNDETERMINED")

    def test_malformed_answers_are_discarded_named_and_never_supported(self):
        """Hostile input: wrong types plus a key that is not in the question set."""
        result = worksheet_mod.evaluate({
            "workflow_id": "BAD", "name": "malformed",
            "answers": {"answer_useful_within": "someday", "consequential": "yes",
                        "peak_items_per_hour": "lots", "favourite_colour": "umber"}})
        self.assertEqual(result["unexpected_answer_keys_ignored"], ["favourite_colour"])
        self.assertEqual(len(result["invalid_answers_discarded"]), 3)
        for pattern_id in patterns_mod.PATTERN_ORDER:
            self.assertNotEqual(result["patterns"][pattern_id]["fit"], "SUPPORTED")
            self.assertNotEqual(result["patterns"][pattern_id]["fit"],
                                "SUPPORTED_WITH_CAUTIONS")
        self.assertIn("consequential", result["unanswered_questions"])

    def test_every_verdict_names_the_question_that_produced_it(self):
        result = self._evaluate()
        for pattern_id in patterns_mod.PATTERN_ORDER:
            entry = result["patterns"][pattern_id]
            for bucket in ("supports", "cautions", "disqualifiers"):
                for item in entry[bucket]:
                    self.assertIn(item["question"], worksheet_mod.QUESTION_BY_ID)
                    self.assertTrue(item["reason"])

    def test_unresolved_evidence_only_carried_for_live_patterns(self):
        result = self._evaluate(answer_useful_within="days")
        self.assertEqual(result["patterns"]["A_SYNCHRONOUS_IN_REQUEST"]["fit"],
                         "DISQUALIFIED")
        carried = {e["pattern_id"] for e in result["unresolved_evidence"]}
        self.assertNotIn("A_SYNCHRONOUS_IN_REQUEST", carried)
        self.assertTrue(carried)

    def test_csv_has_one_row_per_workflow_and_pattern(self):
        evaluations = [self._evaluate(), self._evaluate(consequential=True)]
        rows = worksheet_mod.render_worksheet_csv(evaluations).strip().splitlines()
        self.assertEqual(len(rows), 1 + 2 * len(patterns_mod.PATTERN_ORDER))
        self.assertTrue(rows[0].startswith("workflow_id,"))


# ------------------------------------------------------ patterns + fixtures

class TestPatterns(unittest.TestCase):

    def test_all_three_patterns_answer_every_axis(self):
        for pattern_id in patterns_mod.PATTERN_ORDER:
            pattern = patterns_mod.PATTERNS[pattern_id]
            for key, _label in patterns_mod.AXES:
                with self.subTest(pattern=pattern_id, axis=key):
                    self.assertIn(key, pattern)
                    self.assertTrue(pattern[key])

    def test_patterns_are_structurally_different_not_three_flavors_of_one(self):
        shapes = {patterns_mod.PATTERNS[p]["shape"]
                  for p in patterns_mod.PATTERN_ORDER}
        couplings = {patterns_mod.PATTERNS[p]["availability_coupling"][:4]
                     for p in patterns_mod.PATTERN_ORDER}
        self.assertEqual(len(shapes), 3)
        self.assertGreaterEqual(len(couplings), 2)

    def test_every_capability_class_used_is_in_the_closed_vocabulary(self):
        for name in patterns_mod.declared_capability_classes():
            self.assertIn(name, patterns_mod.CAPABILITY_CLASSES)

    def test_each_pattern_carries_a_deterministic_baseline(self):
        for pattern_id in patterns_mod.PATTERN_ORDER:
            pattern = patterns_mod.PATTERNS[pattern_id]
            self.assertIn(pattern["deterministic_baseline_class"],
                          patterns_mod.CAPABILITY_CLASSES)

    def test_each_pattern_lists_unresolved_evidence(self):
        for pattern_id in patterns_mod.PATTERN_ORDER:
            self.assertGreaterEqual(
                len(patterns_mod.PATTERNS[pattern_id]["unresolved_evidence"]), 3)

    def test_rendering_is_deterministic(self):
        self.assertEqual(patterns_mod.render_patterns_markdown(),
                         patterns_mod.render_patterns_markdown())


class TestVendorNeutrality(unittest.TestCase):

    def test_generated_patterns_document_is_clean(self):
        result = patterns_mod.check_vendor_neutrality(
            patterns_mod.render_patterns_markdown(),
            patterns_mod.declared_capability_classes())
        self.assertTrue(result["neutral"], result["findings"])

    def test_tripwire_catches_procurement_language(self):
        """Fictional product name used on purpose; the tell is structural."""
        result = patterns_mod.check_vendor_neutrality(
            "We recommend purchasing Acme Cortex 4.0™ for this workload.",
            ["magic-box"])
        kinds = {f["kind"] for f in result["findings"]}
        self.assertFalse(result["neutral"])
        self.assertIn("trademark_mark", kinds)
        self.assertIn("versioned_proper_noun", kinds)
        self.assertIn("procurement_recommendation", kinds)
        self.assertIn("capability_outside_vocabulary", kinds)

    def test_our_own_identifiers_are_not_false_positives(self):
        result = patterns_mod.check_vendor_neutrality(
            "See UIOWA-080 and NIST AI RMF 1.0 as a reference.", [])
        self.assertTrue(result["neutral"], result["findings"])


class TestFixturesAreConsistentAndLabelled(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "data", "workflows.json"),
                  encoding="utf-8") as handle:
            cls.raw = json.load(handle)
        cls.workflows = cls.raw["workflows"]

    def test_fiction_is_labelled_as_fiction(self):
        self.assertIn("FICTIONAL", self.raw["_fiction_notice"])
        for workflow in self.workflows:
            self.assertIn("FICTIONAL", workflow["fiction_label"])

    def test_fixtures_demonstrate_both_a_strength_and_a_gap(self):
        for workflow in self.workflows[:3]:
            with self.subTest(workflow=workflow["workflow_id"]):
                self.assertIn("STRENGTH", workflow["narrative"])
                self.assertIn("GAP", workflow["narrative"])

    def test_fixture_set_exercises_every_portability_band(self):
        scores = {}
        for workflow in self.workflows:
            try:
                score = portability.swap_blast_radius(
                    workflow.get("code_surface_inventory", {}),
                    workflow["workflow_id"])
            except ValueError:
                scores[workflow["workflow_id"]] = "REJECTED"
                continue
            scores[workflow["workflow_id"]] = score["band"]
        self.assertEqual(scores["HRI-ARCHIVE-02"], "CONTAINED")
        self.assertEqual(scores["HRI-INTAKE-01"], "PERVASIVE")
        self.assertEqual(scores["HRI-AWARD-03"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(scores["HRI-MALFORMED-99"], "REJECTED")

    def test_award_workflow_is_disqualified_by_measured_review_capacity(self):
        award = next(w for w in self.workflows if w["workflow_id"] == "HRI-AWARD-03")
        result = worksheet_mod.evaluate(award)
        self.assertEqual(result["patterns"]["C_HUMAN_IN_THE_LOOP_REVIEW"]["fit"],
                         "DISQUALIFIED")
        self.assertEqual(result["derived_review_capacity_overrun"], "yes")


if __name__ == "__main__":
    unittest.main(verbosity=2)
