#!/usr/bin/env python3
"""Regression tests for the cross-lane UNKNOWN-propagation screen.

A screen only ever run against clean input has not been tested, so the two-lane
fixture carries planted conflicts and the suite asserts each one is found.

Run:  python3 -m unittest -v test_scan_unknowns.py
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

import scan_unknowns
from scan_unknowns import (
    CONSISTENT,
    CROSS_LANE,
    EMPTY,
    INCOMPLETE,
    INTRA_LANE_VARIANT,
    KNOWN,
    UNKNOWN,
    UNKNOWN_BECAME_ZERO,
    UNKNOWN_HARDENED,
    ZERO,
    Claim,
    Crosswalk,
    ScanError,
    analyze,
    claims_from_csv,
    claims_from_json,
    classify_value,
    collect_claims,
    render_markdown,
    to_csv_rows,
    tree_digest,
    unknown_vocabulary_census,
    verify_readonly,
    vocabulary_divergence,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")


def scan_fixtures():
    claims, unreadable = collect_claims(FIXTURES, "lane_")
    return analyze(claims), claims, unreadable


def finding_for(result, identifier, field):
    for finding in result["findings"]:
        if finding["identifier"] == identifier and finding["aligned_field"] == field:
            return finding
    return None


# ---------------------------------------------------------------------------
# Value classification
# ---------------------------------------------------------------------------


class ClassificationTests(unittest.TestCase):
    def test_zero_is_its_own_class_not_known(self):
        """A zero opposite an unknown is the dangerous case, so it is separable."""
        self.assertEqual(classify_value(0), ZERO)
        self.assertEqual(classify_value(0.0), ZERO)
        self.assertEqual(classify_value("0"), ZERO)
        self.assertEqual(classify_value("$0.00"), ZERO)
        self.assertEqual(classify_value(3), KNOWN)
        self.assertNotEqual(classify_value(0), classify_value(3))

    def test_null_and_unknown_markers_classify_as_unknown(self):
        for value in (None, "UNKNOWN", "unknown", "NOT_RANKED", "TBD", "N/A"):
            with self.subTest(value=value):
                self.assertEqual(classify_value(value), UNKNOWN)

    def test_incomplete_is_kept_separate_from_unknown(self):
        """PARTIAL does not mean nobody looked.

        Folding 'incomplete' into 'never estimated' would be the same conflation
        this screen exists to detect, committed by the screen itself.
        """
        self.assertEqual(classify_value("PARTIAL"), INCOMPLETE)
        self.assertEqual(classify_value("UNRESOLVED"), INCOMPLETE)
        self.assertEqual(classify_value("HOLD"), INCOMPLETE)
        self.assertNotEqual(classify_value("PARTIAL"), classify_value("UNKNOWN"))
        # But both count as unsettled for the hardening check.
        self.assertIn(classify_value("PARTIAL"), scan_unknowns.UNSETTLED)
        self.assertIn(classify_value("UNKNOWN"), scan_unknowns.UNSETTLED)

    def test_empty_string_is_not_unknown(self):
        """An empty cell is ambiguous; it is not evidence of a recorded unknown."""
        self.assertEqual(classify_value(""), EMPTY)
        self.assertEqual(classify_value("   "), EMPTY)
        self.assertNotIn(classify_value(""), scan_unknowns.UNSETTLED)

    def test_booleans_are_known_not_zero(self):
        self.assertEqual(classify_value(False), KNOWN)
        self.assertEqual(classify_value(True), KNOWN)


# ---------------------------------------------------------------------------
# The planted conflicts
# ---------------------------------------------------------------------------


class PlantedConflictTests(unittest.TestCase):
    """The detector is proven on positives, not only on a clean tree."""

    def setUp(self):
        self.result, self.claims, self.unreadable = scan_fixtures()

    def test_fixture_parses_cleanly(self):
        self.assertEqual(self.unreadable, [])
        self.assertTrue(self.claims)

    def test_unknown_that_became_a_zero_is_found(self):
        """The highest-severity case, planted deliberately."""
        finding = finding_for(self.result, "REC-SYN-FIX-001", "effort_hours")
        self.assertIsNotNone(finding)
        self.assertEqual(finding["verdict"], UNKNOWN_BECAME_ZERO)
        self.assertEqual(finding["scope"], CROSS_LANE)
        self.assertEqual(finding["unknown_lanes"], ["lane_alpha"])
        self.assertEqual(finding["valued_lanes"], ["lane_beta"])
        values = {row["value"] for row in finding["evidence_summary"]}
        self.assertIn("0", values)
        self.assertIn("null", values)

    def test_unknown_that_became_a_number_is_found(self):
        finding = finding_for(self.result, "REC-SYN-FIX-002", "effort_hours")
        self.assertIsNotNone(finding)
        self.assertEqual(finding["verdict"], UNKNOWN_HARDENED)
        self.assertEqual(finding["scope"], CROSS_LANE)

    def test_agreement_is_reported_as_consistent_not_omitted(self):
        """The comparison that succeeded is visible, not only its failures."""
        finding = finding_for(self.result, "REC-SYN-FIX-004", "effort_hours")
        self.assertIsNotNone(finding)
        self.assertEqual(finding["verdict"], CONSISTENT)
        self.assertIn("Nothing to resolve", finding["resolution"])

    def test_different_unknown_spellings_still_count_as_agreement(self):
        """`NEEDS_ESTIMATE` and `NOT_ASSESSED` are the same statement."""
        finding = finding_for(self.result, "REC-SYN-FIX-004", "priority")
        self.assertEqual(finding["verdict"], CONSISTENT)
        values = {row["value"] for row in finding["evidence_summary"]}
        self.assertEqual(values, {"NEEDS_ESTIMATE", "NOT_ASSESSED"})

    def test_a_field_both_lanes_agree_on_raises_nothing(self):
        """REC-SYN-FIX-003 is 40 hours in both lanes; no finding either way."""
        self.assertIsNone(finding_for(self.result, "REC-SYN-FIX-003", "effort_hours"))

    def test_counts_match_the_planted_conflicts(self):
        counts = self.result["counts_by_verdict"]
        self.assertEqual(counts[UNKNOWN_BECAME_ZERO], 1)
        self.assertEqual(counts[UNKNOWN_HARDENED], 3)
        self.assertEqual(counts[CONSISTENT], 2)

    def test_every_finding_refuses_to_pick_a_winner(self):
        for finding in self.result["findings"]:
            if finding["verdict"] == CONSISTENT:
                continue
            self.assertIn("does not decide which lane is correct", finding["resolution"])
            # No field anywhere names a correct or authoritative side.
            blob = json.dumps(finding).lower()
            for banned in ("authoritative", "correct_lane", "should be", "is wrong"):
                self.assertNotIn(banned, blob)


# ---------------------------------------------------------------------------
# Intra-lane variants
# ---------------------------------------------------------------------------


class IntraLaneVariantTests(unittest.TestCase):
    """Another seat's deliberately-broken fixtures are not our findings."""

    def _claims(self, rows):
        return [Claim(i, f, v, lane, path, "x") for i, f, v, lane, path in rows]

    def test_a_lane_disagreeing_with_itself_is_set_aside(self):
        """One lane holding both the unknown and the value is a test variant.

        That is what a checker's `fixtures/mismatched/` copies look like from
        outside, and counting them would manufacture defects out of somebody
        else's passing suite.
        """
        claims = self._claims(
            [
                ("REC-A", "status", "UNKNOWN", "lane_one", "lane_one/clean.json"),
                ("REC-A", "status", "SUPPORTED", "lane_one", "lane_one/mismatched/x.json"),
                ("REC-A", "status", "UNKNOWN", "lane_two", "lane_two/matrix.csv"),
            ]
        )
        result = analyze(claims)
        self.assertEqual(result["counts_by_verdict"][UNKNOWN_HARDENED], 0)
        self.assertEqual(len(result["intra_lane_variants"]), 1)
        variant = result["intra_lane_variants"][0]
        self.assertEqual(variant["scope"], INTRA_LANE_VARIANT)
        self.assertEqual(variant["valued_lanes"], ["lane_one"])
        # The path hint is corroboration only; the rule is structural.
        self.assertEqual(
            variant["negative_fixture_path_hint"], ["lane_one/mismatched/x.json"]
        )

    def test_the_set_aside_rule_is_structural_not_path_based(self):
        """A value in a lane that never records the unknown is cross-lane,

        even when it sits under a directory named like a negative fixture. A
        directory name is a convention, not a guarantee, so it must not be able
        to suppress a real finding.
        """
        claims = self._claims(
            [
                ("REC-B", "status", "UNKNOWN", "lane_one", "lane_one/clean.json"),
                ("REC-B", "status", "SUPPORTED", "lane_two", "lane_two/mismatched/x.json"),
            ]
        )
        result = analyze(claims)
        self.assertEqual(result["counts_by_verdict"][UNKNOWN_HARDENED], 1)
        self.assertEqual(result["findings"][0]["scope"], CROSS_LANE)
        # The hint is still reported, it just does not change the verdict.
        self.assertTrue(result["findings"][0]["negative_fixture_path_hint"])

    def test_set_aside_items_are_listed_not_deleted(self):
        claims = self._claims(
            [
                ("REC-C", "status", "UNKNOWN", "lane_one", "lane_one/a.json"),
                ("REC-C", "status", "SUPPORTED", "lane_one", "lane_one/b.json"),
                ("REC-C", "status", "UNKNOWN", "lane_two", "lane_two/c.json"),
            ]
        )
        result = analyze(claims)
        text = render_markdown(
            result, [], {}, {"digest_before": "x", "digest_after": "x",
                            "tree_unchanged": True}, "t"
        )
        self.assertIn("Set aside: one lane's own variants", text)
        self.assertIn("REC-C", text)
        self.assertIn("not silently filtering", text)


