"""Tests for evidence-window agreement.

The rules refuse claims, so the tests that carry the most weight are the ones
asserting a rule does NOT fire on a claim that is properly supported, and the
one asserting that a single bad record produces a single finding.
"""
from __future__ import annotations

import ast
import contextlib
import datetime
import io
import json
import os
import tempfile
import unittest

import check_window
import window as W

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
UNSOUND = os.path.join(FIX, "claims_UNSOUND.json")
SOUND = os.path.join(FIX, "claims_SOUND.json")

AS_OF = datetime.date(2026, 9, 19)
SETTINGS = {"freshness_days": 180, "min_coverage": 0.60}


def d(text: str) -> datetime.date:
    return datetime.date.fromisoformat(text)


def ev(**pairs) -> dict:
    return {k: W.Evidence(id=k, date=(d(v) if v else None)) for k, v in pairs.items()}


def claim(**kw) -> W.Claim:
    base = dict(id="C-T", text="t", tense="PAST", window_start=None,
                window_end=None, evidence_ids=[])
    base.update(kw)
    return W.Claim(**base)


def codes(findings):
    return {f.code for f in findings}


def run(evidence, claims, settings=None):
    return W.check(AS_OF, evidence, claims, settings or SETTINGS)


class TestBeforeAfterPair(unittest.TestCase):
    def test_unsound_set_fails(self):
        as_of, evidence, claims, settings = W.load(UNSOUND)
        self.assertTrue(any(f.severity == W.ERROR
                            for f in W.check(as_of, evidence, claims, settings)))

    def test_sound_set_passes(self):
        as_of, evidence, claims, settings = W.load(SOUND)
        self.assertEqual(
            [f.to_dict() for f in W.check(as_of, evidence, claims, settings)], [])

    def test_every_rule_fires_on_the_unsound_set(self):
        as_of, evidence, claims, settings = W.load(UNSOUND)
        found = codes(W.check(as_of, evidence, claims, settings))
        for code in ("WINDOW_NOT_COVERED", "SINGLE_DATE_SUPPORTS_A_PERIOD",
                     "STALE_EVIDENCE_FOR_PRESENT_TENSE", "EVIDENCE_OUTSIDE_WINDOW",
                     "UNDATED_EVIDENCE", "EVIDENCE_AFTER_ASOF",
                     "WINDOW_ENDS_AFTER_ASOF", "WINDOW_INVERTED",
                     "NO_EVIDENCE_CITED", "EVIDENCE_NOT_FOUND", "PARTIAL_WINDOW"):
            self.assertIn(code, found, f"{code} never fired")

    def test_one_bad_record_produces_one_finding(self):
        """Post-as_of evidence is withdrawn from the window analysis rather than
        cascading into out-of-window and single-date findings too."""
        as_of, evidence, claims, settings = W.load(UNSOUND)
        found = [f for f in W.check(as_of, evidence, claims, settings)
                 if f.claim_id == "C-SYN-005"]
        self.assertEqual([f.code for f in found], ["EVIDENCE_AFTER_ASOF"])


class TestCoverage(unittest.TestCase):
    def test_four_days_of_evidence_cannot_describe_ninety(self):
        evidence = ev(**{"E-1": "2026-07-08", "E-2": "2026-07-11"})
        found = run(evidence, [claim(window_start=d("2026-06-22"),
                                     window_end=d("2026-09-19"),
                                     evidence_ids=["E-1", "E-2"])])
        self.assertIn("WINDOW_NOT_COVERED", codes(found))
        self.assertIn("2026-07-08 to 2026-07-11", found[0].restatement)

    def test_evidence_spanning_most_of_the_window_is_accepted(self):
        evidence = ev(**{"E-1": "2026-06-25", "E-2": "2026-09-10"})
        found = run(evidence, [claim(window_start=d("2026-06-22"),
                                     window_end=d("2026-09-19"),
                                     evidence_ids=["E-1", "E-2"])])
        self.assertEqual(codes(found), set())

    def test_single_date_supersedes_the_coverage_rule(self):
        evidence = ev(**{"E-1": "2026-07-08", "E-2": "2026-07-08"})
        found = codes(run(evidence, [claim(window_start=d("2026-06-22"),
                                           window_end=d("2026-09-19"),
                                           evidence_ids=["E-1", "E-2"])]))
        self.assertIn("SINGLE_DATE_SUPPORTS_A_PERIOD", found)
        self.assertNotIn("WINDOW_NOT_COVERED", found)

    def test_coverage_threshold_is_configurable(self):
        evidence = ev(**{"E-1": "2026-06-25", "E-2": "2026-09-10"})
        c = [claim(window_start=d("2026-06-22"), window_end=d("2026-09-19"),
                   evidence_ids=["E-1", "E-2"])]
        self.assertEqual(codes(run(evidence, c)), set())
        strict = {"freshness_days": 180, "min_coverage": 0.95}
        self.assertIn("WINDOW_NOT_COVERED", codes(run(evidence, c, strict)))


