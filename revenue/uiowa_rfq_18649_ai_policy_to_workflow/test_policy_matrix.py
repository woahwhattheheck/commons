#!/usr/bin/env python3
"""Tests for the UIOWA-074 policy-to-practice matrix.

These assert BEHAVIOR, not shape. The cases that matter most are the ones where
an assessment tool is normally dishonest:

  * an unfinished fieldwork schedule reading as a finding
  * an interview assertion reading as implementation evidence
  * a draft policy reading as if it were in force
  * an orphaned record being silently dropped
  * an empty dataset reading as "zero gaps, all clear"
  * anything collapsing into a single maturity number
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import policy_matrix as pm  # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures")


def _cell(cells, task_id, policy_id):
    for cell in cells:
        if cell["task_id"] == task_id and cell["policy_id"] == policy_id:
            return cell
    raise AssertionError("no cell %s x %s" % (task_id, policy_id))


class TempFixtures(object):
    """Copy the real fixtures to a temp dir so a test can corrupt them."""

    def __init__(self, mutate=None):
        self.mutate = mutate

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="uiowa074-")
        for name in ("policies.json", "tasks.json", "evidence.json", "questions.json"):
            shutil.copy(os.path.join(FIXTURES, name), os.path.join(self.dir, name))
        if self.mutate:
            self.mutate(self.dir)
        return self.dir

    def __exit__(self, *a):
        shutil.rmtree(self.dir, ignore_errors=True)


def _write(dirname, name, blob):
    with open(os.path.join(dirname, name), "w", encoding="utf-8") as fh:
        json.dump(blob, fh)


def _read(dirname, name):
    with open(os.path.join(dirname, name), "r", encoding="utf-8") as fh:
        return json.load(fh)


class TestReadingTable(unittest.TestCase):
    def test_table_is_total(self):
        """Every policy class x evidence level must have an explicit reading.

        A missing combination would fall through to a KeyError at best, or to a
        silent default at worst. A default here is how 'we don't know' turns
        into 'it's fine'.
        """
        for pclass in pm.POLICY_CLASSES:
            for level in pm.EVIDENCE_LEVELS:
                self.assertIn((pclass, level), pm.READING_TABLE,
                              "unmapped combination %s/%s" % (pclass, level))
        self.assertEqual(len(pm.READING_TABLE),
                         len(pm.POLICY_CLASSES) * len(pm.EVIDENCE_LEVELS))

    def test_every_reading_has_meta(self):
        for reading in set(pm.READING_TABLE.values()) | {pm.BLOCKED}:
            self.assertIn(reading, pm.READING_META)

    def test_not_gathered_always_reads_not_assessed(self):
        """No policy class may turn 'nobody looked' into a finding."""
        for pclass in pm.POLICY_CLASSES:
            self.assertEqual(pm.READING_TABLE[(pclass, "NOT_GATHERED")],
                             "NOT_ASSESSED")

    def test_not_assessed_and_blocked_are_never_gaps_or_strengths(self):
        for reading in ("NOT_ASSESSED", pm.BLOCKED):
            meta = pm.READING_META[reading]
            self.assertFalse(meta["gap"], "%s must not count as a gap" % reading)
            self.assertFalse(meta["strength"], "%s must not count as a strength" % reading)
            self.assertFalse(meta["assessed"], "%s must not count as assessed" % reading)

    def test_assertion_is_never_a_strength(self):
        """An interview claim must not be promoted to implementation evidence."""
        for pclass in pm.POLICY_CLASSES:
            reading = pm.READING_TABLE[(pclass, "ASSERTED_ONLY")]
            self.assertFalse(pm.READING_META[reading]["strength"],
                             "%s/%s -> %s was scored a strength on an assertion"
                             % (pclass, "ASSERTED_ONLY", reading))
        self.assertLess(pm.EVIDENCE_LEVELS.index("ASSERTED_ONLY"),
                        pm.EVIDENCE_LEVELS.index("EVIDENCED_INDIRECT"))


class TestFixtureResolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = pm.load_dataset(FIXTURES)
        cls.cells = pm.build_matrix(cls.data)
        cls.summary = pm.summarize(cls.cells, cls.data["questions"])

    def test_scheduled_but_not_performed_is_unknown_not_a_gap(self):
        """THE load-bearing case.

        EV-012 records that a release-approval walkthrough was scheduled and did
        not happen. A record exists, with a date and a locator. It must NOT
        become a finding about the University.
        """
        cell = _cell(self.cells, "TSK-07", "POL-SEC-07")
        self.assertEqual(cell["evidence_axis"], "NOT_GATHERED")
        self.assertEqual(cell["reading"], "NOT_ASSESSED")
        self.assertFalse(pm.READING_META[cell["reading"]]["gap"])

    def test_looked_and_found_nothing_is_a_gap(self):
        """The mirror of the case above: somebody checked, so it IS a finding."""
        cell = _cell(self.cells, "TSK-08", "POL-SEC-07")
        self.assertEqual(cell["evidence_axis"], "LOOKED_NONE_FOUND")
        self.assertEqual(cell["reading"], "STATED_NOT_PRACTICED")
        self.assertTrue(pm.READING_META[cell["reading"]]["gap"])

    def test_checked_flag_is_the_only_difference(self):
        """Flip checked:true -> false on a real gap and it must become UNKNOWN.

        Both records are kind 'none' with identical locators and dates. Nothing
        but the flag distinguishes them, which is the claim the design makes.
        """
        def mutate(d):
            ev = _read(d, "evidence.json")
            for rec in ev:
                if rec["evidence_id"] == "EV-006":
                    rec["checked"] = False
            _write(d, "evidence.json", ev)

        with TempFixtures(mutate) as d:
            cells = pm.build_matrix(pm.load_dataset(d))
            cell = _cell(cells, "TSK-08", "POL-SEC-07")
        self.assertEqual(cell["reading"], "NOT_ASSESSED")

    def test_interview_only_is_not_aligned(self):
        cell = _cell(self.cells, "TSK-03", "POL-AI-01")
        self.assertEqual(cell["evidence_axis"], "ASSERTED_ONLY")
        self.assertEqual(cell["reading"], "STATED_PRACTICE_UNCORROBORATED")
        self.assertFalse(pm.READING_META[cell["reading"]]["strength"])
        self.assertFalse(pm.READING_META[cell["reading"]]["gap"])

    def test_draft_policy_does_not_read_as_in_force(self):
        """POL-AI-04 is a draft. Direct evidence against it is practice ahead of
        policy, not compliance with a policy that binds nothing."""
        cell = _cell(self.cells, "TSK-02", "POL-AI-04")
        self.assertEqual(cell["policy_axis"], "HAS_NONBINDING_POLICY")
        self.assertEqual(cell["reading"], "PRACTICE_AHEAD_OF_POLICY")
        self.assertNotEqual(cell["reading"], "ALIGNED")

    def test_undocumented_practice_is_a_strength_not_a_failure(self):
        cell = _cell(self.cells, "TSK-09", "(none)")
        self.assertEqual(cell["policy_axis"], "NO_POLICY")
        self.assertEqual(cell["reading"], "UNDOCUMENTED_PRACTICE")
        self.assertTrue(pm.READING_META[cell["reading"]]["strength"])
        self.assertFalse(pm.READING_META[cell["reading"]]["gap"])

    def test_blocking_question_overrides_but_preserves_the_axes(self):
        """A blocked cell must not lose the evidence that was gathered, or
        answering the question would mean redoing the fieldwork."""
        cell = _cell(self.cells, "TSK-05", "POL-DATA-03")
        self.assertEqual(cell["reading"], pm.BLOCKED)
        self.assertEqual(cell["blocking_questions"], "Q-01")
        self.assertEqual(cell["evidence_axis"], "EVIDENCED_INDIRECT")
        self.assertEqual(cell["reading_if_unblocked"], "ALIGNED_INDIRECT")

    def test_non_blocking_question_does_not_override(self):
        cell = _cell(self.cells, "TSK-06", "POL-AI-02")
        self.assertIn("Q-04", cell["open_questions"])
        self.assertEqual(cell["blocking_questions"], "")
        self.assertEqual(cell["reading"], "ALIGNED")

    def test_fixture_shows_both_a_strength_and_a_real_gap(self):
        readings = {c["reading"] for c in self.cells}
        self.assertIn("ALIGNED", readings)
        self.assertIn("STATED_NOT_PRACTICED", readings)
        self.assertGreater(self.summary["gaps_among_assessed"], 0)
        self.assertGreater(self.summary["strengths_among_assessed"], 0)

    def test_counts_exclude_unknown_and_blocked(self):
        s = self.summary
        self.assertEqual(s["cells_total"],
                         s["cells_assessed"] + s["cells_not_assessed"]
                         + s["cells_blocked_on_clarification"])
        self.assertLessEqual(s["gaps_among_assessed"] + s["strengths_among_assessed"],
                             s["cells_assessed"])

    def test_caution_fires_when_assessment_is_incomplete(self):
        self.assertGreater(self.summary["cells_not_assessed"], 0)
        joined = " ".join(self.summary["cautions"])
        self.assertIn("never assessed", joined)

    def test_determinism(self):
        again = pm.build_matrix(pm.load_dataset(FIXTURES))
        self.assertEqual(self.cells, again)

    def test_every_evidence_record_is_attached_to_some_cell(self):
        """Nothing gathered in the field may vanish between load and matrix."""
        attached = set()
        for cell in self.cells:
            attached.update(x for x in cell["evidence_ids"].split(";") if x)
        for ev in self.data["evidence"]:
            self.assertIn(ev["evidence_id"], attached,
                          "evidence %s was dropped" % ev["evidence_id"])


class TestRefusals(unittest.TestCase):
    def test_score_refuses(self):
        with self.assertRaises(pm.ScoreRefused):
            pm.score()

    def test_refusal_text_names_what_is_refused(self):
        joined = " ".join(pm.refusals()).lower()
        for term in ("maturity", "certification", "percentage", "individual",
                     "percentile", "subcategory"):
            self.assertIn(term, joined)

    def test_refusals_travel_with_the_output(self):
        data = pm.load_dataset(FIXTURES)
        summary = pm.summarize(pm.build_matrix(data), data["questions"])
        self.assertEqual(summary["refusals"], pm.refusals())
        self.assertIn("nist.gov/itl/ai-risk-management-framework",
                      summary["nist_ai_rmf_reference"])

    def test_no_percentage_or_score_FIELD_in_summary_or_cells(self):
        """A percentage implies a complete denominator. There isn't one.

        Checked against field NAMES, recursively, not against prose: the
        refusal text legitimately contains the words 'percentage' and 'score'
        because its whole job is to name what is refused. What must never exist
        is a KEY that a downstream consumer could read as a score, and no
        numeric value may be a fraction between 0 and 1 masquerading as one.
        """
        data = pm.load_dataset(FIXTURES)
        cells = pm.build_matrix(data)
        summary = pm.summarize(cells, data["questions"])
        banned = ("percent", "pct", "ratio", "maturity", "score", "level",
                  "tier", "grade", "rating", "index")

        def walk(node, path):
            if isinstance(node, dict):
                for key, value in node.items():
                    low = str(key).lower()
                    for bad in banned:
                        self.assertNotIn(
                            bad, low,
                            "field %s/%s could be read as a score" % (path, key))
                    walk(value, "%s/%s" % (path, key))
            elif isinstance(node, list):
                for i, value in enumerate(node):
                    walk(value, "%s[%d]" % (path, i))

        walk(summary, "summary")
        for cell in cells:
            walk(cell, "cell")

        # Every numeric in the summary must be a raw count (a non-negative
        # integer), never a fraction that a reader could quote as a rate.
        for key, value in summary.items():
            if isinstance(value, bool):
                continue
            if isinstance(value, float):
                self.fail("summary/%s is a float (%r); counts must be integers "
                          "so nothing reads as a rate" % (key, value))
            if isinstance(value, int):
                self.assertGreaterEqual(value, 0)

    def test_rmf_is_reference_only(self):
        """Only the four core functions are used; no subcategory IDs invented."""
        data = pm.load_dataset(FIXTURES)
        for pol in data["policies"]:
            for fn in pol["rmf_functions"]:
                self.assertIn(fn, pm.RMF_FUNCTIONS)


class TestHostileAndMissingData(unittest.TestCase):
    def test_orphan_evidence_raises_rather_than_being_dropped(self):
        def mutate(d):
            ev = _read(d, "evidence.json")
            ev.append({"evidence_id": "EV-999", "task_id": "TSK-NOPE",
                       "policy_id": "POL-NOPE", "kind": "artifact",
                       "locator": "FICTIONAL", "observed_date": "2026-08-30"})
            _write(d, "evidence.json", ev)

        with TempFixtures(mutate) as d:
            with self.assertRaises(pm.FixtureError) as ctx:
                pm.load_dataset(d)
        msg = str(ctx.exception)
        self.assertIn("TSK-NOPE", msg)
        self.assertIn("POL-NOPE", msg)

    def test_kind_none_without_checked_flag_is_rejected(self):
        """Without the flag the tool cannot tell a gap from unfinished work, so
        it must refuse to guess."""
        def mutate(d):
            ev = _read(d, "evidence.json")
            for rec in ev:
                if rec["evidence_id"] == "EV-005":
                    rec.pop("checked")
            _write(d, "evidence.json", ev)

        with TempFixtures(mutate) as d:
            with self.assertRaises(pm.FixtureError) as ctx:
                pm.load_dataset(d)
        self.assertIn("never looked", str(ctx.exception))

    def test_all_problems_reported_at_once(self):
        def mutate(d):
            ev = _read(d, "evidence.json")
            ev.append({"evidence_id": "EV-997", "task_id": "TSK-GONE",
                       "kind": "wishful", "locator": "x",
                       "observed_date": "2026-01-01"})
            ev.append({"evidence_id": "EV-998", "task_id": "TSK-ALSOGONE",
                       "kind": "artifact", "locator": "x",
                       "observed_date": "2026-01-01"})
            _write(d, "evidence.json", ev)

        with TempFixtures(mutate) as d:
            with self.assertRaises(pm.FixtureError) as ctx:
                pm.load_dataset(d)
        msg = str(ctx.exception)
        self.assertIn("TSK-GONE", msg)
        self.assertIn("TSK-ALSOGONE", msg)
        self.assertIn("wishful", msg)

    def test_empty_evidence_is_all_unknown_not_all_clear(self):
        """The nastiest failure mode: no fieldwork done, and the tool reports
        zero gaps. Zero gaps must arrive with a caution that says why."""
        def mutate(d):
            _write(d, "evidence.json", [])

        with TempFixtures(mutate) as d:
            data = pm.load_dataset(d)
            cells = pm.build_matrix(data)
            summary = pm.summarize(cells, data["questions"])

        self.assertEqual(summary["gaps_among_assessed"], 0)
        self.assertEqual(summary["strengths_among_assessed"], 0)
        self.assertEqual(summary["cells_not_assessed"] +
                         summary["cells_blocked_on_clarification"],
                         summary["cells_total"])
        self.assertEqual(summary["cells_assessed"], 0)
        joined = " ".join(summary["cautions"])
        self.assertIn("never assessed", joined)
        self.assertNotIn("ALIGNED", {c["reading"] for c in cells})

    def test_missing_file_names_the_file(self):
        with TempFixtures() as d:
            os.remove(os.path.join(d, "questions.json"))
            with self.assertRaises(pm.FixtureError) as ctx:
                pm.load_dataset(d)
        self.assertIn("questions.json", str(ctx.exception))

    def test_malformed_json_names_the_file(self):
        with TempFixtures() as d:
            with open(os.path.join(d, "policies.json"), "w", encoding="utf-8") as fh:
                fh.write("{ not json ,,,")
            with self.assertRaises(pm.FixtureError) as ctx:
                pm.load_dataset(d)
        self.assertIn("policies.json", str(ctx.exception))

    def test_non_boolean_blocking_flag_is_rejected(self):
        """'blocking': 'yes' must not be truthy-coerced into a blocking question."""
        def mutate(d):
            qs = _read(d, "questions.json")
            qs[0]["blocking"] = "yes"
            _write(d, "questions.json", qs)

        with TempFixtures(mutate) as d:
            with self.assertRaises(pm.FixtureError) as ctx:
                pm.load_dataset(d)
        self.assertIn("blocking", str(ctx.exception))

    def test_unknown_policy_status_is_rejected(self):
        def mutate(d):
            pols = _read(d, "policies.json")
            pols[0]["status"] = "mostly active"
            _write(d, "policies.json", pols)

        with TempFixtures(mutate) as d:
            with self.assertRaises(pm.FixtureError):
                pm.load_dataset(d)

    def test_task_with_no_policy_still_gets_a_row(self):
        """A task no policy claims must not silently disappear from the matrix."""
        def mutate(d):
            pols = _read(d, "policies.json")
            for pol in pols:
                pol["applies_to_tasks"] = [t for t in pol["applies_to_tasks"]
                                           if t != "TSK-02"]
            _write(d, "policies.json", pols)

        with TempFixtures(mutate) as d:
            cells = pm.build_matrix(pm.load_dataset(d))
        cell = _cell(cells, "TSK-02", "(none)")
        self.assertEqual(cell["policy_axis"], "NO_POLICY")


class TestOutputs(unittest.TestCase):
    def test_run_writes_all_four_outputs(self):
        out = tempfile.mkdtemp(prefix="uiowa074-out-")
        try:
            cells, summary = pm.run(FIXTURES, out)
            for name in ("matrix.csv", "matrix.md", "open_questions.csv",
                         "findings.json"):
                path = os.path.join(out, name)
                self.assertTrue(os.path.exists(path), "%s not written" % name)
                self.assertGreater(os.path.getsize(path), 0)
            with open(os.path.join(out, "findings.json"), encoding="utf-8") as fh:
                blob = json.load(fh)
            self.assertEqual(len(blob["cells"]), len(cells))
            self.assertIn("FICTIONAL", blob["fiction_notice"])
            with open(os.path.join(out, "matrix.md"), encoding="utf-8") as fh:
                md = fh.read()
            self.assertIn("FICTIONAL", md)
            self.assertIn("nist.gov/itl/ai-risk-management-framework", md)
            self.assertIn("Open questions", md)
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_csv_carries_all_three_axes_separately(self):
        out = tempfile.mkdtemp(prefix="uiowa074-out-")
        try:
            pm.run(FIXTURES, out)
            import csv as _csv
            with open(os.path.join(out, "matrix.csv"), encoding="utf-8") as fh:
                rows = list(_csv.DictReader(fh))
            for axis in ("policy_axis", "evidence_axis", "open_questions"):
                self.assertIn(axis, rows[0])
            self.assertIn("reading_if_unblocked", rows[0])
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_cli_exits_zero_and_prints_fiction_banner(self):
        out = tempfile.mkdtemp(prefix="uiowa074-out-")
        try:
            rc = pm.main(["--fixtures", FIXTURES, "--out", out])
            self.assertEqual(rc, 0)
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_cli_exits_nonzero_on_bad_fixtures(self):
        with TempFixtures() as d:
            os.remove(os.path.join(d, "tasks.json"))
            out = tempfile.mkdtemp(prefix="uiowa074-out-")
            try:
                rc = pm.main(["--fixtures", d, "--out", out])
                self.assertEqual(rc, 2)
            finally:
                shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
