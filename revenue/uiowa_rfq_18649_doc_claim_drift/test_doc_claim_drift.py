#!/usr/bin/env python3
"""Tests for the documentation-claim drift screen.

Run:  python3 -m unittest -v test_doc_claim_drift.py

The precision tests come first and carry the most weight. A naive first pass
over the delivered tree reported 97 contradictions; after the fixes below it
reports 4. Every one of those fixes has a test here using the real string that
caused the false positive, because an over-firing screen is an accusation
against another seat.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import doc_claim_drift as d  # noqa: E402


def sweep(lanes):
    return {"observed_on": "2026-09-19", "lanes": lanes}


def lane_rec(name, total, suites=None, category="TESTED"):
    return {"lane": name, "category": category, "lane_outcome": "PASS",
            "tests_run_total": total,
            "suites": suites if suites is not None
            else [{"suite": f"test_{name}.py", "tests_run": total, "outcome": "PASS"}]}


class Fixture:
    """A throwaway tree: lanes, their docs, and a run_sweep.json."""

    def __init__(self, td):
        self.root = td

    def lane(self, name, files=None, subdir_files=None):
        d_ = os.path.join(self.root, name)
        os.makedirs(d_, exist_ok=True)
        for fn, text in (files or {}).items():
            with open(os.path.join(d_, fn), "w", encoding="utf-8") as f:
                f.write(text)
        for rel, text in (subdir_files or {}).items():
            p = os.path.join(d_, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
        return self

    def sweep(self, lanes):
        p = os.path.join(self.root, "uiowa_rfq_18649_run_sweep", "out")
        os.makedirs(p, exist_ok=True)
        with open(os.path.join(p, "run_sweep.json"), "w", encoding="utf-8") as f:
            json.dump(sweep(lanes), f)
        return self

    def run(self):
        return d.run(self.root)


class ClaimExtractionPrecisionTests(unittest.TestCase):
    """Each case is a real string that produced a false positive."""

    def find(self, text):
        return [int(m.group(1)) for m in d._TEST_CLAIM.finditer(text)]

    def test_order_id_is_not_a_test_count(self):
        """'the UIOWA-136 tests assert ...' is an order ID, not 136 tests."""
        self.assertEqual([], self.find("the UIOWA-136 tests assert the named fields"))
        self.assertEqual([], self.find("uiowa-082 tests"))

    def test_file_counts_are_not_test_counts(self):
        for text in ("1 of 1 test file(s) failed",
                     "executed 1 test file(s) here",
                     "2 test suites were discovered",
                     "3 test modules"):
            with self.subTest(text=text):
                self.assertEqual([], self.find(text))

    def test_real_test_counts_are_still_found(self):
        self.assertEqual([41], self.find("Ran 41 tests in 0.02s"))
        self.assertEqual([30], self.find("30 tests, all green"))
        self.assertEqual([22], self.find("22 unittest tests, mostly adversarial"))
        self.assertEqual([55], self.find("55 unittest cases"))

    def test_a_count_and_a_file_count_in_one_sentence(self):
        self.assertEqual([37], self.find("executed 1 test file(s) here, 37 tests ran"))


class LaneAttributionTests(unittest.TestCase):
    def test_embedded_copy_is_attributed_to_its_author(self):
        """A sample packet holding another lane's README is not a self-claim."""
        got = d.attribute_lane(
            "/r",
            "/r/uiowa_rfq_18649_acceptance_map/output/sample_packet/"
            "uiowa_rfq_18649_intake_rehearsal__README.md",
            "uiowa_rfq_18649_acceptance_map")
        self.assertEqual("uiowa_rfq_18649_intake_rehearsal", got)

    def test_ordinary_file_is_attributed_to_its_directory(self):
        self.assertEqual(
            "uiowa_rfq_18649_alpha",
            d.attribute_lane("/r", "/r/uiowa_rfq_18649_alpha/README.md",
                             "uiowa_rfq_18649_alpha"))


