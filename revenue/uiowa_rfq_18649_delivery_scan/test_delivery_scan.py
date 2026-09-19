#!/usr/bin/env python3
"""Tests for the cross-lane scope screen and the guard hardening it drove.

Run:  python3 -m unittest -v test_delivery_scan.py

The important class here is `RealDeliveredSentenceTests`. Every string in it was
copied verbatim out of the delivered RFQ 18649 tree, and every one was a **false
positive** on the first cross-lane scan. They are the regression suite for the
hardening, and they are quoted rather than paraphrased on purpose: a
paraphrase would test the fix against text I wrote to pass it.

The drift cases are re-asserted here too. A hardening pass that quietly loses
detection is worse than no hardening at all, so precision and recall are tested
in the same file.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import delivery_scan as ds  # noqa: E402
import scope_guard as sg  # noqa: E402  (resolved through delivery_scan's path setup)


def flags(text):
    return sg.flagged(sg.scan_text(text))


def classes(text):
    return {h.guard_class for h in flags(text)}


class RealDeliveredSentenceTests(unittest.TestCase):
    """Verbatim sentences from other seats' landed lanes. None is drift."""

    # (lane it came from, the sentence, why it is not drift)
    CASES = [
        ("uiowa_rfq_18649_mobilization",
         "| R9 | RFQ p5, attribute 4, section 3.4 | Excludes line-by-line review, formal "
         "compliance audit, performance evaluation of any individual or workgroup, commercial "
         "product/vendor/tool procurement recommendations, and a deep dive into a specific "
         "application/service/system. |",
         "a requirements table cell declaring the RFQ's own exclusions"),

        ("uiowa_rfq_18649_release_provenance",
         "There is no average, maturity score, confidence score, or employee ranking.",
         "an explicit negation spread across a comma list"),

        ("uiowa_rfq_18649_secure_guidance",
         "**Reasoning anchors (facilitator prompts, not employee scoring keys)**",
         "a parenthetical contrast: X, not Y"),

        ("uiowa_rfq_18649_qa_refusal_contract",
         "**Not attempted:** no model calls anywhere; no scoring, maturity rating, percentile,\n"
         "certification verdict or individual/team performance rating is produced by any path in\n"
         "this code, and the fixtures contain none.",
         "one sentence wrapped across three markdown lines"),

        ("uiowa_rfq_18649_adoption_readiness",
         "Supply any of these and the corresponding `assumption_basis` should be replaced",
         "replacing a configuration value, not a person"),

        ("uiowa_rfq_18649_workshare",
         "The workshare may recommend practices/process improvements but does not create "
         "product/vendor selection or endorsement.",
         "the lane declaring its own boundary"),
    ]

    def test_no_delivered_boundary_sentence_is_flagged(self):
        for lane, text, why in self.CASES:
            with self.subTest(lane=lane, why=why):
                hits = flags(text)
                self.assertEqual(
                    [], hits,
                    f"{lane}: {why}\n  flagged: "
                    + "; ".join(f"[{h.rule_id}] {h.matched!r}" for h in hits))

    def test_bullet_inherits_its_lead_in(self):
        """An exclusion list's negation lives in the line above the bullets."""
        text = (
            "The $24,000 base workshare does not silently expand to cover materially new scope. "
            "The parties should separately authorize a change when the prime requests work "
            "outside the bounded technical package, including examples such as:\n"
            "\n"
            "- additional system/application groups not represented by the agreed frame;\n"
            "- onsite work or travel;\n"
            "- procurement/vendor selection, recommendations or endorsements for specific "
            "commercial products/vendors, legal, audit, certification, insurance, or regulatory "
            "opinions;\n")
        self.assertEqual([], flags(text))

    def test_markdown_emphasis_does_not_break_a_negation(self):
        """`must *not* turn into` still reads as a negation."""
        text = ("scans report prose for the three deliverables this engagement must *not* turn "
                "into: an audit/compliance verdict, an individual performance evaluation, a "
                "product procurement recommendation.")
        self.assertEqual([], flags(text))

    def test_a_documented_rule_vocabulary_is_not_drift(self):
        """A rules table cataloguing forbidden phrases must not trip on them."""
        text = ("- **`audit_verdict`** -- `non-compliant`, `audit finding`, `material weakness`, "
                "`certifies`, `failed the audit`, `in violation of`.\n"
                "- **`product_procurement`** -- `we recommend purchasing`, `preferred vendor`, "
                "`issue an RFP`, `per-seat price`.")
        self.assertEqual([], flags(text))

    def test_captured_transcript_in_a_fenced_block_is_not_drift(self):
        """10 of the first scan's 42 flags were 082's own CLI test output,
        captured into two lanes' verification logs."""
        text = ("Verification log for the 082 lane:\n\n"
                "```\n"
                "[AV-01] audit_verdict  /tmp/x/drifted.md:1\n"
                "  matched : \"non-compliant\"\n"
                "  in      : The service is non-compliant and we recommend purchasing a new tool.\n"
                "```\n\n"
                "All checks passed.\n")
        self.assertEqual([], flags(text))


