"""Tests for the common maturity anchors (UIOWA-021).

Each claim the method makes, turned into an assertion:

  "paperwork alone does not raise the level"  -> N documents still cap at 2
  "a ceiling is not an award"                 -> holding evidence != reaching the level
  "the four patterns stay apart"              -> repeatable / isolated / claim-only / missing
  "unassessed is not a low level"             -> rank is None, never 1
  "one scale across four areas"               -> same evaluator, all four exercised
  "it feeds UIOWA-022"                        -> the declared field names are emitted

Run:  python3 -m unittest -v test_anchors
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest

import anchors
import render_scale

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "worked_examples.json")


def load_raw() -> dict:
    with open(FIXTURE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def evaluated() -> dict:
    return {a.criterion_id: a for a in anchors.evaluate_all(load_raw()["criteria"])}


def criterion(**over) -> dict:
    base = {"criterion_id": "T-1", "area": "development", "service": "ESS", "evidence": []}
    base.update(over)
    return base


def ev(kind, **over) -> dict:
    base = {"kind": kind, "locator": f"fixture://{kind}"}
    base.update(over)
    return base


class TestPaperworkAloneDoesNotRaiseTheLevel(unittest.TestCase):
    """The guardrail the order names."""

    def test_one_document_caps_at_two(self):
        a = anchors.evaluate(criterion(evidence=[ev("policy_document")]))
        self.assertEqual(a.rank, 2)
        self.assertEqual(a.pattern, "policy_only_claim")

    def test_volume_of_documents_buys_nothing(self):
        """Ten policies are still zero instances of practice."""
        for count in (1, 2, 5, 10, 50):
            with self.subTest(documents=count):
                a = anchors.evaluate(criterion(
                    evidence=[ev("policy_document", locator=f"doc-{i}") for i in range(count)]))
                self.assertEqual(a.rank, 2, f"{count} documents changed the level")
                self.assertEqual(a.pattern, "policy_only_claim")

    def test_one_real_record_beats_fifty_documents(self):
        paper = anchors.evaluate(criterion(
            evidence=[ev("policy_document", locator=f"d{i}") for i in range(50)]))
        practice = anchors.evaluate(criterion(evidence=[ev("single_instance")]))
        self.assertGreater(practice.rank, paper.rank)

    def test_an_uncorroborated_interview_statement_stays_at_one(self):
        """Level 1's exit criterion is a practice MORE THAN ONE person recognises.

        One person describing the intended practice is a claim, not a defined
        practice, so it does not clear level 1 on its own.
        """
        a = anchors.evaluate(criterion(evidence=[ev("interview_statement")]))
        self.assertEqual(a.rank, 1)

    def test_a_corroborated_interview_statement_reaches_two_but_no_further(self):
        a = anchors.evaluate(criterion(evidence=[
            ev("interview_statement", states_intended_practice=True)]))
        self.assertEqual(a.rank, 2)
        self.assertEqual(a.pattern, "policy_only_claim",
                         "a statement is still a claim, not a record of the work")

    def test_disagreeing_descriptions_do_not_even_reach_two(self):
        """A ceiling is not an award: holding evidence is not reaching a level."""
        a = anchors.evaluate(criterion(evidence=[
            ev("interview_statement", states_intended_practice=False),
            ev("interview_statement", states_intended_practice=False)]))
        self.assertEqual(a.rank, 1)
        self.assertIn("do not agree", a.cap_reason)

    def test_the_fixture_shows_this_case(self):
        a = evaluated()["DEV-03"]
        self.assertEqual(a.rank, 1)

    def test_an_unknown_evidence_kind_cannot_sneak_past_a_cap(self):
        with self.assertRaises(anchors.AnchorError) as ctx:
            anchors.evaluate(criterion(evidence=[ev("vendor_assurance")]))
        self.assertIn("needs a declared cap", str(ctx.exception))


class TestCeilingIsNotAnAward(unittest.TestCase):
    def test_repeated_records_by_one_person_stay_at_three(self):
        a = anchors.evaluate(criterion(evidence=[
            ev("repeated_instances", instances=30, covers_multiple_actors=False,
               exceptions_recorded=True)]))
        self.assertEqual(a.rank, 3)
        self.assertIn("one individual's habit", a.cap_reason)

    def test_repetition_with_no_exceptions_recorded_stays_at_three(self):
        a = anchors.evaluate(criterion(evidence=[
            ev("repeated_instances", instances=18, covers_multiple_actors=True,
               exceptions_recorded=False)]))
        self.assertEqual(a.rank, 3)
        self.assertIn("exceptions", a.cap_reason)

    def test_an_undefined_measure_does_not_reach_five(self):
        a = anchors.evaluate(criterion(evidence=[
            ev("repeated_instances", instances=9, covers_multiple_actors=True,
               exceptions_recorded=True),
            ev("outcome_measure", measure_defined=False)]))
        self.assertEqual(a.rank, 4)
        self.assertIn("cannot be read", a.cap_reason)

    def test_a_measure_that_changed_nothing_does_not_reach_five(self):
        a = anchors.evaluate(criterion(evidence=[
            ev("repeated_instances", instances=6, covers_multiple_actors=True,
               exceptions_recorded=True),
            ev("outcome_measure", measure_defined=True, change_evidenced=False)]))
        self.assertEqual(a.rank, 4)
        self.assertIn("measuring is not adjusting", a.cap_reason)

    def test_the_full_ladder_reaches_five(self):
        a = anchors.evaluate(criterion(evidence=[
            ev("policy_document"),
            ev("repeated_instances", instances=4, covers_multiple_actors=True,
               exceptions_recorded=True),
            ev("outcome_measure", measure_defined=True, change_evidenced=True)]))
        self.assertEqual(a.rank, 5)
        self.assertIn("top of the scale", a.cap_reason)

    def test_levels_are_contiguous_not_skipped(self):
        """Level 4 is unreachable without level 3's anchor being met."""
        a = anchors.evaluate(criterion(evidence=[
            ev("outcome_measure", measure_defined=True, change_evidenced=True,
               instances=1, covers_multiple_actors=False)]))
        self.assertLessEqual(a.rank, 3)

    def test_every_result_names_why_it_is_not_higher(self):
        for a in evaluated().values():
            self.assertTrue(a.cap_reason.strip(), a.criterion_id)