# ---------------------------------------------------------------------------
# Alignment honesty
# ---------------------------------------------------------------------------


class AlignmentTests(unittest.TestCase):
    def test_single_lane_fields_are_reported_as_uncheckable(self):
        """Where nothing can be compared, silence is not agreement."""
        result, _, _ = scan_fixtures()
        self.assertGreaterEqual(result["totals"]["field_names_in_one_lane_only"], 1)
        self.assertIn("not because they agree", result["coverage"]["alignment_note"])

    def test_a_field_only_one_lane_uses_produces_no_finding(self):
        claims = [
            Claim("REC-D", "solo_field", None, "lane_one", "a.json", "x"),
        ]
        result = analyze(claims)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["totals"]["comparable_identifier_field_pairs"], 0)

    def test_crosswalk_aligns_declared_fields_only(self):
        crosswalk = Crosswalk(
            {
                "equivalences": [
                    {
                        "canonical_field": "effort",
                        "asserted_by": "a person",
                        "basis": "both hold implementation effort in hours",
                        "members": [
                            {"lane": "lane_one", "field": "hours"},
                            {"lane": "lane_two", "field": "effort_hours"},
                        ],
                    }
                ]
            }
        )
        claims = [
            Claim("REC-E", "hours", None, "lane_one", "a.json", "x"),
            Claim("REC-E", "effort_hours", 0, "lane_two", "b.csv", "y"),
        ]
        # Without the crosswalk the two field names never meet.
        self.assertEqual(analyze(claims)["findings"], [])
        # With it, the conflict surfaces.
        aligned = analyze(claims, crosswalk)
        self.assertEqual(len(aligned["findings"]), 1)
        self.assertEqual(aligned["findings"][0]["verdict"], UNKNOWN_BECAME_ZERO)
        self.assertEqual(aligned["findings"][0]["aligned_field"], "effort")

    def test_an_equivalence_without_a_basis_is_refused(self):
        """An unexplained mapping is indistinguishable from a guess."""
        for missing in ("basis", "asserted_by"):
            entry = {
                "canonical_field": "effort",
                "asserted_by": "a person",
                "basis": "a reason",
                "members": [{"lane": "l", "field": "f"}],
            }
            del entry[missing]
            with self.subTest(missing=missing):
                with self.assertRaises(ScanError) as ctx:
                    Crosswalk({"equivalences": [entry]})
                self.assertIn("guess", str(ctx.exception))

    def test_no_similarity_matching_happens(self):
        """`effort_hours` and `effort_hrs` must NOT be aligned automatically."""
        claims = [
            Claim("REC-F", "effort_hours", None, "lane_one", "a.json", "x"),
            Claim("REC-F", "effort_hrs", 0, "lane_two", "b.csv", "y"),
        ]
        self.assertEqual(analyze(claims)["findings"], [])

    def test_the_shipped_crosswalk_loads(self):
        path = os.path.join(HERE, "crosswalk.json")
        with open(path, encoding="utf-8") as handle:
            crosswalk = Crosswalk(json.load(handle))
        self.assertTrue(crosswalk.declarations)
        for entry in crosswalk.declarations:
            self.assertTrue(entry["basis"])
            self.assertTrue(entry["asserted_by"])


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


