#!/usr/bin/env python3
"""Tests for the cross-output agreement checker (UIOWA-117).

Run:  python3 -m unittest -v test_output_agreement.py

The shape of this suite is deliberate. A consistency checker is only worth
trusting if three things hold together:

  1. the consistent bundle is clean,
  2. each deliberate defect produces its own named diagnostic, and
  3. correcting the derived values returns the bundle to clean.

Any one of those alone proves nothing. A checker that only passes on good input
has not been tested; a checker that only fires on broken input might be firing
on everything.
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest

import output_agreement as oa
import make_bundle as mb

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")


def codes(ds):
    return {d.code for d in ds}


class ConsistentBundleTests(unittest.TestCase):
    def test_generated_consistent_bundle_is_clean(self):
        ds = oa.check_bundle(mb.consistent_bundle())
        self.assertEqual([], oa.errors(ds), "\n".join(str(d) for d in ds))

    def test_shipped_consistent_fixture_is_clean(self):
        b = oa.load_bundle(os.path.join(FIXTURES, "consistent"))
        ds = oa.check_bundle(b)
        self.assertEqual([], oa.errors(ds), "\n".join(str(d) for d in ds))

    def test_consistent_bundle_has_no_warnings_either(self):
        ds = oa.check_bundle(mb.consistent_bundle())
        self.assertEqual([], ds, "\n".join(str(d) for d in ds))

    def test_round_trip_through_disk_preserves_agreement(self):
        with tempfile.TemporaryDirectory() as td:
            oa.save_bundle(mb.consistent_bundle(), td)
            reloaded = oa.load_bundle(td)
            self.assertEqual([], oa.errors(oa.check_bundle(reloaded)))
            self.assertEqual(11, len(reloaded.matrix))
            self.assertEqual(6, len(reloaded.register))

    def test_regenerating_an_already_consistent_bundle_changes_nothing(self):
        b = mb.consistent_bundle()
        again = oa.regenerate_derived(b)
        self.assertEqual(b.summary, again.summary)
        self.assertEqual(b.presentation, again.presentation)


class DeliberateMismatchTests(unittest.TestCase):
    """Every defect fires its own diagnostic, naming both artifacts and the field."""

    def test_every_defect_produces_its_expected_code(self):
        for name, (code, _, _) in sorted(mb.DEFECTS.items()):
            with self.subTest(defect=name):
                ds = oa.check_bundle(mb.build_defect(name))
                self.assertIn(code, codes(ds),
                              f"{name} did not produce {code}; got {sorted(codes(ds))}")

    def test_every_diagnostic_names_the_conflicting_artifacts_and_field(self):
        """The completion condition: diagnostics name artifacts AND fields."""
        for name in sorted(mb.DEFECTS):
            with self.subTest(defect=name):
                for d in oa.check_bundle(mb.build_defect(name)):
                    self.assertTrue(d.artifacts, f"{d.code} names no artifact")
                    for a in d.artifacts:
                        self.assertIn(a, oa.ARTIFACTS, f"{d.code} names unknown artifact {a}")
                    self.assertTrue(d.field_name, f"{d.code} names no field")
                    self.assertTrue(d.detail, f"{d.code} carries no detail")
                    self.assertTrue(d.subject, f"{d.code} names no subject")

    def test_cross_artifact_defects_name_both_sides(self):
        """A diagnostic saying only 'the deck is wrong' is not actionable."""
        for name in ("count_mismatch", "state_mismatch", "phase_mismatch",
                     "estimate_mismatch", "estimate_fabricated", "phase_fabricated",
                     "unassessed_result_claimed"):
            with self.subTest(defect=name):
                code = mb.DEFECTS[name][0]
                hit = [d for d in oa.check_bundle(mb.build_defect(name)) if d.code == code]
                self.assertTrue(hit)
                self.assertEqual(2, len(hit[0].artifacts),
                                 f"{code} should name both conflicting artifacts")

    def test_count_mismatch_reports_both_numbers(self):
        ds = oa.check_bundle(mb.build_defect("count_mismatch"))
        d = next(x for x in ds if x.code == "COUNT_MISMATCH")
        self.assertIn("3", d.detail)
        self.assertIn("5", d.detail)
        self.assertIn(oa.SUMMARY, d.artifacts)
        self.assertIn(oa.MATRIX, d.artifacts)

    def test_estimate_fabricated_is_distinguished_from_a_mere_mismatch(self):
        """UNKNOWN -> a number is a different defect from two different numbers."""
        fab = codes(oa.check_bundle(mb.build_defect("estimate_fabricated")))
        mis = codes(oa.check_bundle(mb.build_defect("estimate_mismatch")))
        self.assertIn("ESTIMATE_FABRICATED", fab)
        self.assertNotIn("ESTIMATE_MISMATCH", fab)
        self.assertIn("ESTIMATE_MISMATCH", mis)
        self.assertNotIn("ESTIMATE_FABRICATED", mis)

    def test_unassessed_result_claimed_is_distinguished_from_a_state_mismatch(self):
        """Stating a result for a cell nobody assessed is not the same error as
        disagreeing about an assessed one."""
        unassessed = codes(oa.check_bundle(mb.build_defect("unassessed_result_claimed")))
        mismatch = codes(oa.check_bundle(mb.build_defect("state_mismatch")))
        self.assertIn("UNASSESSED_RESULT_CLAIMED", unassessed)
        self.assertNotIn("STATE_MISMATCH", unassessed)
        self.assertIn("STATE_MISMATCH", mismatch)
        self.assertNotIn("UNASSESSED_RESULT_CLAIMED", mismatch)

    def test_phase_fabricated_catches_an_unsequenced_item_gaining_a_phase(self):
        ds = oa.check_bundle(mb.build_defect("phase_fabricated"))
        d = next(x for x in ds if x.code == "PHASE_FABRICATED")
        self.assertIn("REC-SYN-IAM-AI-001", d.detail)
        self.assertIn("0-90", d.detail)

    def test_dangling_id_names_the_missing_identifier(self):
        ds = oa.check_bundle(mb.build_defect("dangling_id"))
        d = next(x for x in ds if x.code == "DANGLING_ID")
        self.assertIn("FND-SYN-ESS-XX-999", d.detail)

    def test_unknown_count_set_is_a_warning_not_a_silent_pass(self):
        ds = oa.check_bundle(mb.build_defect("unknown_count_set"))
        d = next(x for x in ds if x.code == "UNKNOWN_COUNT_SET")
        self.assertEqual(oa.WARN, d.severity)
        self.assertIn("cells_we_liked", d.detail)

    def test_each_defect_is_isolated_to_its_declared_codes(self):
        """A fixture that triggers five diagnostics proves nothing about any of them.

        One defect legitimately cascades: a duplicated matrix row really does
        invalidate every count taken over the matrix. That cascade is declared in
        EXPECTED_CASCADE, so a new one fails this test and has to be justified
        rather than quietly tolerated.
        """
        for name, (code, _, _) in sorted(mb.DEFECTS.items()):
            with self.subTest(defect=name):
                expected = {code} | mb.EXPECTED_CASCADE.get(name, set())
                got = codes(oa.check_bundle(mb.build_defect(name)))
                self.assertEqual(expected, got,
                                 f"{name} should produce {sorted(expected)}, got {sorted(got)}")

    def test_the_declared_cascade_is_real_and_not_a_checker_artifact(self):
        """The duplicated row must actually change the count it is said to break."""
        good = mb.consistent_bundle()
        dup = mb.build_defect("duplicate_id")
        self.assertEqual(10, good.count_set("assessed_cells"))
        self.assertEqual(11, dup.count_set("assessed_cells"))
        d = next(x for x in oa.check_bundle(dup) if x.code == "COUNT_MISMATCH")
        self.assertIn("11", d.detail)

    def test_shipped_mismatch_fixtures_match_the_generator(self):
        for name, (code, _, _) in sorted(mb.DEFECTS.items()):
            with self.subTest(defect=name):
                path = os.path.join(FIXTURES, "mismatched", name)
                self.assertTrue(os.path.isdir(path), f"fixture {name} is not checked in")
                self.assertIn(code, codes(oa.check_bundle(oa.load_bundle(path))))


class RegenerationTests(unittest.TestCase):
    """'Actual regenerated examples agree after correction' - executed, not asserted."""

    def test_regeneration_clears_exactly_the_codes_it_contracts_to_clear(self):
        for name, (code, clears, _) in sorted(mb.DEFECTS.items()):
            with self.subTest(defect=name):
                b = mb.build_defect(name)
                self.assertIn(code, codes(oa.check_bundle(b)))
                after = codes(oa.check_bundle(oa.regenerate_derived(b)))
                if clears:
                    self.assertNotIn(code, after,
                                     f"regeneration should have corrected {code}")
                else:
                    self.assertIn(code, after,
                                  f"{code} has no source to regenerate from and must persist")

    def test_derived_defects_regenerate_to_a_fully_clean_bundle(self):
        for name, (code, clears, _) in sorted(mb.DEFECTS.items()):
            if not clears:
                continue
            with self.subTest(defect=name):
                fixed = oa.regenerate_derived(mb.build_defect(name))
                self.assertEqual([], oa.errors(oa.check_bundle(fixed)))

    def test_regeneration_does_not_rewrite_human_prose(self):
        """It corrects the numbers, not the writing. Silently editing an author's
        sentence to match the data would hide the disagreement, not resolve it."""
        b = mb.build_defect("count_mismatch")
        before = [c["text"] for c in b.summary["claims"]]
        fixed = oa.regenerate_derived(b)
        self.assertEqual(before, [c["text"] for c in fixed.summary["claims"]])
        # The prose still says "Three" while the value is corrected to 5 - which is
        # exactly the state a human must review. The checker does not pretend to
        # have fixed the sentence.
        self.assertIn("Three", fixed.summary["claims"][1]["text"])
        self.assertEqual(5, fixed.summary["claims"][1]["asserted_count"]["value"])

    def test_regeneration_cannot_invent_a_source(self):
        """A dangling citation must survive regeneration. Clearing it would be the
        checker fabricating agreement."""
        b = mb.build_defect("dangling_id")
        fixed = oa.regenerate_derived(b)
        self.assertIn("DANGLING_ID", codes(oa.check_bundle(fixed)))

    def test_regeneration_never_promotes_an_unassessed_cell(self):
        b = mb.build_defect("unassessed_result_claimed")
        fixed = oa.regenerate_derived(b)
        claim = next(c for c in fixed.presentation["claims"] if c["claim_id"] == "PS-05")
        self.assertEqual("UNKNOWN", claim["asserted_state"]["status"])

    def test_regeneration_restores_unknown_over_a_fabricated_estimate(self):
        b = mb.build_defect("estimate_fabricated")
        fixed = oa.regenerate_derived(b)
        claim = next(c for c in fixed.summary["claims"] if c["claim_id"] == "ES-06")
        self.assertTrue(claim["asserted_estimate"]["estimate"].startswith("UNKNOWN"))


class HostileInputTests(unittest.TestCase):
    def test_empty_bundle_reports_every_artifact_missing_and_does_not_crash(self):
        ds = oa.check_bundle(oa.Bundle())
        self.assertIn("ARTIFACT_EMPTY", codes(ds))
        self.assertEqual(4, len([d for d in ds if d.code == "ARTIFACT_EMPTY"]))

    def test_missing_bundle_directory_loads_empty_rather_than_raising(self):
        b = oa.load_bundle("/nonexistent-bundle-path")
        self.assertEqual([], b.matrix)
        self.assertTrue(oa.errors(oa.check_bundle(b)))

    def test_claims_with_no_assertions_are_not_errors(self):
        """A purely narrative claim asserts nothing checkable. That is allowed."""
        b = mb.consistent_bundle()
        b.summary["claims"].append({"claim_id": "ES-99", "text": "Context paragraph."})
        self.assertEqual([], oa.errors(oa.check_bundle(b)))

    def test_matrix_row_missing_status_counts_as_unassessed_not_as_a_result(self):
        b = mb.consistent_bundle()
        b.matrix.append({"finding_id": "FND-SYN-RIS-AI-001", "group": "RIS",
                         "area": "AI", "status": "", "confidence": "", "statement": ""})
        self.assertEqual(10, b.count_set("assessed_cells"))
        self.assertEqual(2, b.count_set("unassessed_cells"))

    def test_blank_status_cannot_be_reported_as_a_result(self):
        b = mb.consistent_bundle()
        b.matrix.append({"finding_id": "FND-SYN-RIS-AI-001", "group": "RIS", "area": "AI",
                         "status": "", "confidence": "", "statement": ""})
        b.presentation["claims"].append({
            "claim_id": "PS-98", "slide_id": "S9", "text": "RIS AI readiness is solid.",
            "asserted_state": {"finding_id": "FND-SYN-RIS-AI-001", "status": "SUPPORTED"}})
        self.assertIn("UNASSESSED_RESULT_CLAIMED", codes(oa.check_bundle(b)))

    def test_unicode_and_multiline_text_survive_a_disk_round_trip(self):
        b = mb.consistent_bundle()
        b.summary["claims"][0]["text"] = "Ünicode — line one\nline two\ttabbed"
        with tempfile.TemporaryDirectory() as td:
            oa.save_bundle(b, td)
            back = oa.load_bundle(td)
            self.assertEqual("Ünicode — line one\nline two\ttabbed",
                             back.summary["claims"][0]["text"])
            self.assertEqual([], oa.errors(oa.check_bundle(back)))

    def test_recommendation_citing_a_nonexistent_finding_is_caught(self):
        b = mb.consistent_bundle()
        b.register[0]["finding_refs"] = "FND-DOES-NOT-EXIST"
        ds = oa.check_bundle(b)
        self.assertIn("DANGLING_ID", codes(ds))
        d = next(x for x in ds if x.code == "DANGLING_ID")
        self.assertEqual("finding_refs", d.field_name)

    def test_unknown_countable_set_never_silently_passes(self):
        b = mb.consistent_bundle()
        b.summary["claims"][0]["asserted_count"]["of"] = "nonexistent_set"
        self.assertIn("UNKNOWN_COUNT_SET", codes(oa.check_bundle(b)))


class SetDefinitionTests(unittest.TestCase):
    def test_every_countable_set_is_documented_and_computable(self):
        b = mb.consistent_bundle()
        for name in oa.COUNTABLE_SETS:
            with self.subTest(set=name):
                self.assertTrue(oa.COUNTABLE_SETS[name], "set has no written definition")
                self.assertIsNotNone(b.count_set(name))

    def test_assessed_and_unassessed_partition_the_matrix(self):
        b = mb.consistent_bundle()
        self.assertEqual(len(b.matrix),
                         b.count_set("assessed_cells") + b.count_set("unassessed_cells"))

    def test_unassessed_cells_are_excluded_from_assessed_count(self):
        b = mb.consistent_bundle()
        self.assertEqual(10, b.count_set("assessed_cells"))
        self.assertEqual(1, b.count_set("unassessed_cells"))
        self.assertEqual(11, b.count_set("findings"))


class CliTests(unittest.TestCase):
    def test_cli_exits_nonzero_on_a_mismatched_bundle(self):
        self.assertEqual(1, oa.main([os.path.join(FIXTURES, "mismatched", "count_mismatch")]))

    def test_cli_exits_zero_on_the_consistent_bundle(self):
        self.assertEqual(0, oa.main([os.path.join(FIXTURES, "consistent")]))

    def test_cli_regenerate_writes_a_corrected_bundle_that_passes(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "corrected")
            rc = oa.main([os.path.join(FIXTURES, "mismatched", "state_mismatch"),
                          "--regenerate", out])
            self.assertEqual(0, rc)
            self.assertEqual([], oa.errors(oa.check_bundle(oa.load_bundle(out))))

    def test_cli_regenerate_still_fails_on_a_defect_it_cannot_correct(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "corrected")
            rc = oa.main([os.path.join(FIXTURES, "mismatched", "dangling_id"),
                          "--regenerate", out])
            self.assertEqual(1, rc, "a dangling citation must not be reported as corrected")

    def test_json_output_is_parseable(self):
        b = mb.build_defect("count_mismatch")
        payload = json.dumps([d.as_dict() for d in oa.check_bundle(b)])
        self.assertTrue(json.loads(payload))


class FictionLabelTests(unittest.TestCase):
    def test_prose_artifacts_are_labeled_synthetic(self):
        b = mb.consistent_bundle()
        for doc in (b.summary, b.presentation):
            self.assertIn("SYNTHETIC", doc.get("status", ""))
            self.assertIn("NOT A UNIVERSITY FINDING", doc.get("status", ""))

    def test_identifiers_carry_the_synthetic_marker(self):
        b = mb.consistent_bundle()
        for r in b.matrix:
            self.assertIn("SYN", r["finding_id"])
        for r in b.register:
            self.assertIn("SYN", r["recommendation_id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