class TestFourPatternsStayApart(unittest.TestCase):
    def test_each_pattern_is_produced_by_the_fixture(self):
        patterns = {a.pattern for a in evaluated().values()}
        for expected in ("repeatable_practice", "isolated_success", "policy_only_claim",
                         "missing_evidence", "not_applicable", "unassessed"):
            self.assertIn(expected, patterns)

    def test_isolated_success_is_not_repeatable_practice(self):
        one = anchors.evaluate(criterion(evidence=[ev("single_instance", instances=1)]))
        many = anchors.evaluate(criterion(evidence=[
            ev("repeated_instances", instances=12, covers_multiple_actors=True,
               exceptions_recorded=True)]))
        self.assertEqual(one.pattern, "isolated_success")
        self.assertEqual(many.pattern, "repeatable_practice")
        self.assertLess(one.rank, many.rank)

    def test_two_single_instances_become_repeatable(self):
        a = anchors.evaluate(criterion(evidence=[
            ev("single_instance", locator="a"), ev("single_instance", locator="b")]))
        self.assertEqual(a.pattern, "repeatable_practice")
        self.assertEqual(a.rank, 3, "the single_instance ceiling still applies")

    def test_missing_evidence_is_not_a_pattern_of_practice(self):
        a = anchors.evaluate(criterion(evidence=[]))
        self.assertEqual(a.pattern, "missing_evidence")