class TestFreshness(unittest.TestCase):
    def test_present_tense_on_old_evidence_is_caught(self):
        evidence = ev(**{"E-1": "2025-02-14"})
        found = [f for f in run(evidence, [claim(
            tense="PRESENT", window_start=d("2025-01-01"),
            window_end=d("2025-03-01"), evidence_ids=["E-1"])])
            if f.code == "STALE_EVIDENCE_FOR_PRESENT_TENSE"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].detail["age_days"], 582)

    def test_past_tense_on_old_evidence_is_not_a_staleness_problem(self):
        """A dated historical statement does not go stale; a present-tense one does."""
        evidence = ev(**{"E-1": "2025-01-05", "E-2": "2025-02-25"})
        found = codes(run(evidence, [claim(
            tense="PAST", window_start=d("2025-01-01"), window_end=d("2025-03-01"),
            evidence_ids=["E-1", "E-2"])]))
        self.assertNotIn("STALE_EVIDENCE_FOR_PRESENT_TENSE", found)

    def test_present_tense_on_current_evidence_is_accepted(self):
        evidence = ev(**{"E-1": "2026-08-05", "E-2": "2026-09-15"})
        found = codes(run(evidence, [claim(
            tense="PRESENT", window_start=d("2026-08-01"),
            window_end=d("2026-09-19"), evidence_ids=["E-1", "E-2"])]))
        self.assertEqual(found, set())


class TestMissingData(unittest.TestCase):
    def test_undated_evidence_is_not_assumed_in_window(self):
        evidence = ev(**{"E-1": None})
        found = run(evidence, [claim(window_start=d("2026-08-01"),
                                     window_end=d("2026-08-31"),
                                     evidence_ids=["E-1"])])
        self.assertIn("UNDATED_EVIDENCE", codes(found))
        self.assertNotIn("WINDOW_NOT_COVERED", codes(found))

    def test_a_claim_citing_nothing_is_caught(self):
        found = run({}, [claim(window_start=d("2026-06-01"),
                               window_end=d("2026-08-31"), evidence_ids=[])])
        self.assertEqual(codes(found), {"NO_EVIDENCE_CITED"})

    def test_a_citation_to_a_record_that_does_not_exist_is_caught(self):
        found = run({}, [claim(window_start=d("2026-06-01"),
                               window_end=d("2026-06-30"),
                               evidence_ids=["E-NOPE"])])
        self.assertIn("EVIDENCE_NOT_FOUND", codes(found))

    def test_an_untimed_claim_with_dated_evidence_is_left_alone(self):
        """No window stated and none implied: nothing for this kit to say."""
        evidence = ev(**{"E-1": "2026-07-08"})
        self.assertEqual(codes(run(evidence, [claim(evidence_ids=["E-1"])])), set())


class TestLoader(unittest.TestCase):
    def _write(self, payload) -> str:
        path = os.path.join(tempfile.mkdtemp(), "c.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        return path

    def test_as_of_is_required(self):
        with self.assertRaises(W.WindowError) as ctx:
            W.load(self._write({"synthetic": True, "claims": []}))
        self.assertIn("reproducible", str(ctx.exception))

    def test_input_must_be_marked_synthetic(self):
        with self.assertRaises(W.WindowError):
            W.load(self._write({"as_of": "2026-09-19", "claims": []}))

    def test_a_malformed_date_is_refused_not_guessed(self):
        with self.assertRaises(W.WindowError):
            W.load(self._write({"synthetic": True, "as_of": "2026-09-19",
                                "evidence": [{"id": "E-1", "date": "19/09/2026"}]}))

    def test_duplicate_evidence_id_is_refused(self):
        with self.assertRaises(W.WindowError):
            W.load(self._write({"synthetic": True, "as_of": "2026-09-19",
                                "evidence": [{"id": "E-1", "date": "2026-01-01"},
                                             {"id": "E-1", "date": "2026-02-01"}]}))

    def test_unknown_tense_is_refused(self):
        with self.assertRaises(W.WindowError):
            W.load(self._write({"synthetic": True, "as_of": "2026-09-19",
                                "claims": [{"id": "C", "text": "t",
                                            "tense": "FUTURE"}]}))


class TestCliAndDeterminism(unittest.TestCase):
    def test_exit_codes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(check_window.main(["--claims", UNSOUND]), 1)
            self.assertEqual(check_window.main(["--claims", SOUND]), 0)

    def test_missing_file_reports_rather_than_crashing(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = check_window.main(["--claims", os.path.join(FIX, "nope.json")])
        self.assertEqual(code, 2)
        self.assertIn("could not load claims", err.getvalue())

    def test_no_wall_clock_is_consulted(self):
        """STATIC TRIPWIRE, not behavioural coverage.

        Staleness is judged against the declared as_of, so the result cannot
        change because the calendar moved. This scans executable lines only --
        comments and the module docstring are stripped first, because an earlier
        version of this test failed on the phrase appearing in prose, which is a
        tripwire catching the documentation rather than the code.
        """
        source = open(os.path.join(HERE, "window.py"), encoding="utf-8").read()
        module = ast.parse(source)
        ast.get_docstring(module)   # confirms it parses as a module
        body = "\n".join(
            line.split("#", 1)[0]
            for line in ast.unparse(module).splitlines())
        self.assertNotIn("datetime.now", body)
        self.assertNotIn("date.today", body)

    def test_two_runs_are_byte_identical(self):
        a, b = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(a):
            check_window.main(["--claims", UNSOUND, "--format", "json"])
        with contextlib.redirect_stdout(b):
            check_window.main(["--claims", UNSOUND, "--format", "json"])
        self.assertEqual(a.getvalue(), b.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