class ExtractionTests(unittest.TestCase):
    def test_json_object_without_an_identifier_yields_nothing(self):
        """Mentioning an id in prose is not a claim about it."""
        payload = {"note": "see REC-SYN-FIX-001 for context", "value": 3}
        self.assertEqual(claims_from_json(payload, "lane", "p.json"), [])

    def test_only_recognized_id_prefixes_count(self):
        payload = {"widget_id": "WIDGET-1", "value": 3}
        self.assertEqual(claims_from_json(payload, "lane", "p.json"), [])

    def test_nested_objects_are_reached(self):
        payload = {"a": {"b": [{"recommendation_id": "REC-SYN-X", "v": None}]}}
        claims = claims_from_json(payload, "lane", "p.json")
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].identifier, "REC-SYN-X")
        self.assertEqual(claims[0].kind, UNKNOWN)
        self.assertIn("[0]", claims[0].locator)

    def test_csv_without_an_id_column_yields_nothing(self):
        self.assertEqual(claims_from_csv("a,b\n1,2\n", "lane", "p.csv"), [])

    def test_csv_rows_carry_a_line_locator(self):
        text = "recommendation_id,effort\nREC-SYN-X,UNKNOWN\n"
        claims = claims_from_csv(text, "lane", "p.csv")
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].locator, "row 2")

    def test_empty_csv_does_not_crash(self):
        self.assertEqual(claims_from_csv("", "lane", "p.csv"), [])

    def test_unreadable_files_are_reported_not_skipped_silently(self):
        """A screen that quietly ignores what it could not read is lying."""
        with tempfile.TemporaryDirectory() as tmp:
            lane = os.path.join(tmp, "lane_bad")
            os.makedirs(lane)
            with open(os.path.join(lane, "broken.json"), "w", encoding="utf-8") as h:
                h.write("{not json")
            _, unreadable = collect_claims(tmp, "lane_")
            self.assertEqual(len(unreadable), 1)
            self.assertIn("broken.json", unreadable[0]["path"])

    def test_missing_root_is_refused(self):
        with self.assertRaises(ScanError):
            collect_claims("/nonexistent/root", "lane_")


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