class TestNotALevelStates(unittest.TestCase):
    def test_unassessed_and_not_applicable_carry_no_rank(self):
        e = evaluated()
        for cid in ("AI-02", "AI-03"):
            self.assertIsNone(e[cid].rank)
        self.assertEqual(e["AI-02"].status, "not_applicable")
        self.assertEqual(e["AI-03"].status, "unassessed")

    def test_no_evidence_is_insufficient_evidence_not_level_one(self):
        a = anchors.evaluate(criterion(evidence=[]))
        self.assertEqual(a.status, "insufficient_evidence")
        self.assertIsNone(a.rank)
        self.assertNotEqual(a.rank, 1)

    def test_level_one_is_a_finding_and_needs_evidence(self):
        """Absent-with-evidence and no-evidence are different answers."""
        absent = anchors.evaluate(criterion(evidence=[
            ev("interview_statement", states_intended_practice=False)]))
        nothing = anchors.evaluate(criterion(evidence=[]))
        self.assertEqual(absent.rank, 1)
        self.assertIsNone(nothing.rank)

    def test_not_applicable_needs_a_stated_reason(self):
        with self.assertRaises(anchors.AnchorError) as ctx:
            anchors.evaluate(criterion(assessment_status="not_applicable"))
        self.assertIn("applicability_reason", str(ctx.exception))

    def test_not_applicable_with_evidence_is_refused(self):
        with self.assertRaises(anchors.AnchorError) as ctx:
            anchors.evaluate(criterion(assessment_status="not_applicable",
                                       applicability_reason="n/a here",
                                       evidence=[ev("policy_document")]))
        self.assertIn("the practice applies", str(ctx.exception))

    def test_no_non_rank_state_ever_gets_a_number(self):
        for status in anchors.NON_RANK_STATUSES:
            extra = {"applicability_reason": "stated"} if status == "not_applicable" else {}
            a = anchors.evaluate(criterion(assessment_status=status, **extra))
            self.assertIsNone(a.rank, status)


class TestOneScaleAcrossFourAreas(unittest.TestCase):
    def test_all_four_areas_are_exercised(self):
        self.assertEqual({a.area for a in evaluated().values()}, set(anchors.AREAS))

    def test_identical_evidence_scores_identically_in_every_area(self):
        """One scale means the area cannot change the answer."""
        evidence = [ev("policy_document"),
                    ev("repeated_instances", instances=5, covers_multiple_actors=True,
                       exceptions_recorded=True)]
        ranks = {area: anchors.evaluate(criterion(area=area, evidence=copy.deepcopy(evidence))).rank
                 for area in anchors.AREAS}
        self.assertEqual(len(set(ranks.values())), 1, ranks)

    def test_an_unknown_area_is_refused(self):
        with self.assertRaises(anchors.AnchorError) as ctx:
            anchors.evaluate(criterion(area="procurement"))
        self.assertIn("is not one of", str(ctx.exception))


class TestHandoffToRatingModel(unittest.TestCase):
    def test_emits_the_field_names_022_declares(self):
        record = evaluated()["DEV-01"].as_rating_model_input()
        for field in ("criterion_id", "area", "service", "assessment_status",
                      "maturity_rank", "maturity_label", "evidence_ids"):
            self.assertIn(field, record)

    def test_rank_is_null_for_every_non_level_status(self):
        payload = json.loads(render_scale.rating_model_input(
            load_raw(), anchors.evaluate_all(load_raw()["criteria"])))
        for record in payload["criteria"]:
            if record["assessment_status"] != "assessed":
                self.assertIsNone(record["maturity_rank"], record["criterion_id"])
            else:
                self.assertIsInstance(record["maturity_rank"], int)

    def test_evidence_ids_are_real_locators(self):
        for a in evaluated().values():
            record = a.as_rating_model_input()
            self.assertEqual(len(record["evidence_ids"]), len(a.evidence))
            for locator in record["evidence_ids"]:
                self.assertTrue(locator.strip())