class ScopeTests(unittest.TestCase):
    def test_only_lane_root_documentation_is_treated_as_a_self_claim(self):
        with tempfile.TemporaryDirectory() as td:
            res = (Fixture(td)
                   .lane("uiowa_rfq_18649_alpha",
                         files={"README.md": "This kit ships 10 tests."},
                         subdir_files={"sample/verification_log.md":
                                       "reason: 37 tests ran, all passed"})
                   .sweep([lane_rec("uiowa_rfq_18649_alpha", 10)])
                   .run())
            self.assertEqual(1, res.files_examined)
            self.assertEqual(1, res.files_skipped_non_root)
            self.assertEqual(1, len(res.claims))
            self.assertEqual(d.AGREES, res.claims[0].verdict)

    def test_the_skipped_count_is_reported_not_hidden(self):
        with tempfile.TemporaryDirectory() as td:
            res = (Fixture(td)
                   .lane("uiowa_rfq_18649_alpha",
                         files={"README.md": "10 tests."},
                         subdir_files={"sample/a.md": "x", "examples/b.md": "y"})
                   .sweep([lane_rec("uiowa_rfq_18649_alpha", 10)])
                   .run())
            self.assertEqual(2, res.files_skipped_non_root)
            self.assertIn("non-root markdown files skipped", d.render_markdown(res))


class VerdictTests(unittest.TestCase):
    def test_a_stale_count_is_contradicted(self):
        with tempfile.TemporaryDirectory() as td:
            res = (Fixture(td)
                   .lane("uiowa_rfq_18649_alpha", files={"README.md": "The suite has 30 tests."})
                   .sweep([lane_rec("uiowa_rfq_18649_alpha", 36)])
                   .run())
            c = res.claims[0]
            self.assertEqual(d.CONTRADICTED, c.verdict)
            self.assertEqual(30, c.claimed)
            self.assertEqual(36, c.measured)
            self.assertIn("30", c.reason)
            self.assertIn("36", c.reason)

    def test_a_current_count_agrees(self):
        with tempfile.TemporaryDirectory() as td:
            res = (Fixture(td)
                   .lane("uiowa_rfq_18649_alpha", files={"README.md": "Ran 36 tests."})
                   .sweep([lane_rec("uiowa_rfq_18649_alpha", 36)])
                   .run())
            self.assertEqual(d.AGREES, res.claims[0].verdict)

    def test_a_lane_with_no_measurement_is_unverifiable_never_agreeing(self):
        """A lane that landed after the sweep ran has no ground truth. That is
        not a pass and it is not a failure."""
        with tempfile.TemporaryDirectory() as td:
            res = (Fixture(td)
                   .lane("uiowa_rfq_18649_newlane", files={"README.md": "42 tests."})
                   .sweep([lane_rec("uiowa_rfq_18649_other", 5)])
                   .run())
            c = res.claims[0]
            self.assertEqual(d.UNVERIFIABLE, c.verdict)
            self.assertIsNone(c.measured)
            self.assertEqual("no_measurement", c.basis)

    def test_an_untested_lane_is_unverifiable(self):
        with tempfile.TemporaryDirectory() as td:
            res = (Fixture(td)
                   .lane("uiowa_rfq_18649_alpha", files={"README.md": "9 tests."})
                   .sweep([lane_rec("uiowa_rfq_18649_alpha", None, suites=[],
                                    category="NO_TESTS")])
                   .run())
            self.assertEqual(d.UNVERIFIABLE, res.claims[0].verdict)

    def test_multi_suite_lane_is_unverifiable_rather_than_accused(self):
        """Two implementations in one lane: a README describing one of them
        legitimately disagrees with the lane total."""
        with tempfile.TemporaryDirectory() as td:
            res = (Fixture(td)
                   .lane("uiowa_rfq_18649_alpha", files={"README.md": "This kit has 12 tests."})
                   .sweep([lane_rec("uiowa_rfq_18649_alpha", 57, suites=[
                       {"suite": "test_a.py", "tests_run": 50, "outcome": "PASS"},
                       {"suite": "test_b.py", "tests_run": 7, "outcome": "PASS"}])])
                   .run())
            self.assertEqual(d.UNVERIFIABLE, res.claims[0].verdict)
            self.assertEqual("multi_suite", res.claims[0].basis)

    def test_multi_suite_claim_matching_one_suite_agrees(self):
        with tempfile.TemporaryDirectory() as td:
            res = (Fixture(td)
                   .lane("uiowa_rfq_18649_alpha", files={"README.md": "50 tests here."})
                   .sweep([lane_rec("uiowa_rfq_18649_alpha", 57, suites=[
                       {"suite": "test_a.py", "tests_run": 50, "outcome": "PASS"},
                       {"suite": "test_b.py", "tests_run": 7, "outcome": "PASS"}])])
                   .run())
            self.assertEqual(d.AGREES, res.claims[0].verdict)

    def test_a_named_suite_is_checked_against_that_suite(self):
        with tempfile.TemporaryDirectory() as td:
            res = (Fixture(td)
                   .lane("uiowa_rfq_18649_alpha",
                         files={"README.md": "`test_b.py` carries 7 tests."})
                   .sweep([lane_rec("uiowa_rfq_18649_alpha", 57, suites=[
                       {"suite": "test_a.py", "tests_run": 50, "outcome": "PASS"},
                       {"suite": "test_b.py", "tests_run": 7, "outcome": "PASS"}])])
                   .run())
            self.assertEqual(d.AGREES, res.claims[0].verdict)
            self.assertEqual("suite:test_b.py", res.claims[0].basis)


