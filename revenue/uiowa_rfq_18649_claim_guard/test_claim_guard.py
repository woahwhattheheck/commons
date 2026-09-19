#!/usr/bin/env python3
"""Tests for the cross-lane claim guard (OPS-CLAIM-GUARD).

The central assertions are the paired ones: the SAME vocabulary must classify
as ASSERTION in the planted-assertion fixture and as REFUSAL in the planted-
refusal fixture. If the guard cannot separate those two files it is a word
search, not a guard.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import claim_guard as cg  # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures")


def scan_fixtures():
    return cg.scan_tree(FIXTURES, lane_glob_prefix="planted_")


def in_lane(findings, lane):
    return [f for f in findings if f["file"].split(os.sep)[0] == lane]


class TestClassifier(unittest.TestCase):
    def c(self, text, pattern=r"\bcertif(y|ied|ication|ies)\b"):
        import re
        clause = cg.normalize(text)
        m = re.search(pattern, clause, re.IGNORECASE)
        self.assertIsNotNone(m, "pattern did not match test text")
        return cg.classify(clause, m.span())

    def test_plain_claim_is_an_assertion(self):
        self.assertEqual(
            self.c("The organization is certified against the standard."),
            cg.ASSERTION)

    def test_negation_before_the_match_is_a_refusal(self):
        self.assertEqual(
            self.c("No certification is claimed anywhere in this kit."),
            cg.REFUSAL)

    def test_verbal_negation_after_the_match_is_a_refusal(self):
        self.assertEqual(
            self.c("Certification is not claimed by this assessment."),
            cg.REFUSAL)

    def test_negation_scoped_to_another_noun_does_not_clear_the_claim(self):
        """'the University of Iowa has no retention schedule' contains 'no',
        but the 'no' negates the schedule, not the claim about the University.
        Treating any later negation as a refusal let a real assertion through.
        """
        self.assertEqual(
            self.c("The University of Iowa has no retention schedule applied "
                   "to its logs.", r"\bthe\s+University\s+of\s+Iowa\b"),
            cg.ASSERTION)

    def test_markdown_emphasis_does_not_hide_a_negation(self):
        """'**not** as a certification checklist' is a refusal. Before
        normalization the marker 'not ' never matched, because the text is
        literally 'not**'."""
        self.assertEqual(
            self.c("Used as a reference, **not** as a certification checklist."),
            cg.REFUSAL)

    def test_quantified_claim_without_a_verb_is_an_assertion(self):
        self.assertEqual(
            self.c("Overall maturity level 4 of 5 for the current period.",
                   r"\bmaturity\s+(level|score|tier|rating|index)\b"),
            cg.ASSERTION)

    def test_identifier_digits_do_not_make_a_heading_a_claim(self):
        """'## CG-01 certification' must not read as a quantified claim just
        because the rule id contains digits."""
        self.assertEqual(self.c("## CG-01 certification"), cg.AMBIGUOUS)

    def test_unclassifiable_stays_ambiguous(self):
        """The classifier must not resolve its own uncertainty toward clean."""
        self.assertEqual(self.c("certification"), cg.AMBIGUOUS)

    def test_ambiguous_is_a_real_third_outcome(self):
        self.assertEqual(len(cg.CLASSIFICATIONS), 3)
        self.assertIn(cg.AMBIGUOUS, cg.CLASSIFICATIONS)


class TestPlantedFixtures(unittest.TestCase):
    """The negative control. Same words, opposite meaning."""

    @classmethod
    def setUpClass(cls):
        cls.findings, cls.meta = scan_fixtures()

    def test_every_rule_fires_on_the_assertion_fixture(self):
        fired = {f["rule"] for f in in_lane(self.findings, "planted_assertions")
                 if f["classification"] == cg.ASSERTION}
        self.assertEqual(sorted(fired), sorted(cg.RULES),
                         "a rule never fired on planted violations, so it "
                         "cannot be trusted to fire on a real one")

    def test_no_assertion_is_found_in_the_refusal_fixture(self):
        bad = [f for f in in_lane(self.findings, "planted_refusals")
               if f["classification"] == cg.ASSERTION]
        self.assertEqual(bad, [], "false positives: %s"
                         % [(f["rule"], f["clause"]) for f in bad])

    def test_no_planted_violation_is_wrongly_cleared(self):
        cleared = [f for f in in_lane(self.findings, "planted_assertions")
                   if f["classification"] == cg.REFUSAL]
        self.assertEqual(cleared, [], "planted violations classified as "
                                      "refusals: %s"
                         % [(f["rule"], f["clause"]) for f in cleared])

    def test_the_two_fixtures_use_the_same_vocabulary(self):
        """If the fixtures did not share vocabulary the separation above would
        prove nothing."""
        def words(lane):
            text = ""
            for dirpath, _, names in os.walk(os.path.join(FIXTURES, lane)):
                for n in names:
                    if n.endswith(".md"):
                        with open(os.path.join(dirpath, n),
                                  encoding="utf-8") as fh:
                            text += fh.read().lower()
            return text
        a, r = words("planted_assertions"), words("planted_refusals")
        for term in ("certif", "maturity", "percentile", "peer institutions",
                     "performance score", "university of iowa", "tier",
                     "industry average", "employee rating"):
            self.assertIn(term, a, "assertion fixture lacks %r" % term)
            self.assertIn(term, r, "refusal fixture lacks %r" % term)

    def test_unlabelled_fiction_is_flagged(self):
        hits = [f for f in self.findings if f["rule"] == "CG-06"]
        self.assertTrue(any(h["file"] == "planted_unlabelled" for h in hits))

    def test_unlabelled_fiction_is_ambiguous_not_a_verdict(self):
        """The tool cannot know that unlabelled data is being passed off as
        real. It flags it for a person."""
        for f in [x for x in self.findings if x["rule"] == "CG-06"]:
            self.assertEqual(f["classification"], cg.AMBIGUOUS)

    def test_labelled_lanes_are_not_flagged_for_fiction(self):
        hits = {f["file"] for f in self.findings if f["rule"] == "CG-06"}
        self.assertNotIn("planted_assertions", hits)
        self.assertNotIn("planted_refusals", hits)


class TestReadOnly(unittest.TestCase):
    def test_a_full_scan_modifies_nothing(self):
        """Proved, not promised: hash the whole tree before and after."""
        tmp = tempfile.mkdtemp(prefix="claimguard-ro-")
        try:
            shutil.copytree(FIXTURES, os.path.join(tmp, "tree"))
            root = os.path.join(tmp, "tree")
            before = cg.tree_digest(root)
            cg.scan_tree(root, lane_glob_prefix="planted_")
            after = cg.tree_digest(root)
            self.assertEqual(before, after, "the scan modified the tree")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_run_records_that_the_tree_was_unmodified(self):
        tmp = tempfile.mkdtemp(prefix="claimguard-ro-")
        out = tempfile.mkdtemp(prefix="claimguard-out-")
        try:
            shutil.copytree(FIXTURES, os.path.join(tmp, "tree"))
            _, summary = cg.run(os.path.join(tmp, "tree"), out)
            self.assertTrue(summary["scanned"]["scanned_tree_unmodified"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            shutil.rmtree(out, ignore_errors=True)

    def test_tree_digest_detects_a_change(self):
        """The read-only proof is only worth something if the digest can move."""
        tmp = tempfile.mkdtemp(prefix="claimguard-ro-")
        try:
            shutil.copytree(FIXTURES, os.path.join(tmp, "tree"))
            root = os.path.join(tmp, "tree")
            before = cg.tree_digest(root)
            with open(os.path.join(root, "planted_refusals", "README.md"),
                      "a", encoding="utf-8") as fh:
                fh.write("\nx\n")
            self.assertNotEqual(before, cg.tree_digest(root))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestRefusalsOfThisTool(unittest.TestCase):
    def test_no_per_lane_aggregate_exists(self):
        """The tool must not produce any per-lane number at all.

        Checked structurally, not by substring: this test originally scanned
        the serialized summary for the word "grade" and matched the tool's own
        refusal sentence, "no lane is scored, graded, ranked or rated". That is
        the exact failure mode this whole module exists to catch -- a refusal
        reading as a violation -- and it fired on its own test three lanes
        running. Field names and value shapes are what matter.
        """
        findings, meta = scan_fixtures()
        summary = cg.summarize(findings, meta)
        lanes = {f["file"].split(os.sep)[0] for f in findings}
        self.assertTrue(lanes, "fixture produced no findings to check")

        def keys(node):
            out = set()
            if isinstance(node, dict):
                for k, v in node.items():
                    out.add(str(k))
                    out |= keys(v)
            elif isinstance(node, list):
                for v in node:
                    out |= keys(v)
            return out

        present = keys(summary)
        for lane in lanes:
            self.assertNotIn(lane, present,
                             "summary carries a per-lane entry for %r" % lane)

    def test_no_summary_value_is_a_rate(self):
        """Every number the summary reports is a raw count. A float is how a
        count turns into a rate, and a rate reads as a score."""
        findings, meta = scan_fixtures()
        summary = cg.summarize(findings, meta)

        def walk(node, path):
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, "%s/%s" % (path, k))
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    walk(v, "%s[%d]" % (path, i))
            elif isinstance(node, float):
                self.fail("%s is a float (%r); counts must be integers"
                          % (path, node))
            elif isinstance(node, int) and not isinstance(node, bool):
                self.assertGreaterEqual(node, 0, path)
        walk(summary, "summary")

    def test_summary_has_no_per_lane_verdict_structure(self):
        findings, meta = scan_fixtures()
        summary = cg.summarize(findings, meta)

        def walk(node, path):
            if isinstance(node, dict):
                for k, v in node.items():
                    low = str(k).lower()
                    for bad in ("score", "grade", "rating", "rank", "percent"):
                        self.assertNotIn(bad, low, "field %s/%s" % (path, k))
                    walk(v, "%s/%s" % (path, k))
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    walk(v, "%s[%d]" % (path, i))
        walk(summary, "summary")

    def test_self_exclusion_is_reported_not_hidden(self):
        findings, meta = cg.scan_tree(os.path.dirname(HERE),
                                      lane_glob_prefix="uiowa_rfq_18649_claim")
        self.assertTrue(any(f.endswith("claim_guard.py")
                            for f in meta["files_excluded"]),
                        "the guard excluded its own source without saying so")
        self.assertIn("excluded", meta["exclusion_note"].lower())

    def test_notes_state_that_assertion_is_a_candidate_not_a_verdict(self):
        findings, meta = scan_fixtures()
        summary = cg.summarize(findings, meta)
        joined = " ".join(summary["notes"]).lower()
        self.assertIn("not a proven violation", joined)

    def test_ambiguous_count_is_reported_when_nonzero(self):
        findings, meta = scan_fixtures()
        summary = cg.summarize(findings, meta)
        if summary["totals_by_classification"][cg.AMBIGUOUS]:
            self.assertIn("ambiguous",
                          " ".join(summary["notes"]).lower())


class TestParagraphHandling(unittest.TestCase):
    def test_wrapped_prose_is_joined_before_classification(self):
        """A sentence split across two source lines must not lose the half
        carrying the negation."""
        lines = ["Nothing is benchmarked against peer",
                 "institutions in this assessment."]
        blocks = list(cg.blocks_of(lines, prose=True))
        self.assertEqual(len(blocks), 1)
        self.assertIn("peer institutions", blocks[0][1])

    def test_headings_stay_separate_from_the_paragraph_below(self):
        lines = ["## Heading", "Body text follows here."]
        blocks = list(cg.blocks_of(lines, prose=True))
        self.assertEqual(len(blocks), 2)

    def test_code_is_not_paragraph_joined(self):
        lines = ["a = 1", "b = 2"]
        self.assertEqual(len(list(cg.blocks_of(lines, prose=False))), 2)

    def test_line_numbers_survive_joining(self):
        lines = ["", "", "first line of para", "second line of para"]
        blocks = list(cg.blocks_of(lines, prose=True))
        self.assertEqual(blocks[0][0], 3)


class TestHostileInput(unittest.TestCase):
    def test_missing_root_raises(self):
        with self.assertRaises(ValueError):
            cg.scan_tree("/nonexistent/path/xyz")

    def test_empty_root_scans_cleanly(self):
        tmp = tempfile.mkdtemp(prefix="claimguard-empty-")
        try:
            findings, meta = cg.scan_tree(tmp)
            self.assertEqual(findings, [])
            self.assertEqual(meta["lanes_scanned"], 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_lane_with_no_text_files_is_handled(self):
        tmp = tempfile.mkdtemp(prefix="claimguard-bin-")
        try:
            lane = os.path.join(tmp, "uiowa_rfq_18649_binary")
            os.makedirs(lane)
            with open(os.path.join(lane, "blob.bin"), "wb") as fh:
                fh.write(b"\x00\x01\x02certified\xff")
            findings, meta = cg.scan_tree(tmp)
            self.assertEqual(meta["lanes_scanned"], 1)
            self.assertEqual(meta["files_scanned"], 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_undecodable_bytes_in_a_text_file_do_not_crash(self):
        tmp = tempfile.mkdtemp(prefix="claimguard-bad-")
        try:
            lane = os.path.join(tmp, "uiowa_rfq_18649_bad")
            os.makedirs(lane)
            with open(os.path.join(lane, "notes.md"), "wb") as fh:
                fh.write(b"The org is certified \xff\xfe and done.\n")
            findings, _ = cg.scan_tree(tmp)
            self.assertTrue(any(f["rule"] == "CG-01" for f in findings))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_scan_is_deterministic(self):
        a, _ = scan_fixtures()
        b, _ = scan_fixtures()
        self.assertEqual(a, b)


class TestOutputs(unittest.TestCase):
    def test_run_writes_all_three_outputs(self):
        out = tempfile.mkdtemp(prefix="claimguard-out-")
        try:
            findings, summary = cg.run(FIXTURES, out)
            for name in ("claim_findings.csv", "claim_findings.md",
                         "claim_findings.json"):
                path = os.path.join(out, name)
                self.assertTrue(os.path.exists(path), name)
                self.assertGreater(os.path.getsize(path), 0)
            with open(os.path.join(out, "claim_findings.json"),
                      encoding="utf-8") as fh:
                blob = json.load(fh)
            self.assertEqual(len(blob["findings"]), len(findings))
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_markdown_explains_all_three_outcomes(self):
        out = tempfile.mkdtemp(prefix="claimguard-out-")
        try:
            cg.run(FIXTURES, out)
            with open(os.path.join(out, "claim_findings.md"),
                      encoding="utf-8") as fh:
                md = fh.read()
            for token in ("ASSERTION", "REFUSAL", "AMBIGUOUS",
                          "Never auto-cleared"):
                self.assertIn(token, md)
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_cli_exits_zero_and_two(self):
        out = tempfile.mkdtemp(prefix="claimguard-out-")
        try:
            self.assertEqual(cg.main(["--root", FIXTURES, "--out", out]), 0)
            self.assertEqual(
                cg.main(["--root", "/nonexistent/xyz", "--out", out]), 2)
        finally:
            shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