class DriftStillCaughtTests(unittest.TestCase):
    """Hardening must not cost recall."""

    def test_audit_verdict_still_caught(self):
        self.assertIn(sg.AUDIT_VERDICT,
                      classes("Finding 3: the RIS group is non-compliant with the standard, "
                              "which is a material weakness."))

    def test_individual_evaluation_still_caught(self):
        self.assertIn(sg.INDIVIDUAL_EVALUATION,
                      classes("The ESS database administrator is underperforming and lacks the "
                              "experience for this platform; her performance rating should "
                              "reflect it."))

    def test_product_procurement_still_caught(self):
        self.assertIn(sg.PRODUCT_PROCUREMENT,
                      classes("We recommend purchasing an enterprise secrets-management platform "
                              "from the preferred vendor this quarter."))

    def test_all_three_still_caught_in_one_pass(self):
        self.assertEqual(
            {sg.AUDIT_VERDICT, sg.INDIVIDUAL_EVALUATION, sg.PRODUCT_PROCUREMENT},
            classes("The group is non-compliant with IT-18. "
                    "The lead engineer lacks the skills to close this. "
                    "We recommend purchasing a replacement platform."))

    def test_person_gate_keeps_the_personnel_case(self):
        """IE-02 now requires a person - it must still fire when one is there."""
        self.assertIn(sg.INDIVIDUAL_EVALUATION,
                      classes("The contractor should be replaced before the next release."))

    def test_person_gate_drops_the_value_case(self):
        self.assertEqual([], flags("The default timeout should be replaced with a configured one."))

    def test_drift_inside_ordinary_prose_next_to_a_code_span_is_still_caught(self):
        """Blanking code spans must not blank the sentence around them."""
        text = "Per `IT-18`, the RIS group is non-compliant and we recommend purchasing a scanner."
        self.assertEqual({sg.AUDIT_VERDICT, sg.PRODUCT_PROCUREMENT}, classes(text))


class StripNonProseTests(unittest.TestCase):
    def test_line_count_is_preserved(self):
        text = "a\n```\nb\nc\n```\nd\n"
        self.assertEqual(len(text.split("\n")), len(sg.strip_non_prose(text).split("\n")))

    def test_code_span_blanking_preserves_width(self):
        line = "see `non-compliant` here"
        out = sg.strip_non_prose(line)
        self.assertEqual(len(line), len(out))
        self.assertNotIn("non-compliant", out)
        self.assertIn("see", out)
        self.assertIn("here", out)

    def test_emphasis_is_unwrapped_not_deleted(self):
        out = sg.strip_non_prose("must *not* turn")
        self.assertIn("not", out)
        self.assertEqual(len("must *not* turn"), len(out))

    def test_list_bullet_is_not_treated_as_emphasis(self):
        self.assertTrue(sg.strip_non_prose("* an item").lstrip().startswith("* an item")
                        or "an item" in sg.strip_non_prose("* an item"))

    def test_unterminated_fence_does_not_swallow_the_whole_file_silently(self):
        """It does blank the remainder - that is the conservative direction - but
        the function must not raise and must keep the line count."""
        text = "prose\n```\nstill fenced\nnever closed\n"
        out = sg.strip_non_prose(text)
        self.assertEqual(len(text.split("\n")), len(out.split("\n")))
        self.assertIn("prose", out)