class CrossReferenceTests(unittest.TestCase):
    def test_a_claim_about_another_lane_is_checked_against_that_lane(self):
        with tempfile.TemporaryDirectory() as td:
            res = (Fixture(td)
                   .lane("uiowa_rfq_18649_alpha",
                         files={"README.md":
                                "uiowa_rfq_18649_betalane still passes its 44 tests."})
                   .sweep([lane_rec("uiowa_rfq_18649_alpha", 3),
                           lane_rec("uiowa_rfq_18649_betalane", 44)])
                   .run())
            c = next(x for x in res.claims if x.claimed == 44)
            self.assertEqual(d.AGREES, c.verdict)
            self.assertEqual("cross_reference_total", c.basis)

    def test_a_wrong_cross_reference_is_contradicted_against_the_right_lane(self):
        with tempfile.TemporaryDirectory() as td:
            res = (Fixture(td)
                   .lane("uiowa_rfq_18649_alpha",
                         files={"README.md":
                                "uiowa_rfq_18649_betalane still passes its 40 tests."})
                   .sweep([lane_rec("uiowa_rfq_18649_alpha", 3),
                           lane_rec("uiowa_rfq_18649_betalane", 44)])
                   .run())
            c = next(x for x in res.claims if x.claimed == 40)
            self.assertEqual(d.CONTRADICTED, c.verdict)
            self.assertEqual(44, c.measured)


class ReportTests(unittest.TestCase):
    def _res(self, td):
        return (Fixture(td)
                .lane("uiowa_rfq_18649_alpha", files={"README.md": "The suite has 30 tests."})
                .sweep([lane_rec("uiowa_rfq_18649_alpha", 36)])
                .run())

    def test_markdown_carries_the_disclaimer(self):
        with tempfile.TemporaryDirectory() as td:
            md = d.render_markdown(self._res(td))
            self.assertIn("NOT A COMPLIANCE CLAIM", md)
            self.assertIn("documentation question", md)

    def test_report_names_no_lane_as_failing(self):
        """Checked against the body with the disclaimer removed: the disclaimer
        says "not a defect in their code", so a raw substring check fails on the
        very sentence that guarantees the property."""
        with tempfile.TemporaryDirectory() as td:
            md = d.render_markdown(self._res(td))
            body = md.replace(d._DISCLAIMER, "").lower()
            for banned in ("non-compliant", "violation", "defect", "failing lane",
                           "certif"):
                self.assertNotIn(banned, body)

    def test_unverifiable_rows_appear_in_the_report(self):
        with tempfile.TemporaryDirectory() as td:
            res = (Fixture(td)
                   .lane("uiowa_rfq_18649_newlane", files={"README.md": "42 tests."})
                   .sweep([lane_rec("uiowa_rfq_18649_other", 5)])
                   .run())
            md = d.render_markdown(res)
            self.assertIn("Unverifiable", md)
            self.assertIn("None of these is counted as agreement", md)

    def test_write_outputs_produces_three_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            res = self._res(td)
            written = d.write_outputs(res, os.path.join(td, "out"))
            self.assertEqual(3, len(written))
            for p in written:
                self.assertTrue(os.path.exists(p))

    def test_cli_does_not_fail_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            self._res(td)
            self.assertEqual(0, d.main(["--root", td]))
            self.assertEqual(1, d.main(["--root", td, "--fail-on-contradiction"]))