class TestHostileAndMissingInput(unittest.TestCase):
    def test_duplicate_criterion_id_refused(self):
        raw = load_raw()["criteria"]
        raw = raw + [copy.deepcopy(raw[0])]
        with self.assertRaises(anchors.AnchorError) as ctx:
            anchors.evaluate_all(raw)
        self.assertIn("duplicate criterion_id", str(ctx.exception))

    def test_blank_required_field_refused(self):
        with self.assertRaises(anchors.AnchorError) as ctx:
            anchors.evaluate(criterion(service="   "))
        self.assertIn("blank", str(ctx.exception))

    def test_missing_required_field_refused(self):
        raw = criterion()
        del raw["service"]
        with self.assertRaises(anchors.AnchorError) as ctx:
            anchors.evaluate(raw)
        self.assertIn("missing required field", str(ctx.exception))

    def test_evidence_without_a_locator_refused(self):
        with self.assertRaises(anchors.AnchorError) as ctx:
            anchors.evaluate(criterion(evidence=[{"kind": "policy_document"}]))
        self.assertIn("locator", str(ctx.exception))

    def test_zero_or_negative_instances_refused(self):
        for bad in (0, -3, True, "four"):
            with self.assertRaises(anchors.AnchorError):
                anchors.evaluate(criterion(evidence=[ev("repeated_instances", instances=bad)]))

    def test_unknown_assessment_status_refused(self):
        with self.assertRaises(anchors.AnchorError) as ctx:
            anchors.evaluate(criterion(assessment_status="probably_fine"))
        self.assertIn("must be one of", str(ctx.exception))

    def test_malformed_json_rejected_with_the_path(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("{ nope ")
            path = fh.name
        try:
            with self.assertRaises(anchors.AnchorError) as ctx:
                anchors.load(path)
            self.assertIn("not valid JSON", str(ctx.exception))
        finally:
            os.unlink(path)

    def test_cli_rejects_bad_data_with_exit_code_2(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"criteria": [{"criterion_id": "X"}]}, fh)
            self.assertEqual(render_scale.main(["--data", path, "--out", d]), 2)

    def test_cli_reports_a_missing_file(self):
        self.assertEqual(render_scale.main(["--data", "/nonexistent.json", "--out", "/tmp"]), 2)


class TestRenderedOutput(unittest.TestCase):
    def test_the_scale_document_is_labelled_our_framework(self):
        md = render_scale.scale_markdown()
        self.assertIn("our proposed framework", md.lower())
        self.assertIn("not a University of Iowa finding", md)
        self.assertIn("not an industry standard", md)
        self.assertIn("not a certification scale", md)

    def test_the_scale_documents_every_level_and_anchor(self):
        md = render_scale.scale_markdown()
        for level in anchors.LEVELS:
            self.assertIn(level["label"], md)
            self.assertIn(level["measures"], md)
            for anchor in level["observable_anchors"]:
                self.assertIn(anchor, md)

    def test_the_scale_documents_every_ceiling(self):
        md = render_scale.scale_markdown()
        for key, kind in anchors.EVIDENCE_KINDS.items():
            self.assertIn(key, md)
            self.assertIn(kind["why"], md)

    def test_examples_are_labelled_synthetic(self):
        doc = load_raw()
        md = render_scale.examples_markdown(doc, anchors.evaluate_all(doc["criteria"]))
        self.assertIn("SYNTHETIC", md)
        self.assertIn("Not University of Iowa findings", md)

    def test_csv_writes_null_not_an_empty_rank(self):
        csv = render_scale.examples_csv(anchors.evaluate_all(load_raw()["criteria"]))
        for line in csv.splitlines()[1:]:
            fields = line.split(",")
            self.assertTrue(fields[4].strip(), "an empty rank cell reads as zero")

    def test_no_certification_or_compliance_language(self):
        blob = (render_scale.scale_markdown() + render_scale.examples_markdown(
            load_raw(), anchors.evaluate_all(load_raw()["criteria"]))).lower()
        for forbidden in ("certified", "compliant with", "percentile", "accredited"):
            self.assertNotIn(forbidden, blob)

    def test_render_is_byte_identical_across_runs(self):
        doc = load_raw()
        a = anchors.evaluate_all(doc["criteria"])
        b = anchors.evaluate_all(load_raw()["criteria"])
        self.assertEqual(render_scale.examples_markdown(doc, a),
                         render_scale.examples_markdown(doc, b))
        self.assertEqual(render_scale.rating_model_input(doc, a),
                         render_scale.rating_model_input(doc, b))

    def test_cli_check_runs_clean(self):
        self.assertEqual(render_scale.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