class VocabularyTests(unittest.TestCase):
    def test_census_records_the_family_of_each_spelling(self):
        claims = [
            Claim("REC-G", "s", "UNKNOWN", "lane_one", "a.json", "x"),
            Claim("REC-G", "s", "PARTIAL", "lane_two", "b.json", "y"),
        ]
        census = unknown_vocabulary_census(claims)
        self.assertEqual(census["UNKNOWN"]["family"], UNKNOWN)
        self.assertEqual(census["PARTIAL"]["family"], INCOMPLETE)

    def test_divergence_reports_fields_spelled_more_than_one_way(self):
        claims = [
            Claim("REC-H", "rank", None, "lane_one", "a.json", "x"),
            Claim("REC-I", "rank", "NOT_RANKED", "lane_one", "a.json", "x"),
            Claim("REC-J", "rank", "UNKNOWN", "lane_two", "b.json", "y"),
        ]
        divergence = vocabulary_divergence(claims)
        self.assertEqual(len(divergence), 1)
        self.assertEqual(divergence[0]["field"], "rank")
        self.assertEqual(
            set(divergence[0]["spellings"]), {"null", "NOT_RANKED", "UNKNOWN"}
        )

    def test_a_field_with_one_spelling_is_not_divergent(self):
        claims = [
            Claim("REC-K", "rank", "UNKNOWN", "lane_one", "a.json", "x"),
            Claim("REC-L", "rank", "UNKNOWN", "lane_two", "b.json", "y"),
        ]
        self.assertEqual(vocabulary_divergence(claims), [])