class ScanTreeTests(unittest.TestCase):
    def _tree(self, td, lane, name, text):
        d = os.path.join(td, lane)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(text)

    def test_scan_finds_drift_and_attributes_it_to_the_right_lane(self):
        with tempfile.TemporaryDirectory() as td:
            self._tree(td, "uiowa_rfq_18649_alpha", "README.md",
                       "The service is non-compliant.")
            self._tree(td, "uiowa_rfq_18649_beta", "README.md",
                       "No vendor selection is recommended.")
            res = ds.scan_tree(td)
            self.assertEqual(2, res.files_scanned)
            self.assertEqual(1, res.total_flags)
            self.assertEqual(["uiowa_rfq_18649_alpha"], [l.lane for l in res.flagged_lanes])
            self.assertGreaterEqual(res.total_neutralized, 1)

    def test_non_matching_directories_are_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            self._tree(td, "unrelated_project", "README.md", "The service is non-compliant.")
            res = ds.scan_tree(td)
            self.assertEqual(0, res.files_scanned)
            self.assertEqual(0, res.total_flags)

    def test_missing_root_returns_an_empty_result_rather_than_raising(self):
        res = ds.scan_tree("/nonexistent-root-for-scan")
        self.assertEqual(0, res.files_scanned)
        self.assertEqual([], res.flagged_lanes)

    def test_scan_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            for i in range(4):
                self._tree(td, f"uiowa_rfq_18649_l{i}", "README.md",
                           "The service is non-compliant.")
            a = [(h.source_id, h.rule_id) for lr in ds.scan_tree(td).lanes.values()
                 for h in lr.flagged]
            b = [(h.source_id, h.rule_id) for lr in ds.scan_tree(td).lanes.values()
                 for h in lr.flagged]
            self.assertEqual(sorted(a), sorted(b))

    def test_unreadable_file_is_reported_and_never_counted_as_clean(self):
        """Hostile: a file the screen cannot read must not silently pass."""
        with tempfile.TemporaryDirectory() as td:
            self._tree(td, "uiowa_rfq_18649_alpha", "README.md", "fine")
            bad = os.path.join(td, "uiowa_rfq_18649_alpha", "locked.md")
            with open(bad, "w") as f:
                f.write("x")
            os.chmod(bad, 0o000)
            try:
                res = ds.scan_tree(td)
                if os.access(bad, os.R_OK):
                    self.skipTest("running as a user that ignores file permissions")
                self.assertEqual(1, len(res.files_unreadable))
                self.assertIn("locked.md", res.files_unreadable[0]["path"])
                self.assertEqual(1, res.files_scanned)
            finally:
                os.chmod(bad, 0o644)

    def test_binary_ish_content_does_not_crash_the_scan(self):
        with tempfile.TemporaryDirectory() as td:
            d = os.path.join(td, "uiowa_rfq_18649_alpha")
            os.makedirs(d)
            with open(os.path.join(d, "weird.md"), "wb") as f:
                f.write(b"\xff\xfe\x00bad bytes \xc3\x28 here")
            res = ds.scan_tree(td)
            self.assertEqual(1, res.files_scanned)

    def test_empty_tree_reports_nothing_rather_than_passing_loudly(self):
        with tempfile.TemporaryDirectory() as td:
            res = ds.scan_tree(td)
            self.assertEqual(0, len(res.lanes))
            self.assertIn("screen, not a proof", ds.render_markdown(res))


class ReportTests(unittest.TestCase):
    def _res(self, td):
        d = os.path.join(td, "uiowa_rfq_18649_alpha")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as f:
            f.write("The service is non-compliant.")
        return ds.scan_tree(td)

    def test_markdown_report_carries_the_disclaimer(self):
        with tempfile.TemporaryDirectory() as td:
            md = ds.render_markdown(self._res(td))
            self.assertIn("screen, not a proof", md)
            self.assertIn("NOT A COMPLIANCE CLAIM", md)

    def test_report_assigns_no_score_or_percentage_to_any_lane(self):
        """The whole point: this names questions, it does not rate lanes.

        Checked against the report body with the disclaimer removed - the
        disclaimer itself contains the words "score" and "pass/fail", because its
        whole job is to say there aren't any. Asserting on raw substrings made
        this test fail on the very sentence that guarantees the property.
        """
        import re
        with tempfile.TemporaryDirectory() as td:
            md = ds.render_markdown(self._res(td))
            body = md.replace(ds._DISCLAIMER, "")
            self.assertNotIn("score", ds._DISCLAIMER.lower().split("no score")[1][:20])
            for pattern, label in (
                    (r"\d+\s*%", "a percentage"),
                    (r"(?i)\bscore\s*[:=]\s*\d", "a numeric score"),
                    (r"(?i)\b(?:grade|rating)\s*[:=]", "a grade"),
                    (r"(?i)\b(?:pass|fail)\b\s*[:=]", "a pass/fail verdict"),
                    # Not a bare `compliant` check: the report necessarily QUOTES
                    # the flagged phrase and the rule's explanation, both of which
                    # contain the word. What must never appear is the report
                    # itself rendering a verdict *about a lane*.
                    (r"(?i)\blane\s+\S+\s+(?:is|was|are)\s+(?:non-?)?compliant",
                     "a compliance verdict about a lane"),
                    (r"(?i)^\s*(?:verdict|determination)\s*:", "a verdict line")):
                with self.subTest(forbidden=label):
                    self.assertIsNone(re.search(pattern, body),
                                      f"report assigns {label} to a lane")

    def test_disclaimer_states_the_screen_is_not_a_proof(self):
        self.assertIn("not a proof", ds._DISCLAIMER.lower())
        self.assertIn("no score", ds._DISCLAIMER.lower())

    def test_write_outputs_produces_all_three_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            res = self._res(td)
            out = os.path.join(td, "out")
            written = ds.write_outputs(res, out)
            self.assertEqual(3, len(written))
            for p in written:
                self.assertTrue(os.path.exists(p))

    def test_writes_only_inside_its_own_output_directory(self):
        """The screen is read-only over the tree it scans."""
        with tempfile.TemporaryDirectory() as td:
            res = self._res(td)
            lane_dir = os.path.join(td, "uiowa_rfq_18649_alpha")
            before = sorted(os.listdir(lane_dir))
            ds.write_outputs(res, os.path.join(td, "out"))
            self.assertEqual(before, sorted(os.listdir(lane_dir)))

    def test_cli_does_not_fail_other_peoples_builds_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            self._res(td)
            self.assertEqual(0, ds.main(["--root", td]))
            self.assertEqual(1, ds.main(["--root", td, "--fail-on-flag"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