class HostileInputTests(unittest.TestCase):
    def test_missing_run_sweep_makes_everything_unverifiable_not_clean(self):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "uiowa_rfq_18649_alpha"))
            with open(os.path.join(td, "uiowa_rfq_18649_alpha", "README.md"), "w") as f:
                f.write("30 tests.")
            res = d.run(td)
            self.assertEqual("", res.sweep_path)
            self.assertEqual(1, len(res.claims))
            self.assertEqual(d.UNVERIFIABLE, res.claims[0].verdict)
            self.assertEqual([], res.by_verdict(d.AGREES))

    def test_missing_root_returns_empty_rather_than_raising(self):
        res = d.run("/nonexistent-root-for-doc-drift")
        self.assertEqual([], res.claims)
        self.assertEqual(0, res.files_examined)

    def test_documentation_with_no_numeric_claim_produces_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            res = (Fixture(td)
                   .lane("uiowa_rfq_18649_alpha", files={"README.md": "A kit with tests."})
                   .sweep([lane_rec("uiowa_rfq_18649_alpha", 5)])
                   .run())
            self.assertEqual([], res.claims)

    def test_fenced_transcript_in_a_root_readme_is_not_a_claim(self):
        """A README pasting its own verbatim run output is showing evidence, and
        the sentence around it is what makes the claim."""
        with tempfile.TemporaryDirectory() as td:
            res = (Fixture(td)
                   .lane("uiowa_rfq_18649_alpha",
                         files={"README.md": "Output:\n\n```\nRan 99 tests in 0.1s\nOK\n```\n"})
                   .sweep([lane_rec("uiowa_rfq_18649_alpha", 36)])
                   .run())
            self.assertEqual([], res.claims)

    def test_unreadable_file_does_not_crash_the_screen(self):
        with tempfile.TemporaryDirectory() as td:
            f = Fixture(td).lane("uiowa_rfq_18649_alpha", files={"README.md": "5 tests."})
            f.sweep([lane_rec("uiowa_rfq_18649_alpha", 5)])
            bad = os.path.join(td, "uiowa_rfq_18649_alpha", "locked.md")
            with open(bad, "w") as fh:
                fh.write("9 tests.")
            os.chmod(bad, 0o000)
            try:
                res = f.run()
                self.assertGreaterEqual(res.files_examined, 1)
            finally:
                os.chmod(bad, 0o644)

    def test_malformed_sweep_json_is_reported_not_swallowed(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "uiowa_rfq_18649_run_sweep", "out")
            os.makedirs(p)
            with open(os.path.join(p, "run_sweep.json"), "w") as fh:
                fh.write("{not json")
            with self.assertRaises(json.JSONDecodeError):
                d.load_measurements(td)

    def test_screen_executes_nothing(self):
        """It reads a landed measurement; it must never run another lane's code."""
        src = open(os.path.join(HERE, "doc_claim_drift.py"), encoding="utf-8").read()
        for banned in ("subprocess", "os.system", "exec(", "eval("):
            self.assertNotIn(banned, src, f"screen must not use {banned}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