# ---------------------------------------------------------------------------
# Read-only guarantee
# ---------------------------------------------------------------------------


class ReadOnlyTests(unittest.TestCase):
    def test_scanning_does_not_change_the_tree(self):
        readonly, claims, _ = verify_readonly(FIXTURES, "lane_")
        self.assertTrue(readonly["tree_unchanged"])
        self.assertEqual(readonly["digest_before"], readonly["digest_after"])
        self.assertTrue(claims)

    def test_the_digest_actually_notices_a_change(self):
        """A read-only proof is worthless if its digest cannot detect an edit."""
        with tempfile.TemporaryDirectory() as tmp:
            lane = os.path.join(tmp, "lane_x")
            os.makedirs(lane)
            path = os.path.join(lane, "a.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write('{"recommendation_id": "REC-SYN-X", "v": 1}')
            before = tree_digest(tmp, "lane_")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write('{"recommendation_id": "REC-SYN-X", "v": 2}')
            self.assertNotEqual(before, tree_digest(tmp, "lane_"))

    def test_the_module_writes_nothing_without_output_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane = os.path.join(tmp, "lane_x")
            os.makedirs(lane)
            with open(os.path.join(lane, "a.json"), "w", encoding="utf-8") as handle:
                handle.write('{"recommendation_id": "REC-SYN-X", "v": null}')
            listing_before = sorted(os.listdir(lane))
            proc = subprocess.run(
                [sys.executable, os.path.join(HERE, "scan_unknowns.py"),
                 "--root", tmp, "--lane-prefix", "lane_", "--crosswalk", ""],
                capture_output=True, text=True, cwd=HERE,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(sorted(os.listdir(lane)), listing_before)


# ---------------------------------------------------------------------------
# Reporting honesty
# ---------------------------------------------------------------------------


class ReportingTests(unittest.TestCase):
    def test_a_clean_result_is_not_reported_as_correctness(self):
        result = analyze([])
        text = render_markdown(
            result, [], {},
            {"digest_before": "x", "digest_after": "x", "tree_unchanged": True},
            "tree",
        )
        self.assertIn("not about the delivery kit", text)
        self.assertIn("could align", text)

    def test_the_alignment_gap_is_stated_as_a_result(self):
        result, _, _ = scan_fixtures()
        text = render_markdown(
            result, [], {},
            {"digest_before": "x", "digest_after": "x", "tree_unchanged": True},
            "tree",
        )
        self.assertIn("headline result, not a caveat", text)

    def test_limits_are_always_present(self):
        result = analyze([])
        self.assertTrue(result["limits"])
        joined = " ".join(result["limits"]).lower()
        self.assertIn("not a statement that the artifacts agree", joined)
        self.assertIn("scored, rated, graded or marked", joined)

    def test_no_output_scores_or_grades_a_lane(self):
        """No finding or total may carry a score, grade or compliance verdict.

        The `limits` block is excluded because that is where the disclaimer
        lives -- it contains the word "scored" precisely in order to say the
        output does not do it.
        """
        result, _, _ = scan_fixtures()
        payload = {k: v for k, v in result.items() if k != "limits"}
        blob = json.dumps(payload).lower()
        for banned in ("score", "grade", "compliant", "pass_rate", "quality_rating"):
            self.assertNotIn(banned, blob, f"output must not contain {banned!r}")
        # And the disclaimer really is in the limits, not missing entirely.
        self.assertIn("scored", " ".join(result["limits"]).lower())

    def test_consistent_findings_do_not_claim_something_crossed_a_boundary(self):
        """A CONSISTENT pair has no valued side, so no handoff changed anything."""
        result, _, _ = scan_fixtures()
        for finding in result["findings"]:
            if finding["verdict"] != CONSISTENT:
                continue
            self.assertEqual(finding["valued_lanes"], [])
            self.assertNotIn("Something changed", finding["scope_detail"])
            self.assertIn("no lane records a settled value", finding["scope_detail"])

    def test_csv_writes_unknowns_as_words_never_blanks(self):
        result, _, _ = scan_fixtures()
        rows = to_csv_rows(result)
        header = rows[0]
        value_col = header.index("unknown_value")
        self.assertGreater(len(rows), 1)
        for row in rows[1:]:
            self.assertNotEqual(row[value_col], "")
            self.assertNotEqual(row[value_col], "0")

    def test_findings_are_ordered_by_severity(self):
        result, _, _ = scan_fixtures()
        verdicts = [f["verdict"] for f in result["findings"]]
        order = {v: i for i, v in enumerate(scan_unknowns.FINDING_ORDER)}
        self.assertEqual(verdicts, sorted(verdicts, key=lambda v: order[v]))
        self.assertEqual(verdicts[0], UNKNOWN_BECAME_ZERO)


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------


class EndToEndTests(unittest.TestCase):
    def test_output_is_deterministic(self):
        first = json.dumps(scan_fixtures()[0], sort_keys=True)
        second = json.dumps(scan_fixtures()[0], sort_keys=True)
        self.assertEqual(first, second)

    def test_cli_writes_all_three_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_out = os.path.join(tmp, "o.json")
            csv_out = os.path.join(tmp, "o.csv")
            md_out = os.path.join(tmp, "o.md")
            code = scan_unknowns.main(
                ["--root", FIXTURES, "--lane-prefix", "lane_", "--crosswalk", "",
                 "--json-out", json_out, "--csv-out", csv_out,
                 "--markdown-out", md_out]
            )
            self.assertEqual(code, 0)
            with open(json_out, encoding="utf-8") as handle:
                bundle = json.load(handle)
            self.assertEqual(
                bundle["content_class"],
                "READ_ONLY_SCREEN_RESULT_NOT_AN_ASSESSMENT",
            )
            self.assertTrue(bundle["readonly_verification"]["tree_unchanged"])
            self.assertEqual(
                bundle["counts_by_verdict"][UNKNOWN_BECAME_ZERO], 1
            )
            with open(md_out, encoding="utf-8") as handle:
                self.assertIn("UNKNOWN_BECAME_ZERO", handle.read())

    def test_module_runs_under_python_O(self):
        proc = subprocess.run(
            [sys.executable, "-O", "-m", "unittest",
             "test_scan_unknowns.PlantedConflictTests"],
            capture_output=True, text=True, cwd=HERE,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
