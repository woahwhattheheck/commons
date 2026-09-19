#!/usr/bin/env python3
"""Tests for the cross-artifact roadmap coherence checker.

Run: python3 -m unittest -v test_roadmap_coherence
"""

import contextlib
import copy
import io
import json
import os
import shutil
import tempfile
import unittest

import roadmap_coherence as rc

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
REPORT = os.path.join(D, "coherent-report.json")
PLAN = os.path.join(D, "coherent-plan.json")
DECK = os.path.join(D, "coherent-deck.json")
BAD_REPORT = os.path.join(D, "incoherent-report.json")
DRIFTED_PLAN = os.path.join(D, "drifted-plan.json")
UNDECLARED = os.path.join(D, "undeclared-report.json")


def run_cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = rc.main(argv)
    return code


def codes(findings):
    return set(f.code for f in findings)


def err_codes(findings):
    return set(f.code for f in rc.errors(findings))


class Base(unittest.TestCase):
    def setUp(self):
        self.report = rc.load_report(REPORT)
        self.plan = rc.load_plan(PLAN)
        self.deck = rc.load_deck(DECK)


class TestCoherentBaseline(Base):
    def test_the_three_artifacts_agree(self):
        findings = rc.check(self.report, self.plan, self.deck)
        self.assertEqual([], [f.as_dict() for f in findings])
        self.assertEqual(rc.COHERENT, rc.verdict(findings, self.report))

    def test_cli_exits_zero_on_the_coherent_set(self):
        self.assertEqual(0, run_cli(["check", "--report", REPORT, "--plan", PLAN, "--deck", DECK]))


class TestReportRoadmap(Base):
    def test_prerequisite_after_its_dependent_is_caught(self):
        findings = rc.check(rc.load_report(BAD_REPORT), self.plan, self.deck)
        self.assertIn("RC002_REPORT_PREREQ_AFTER_DEPENDENT", err_codes(findings))
        self.assertEqual(rc.INCOHERENT, rc.verdict(findings, self.report))

    def test_dependency_cycle_is_caught(self):
        for i in self.report["roadmap"]["items"]:
            if i["rec"] == "R-001":
                i["depends_on"] = ["R-004"]
        findings = rc.check(self.report, None, None)
        self.assertIn("RC003_REPORT_DEPENDENCY_CYCLE", err_codes(findings))

    def test_dangling_dependency_is_caught(self):
        for i in self.report["roadmap"]["items"]:
            if i["rec"] == "R-004":
                i["depends_on"] = ["R-001", "R-999"]
        findings = rc.check(self.report, None, None)
        self.assertIn("RC004_REPORT_DANGLING_DEPENDENCY", err_codes(findings))

    def test_same_phase_prerequisite_is_allowed(self):
        for i in self.report["roadmap"]["items"]:
            if i["rec"] == "R-002":
                i["phase"] = "0-90"
        findings = rc.check(self.report, None, None)
        self.assertNotIn("RC002_REPORT_PREREQ_AFTER_DEPENDENT", err_codes(findings))


class TestNotAssessed(unittest.TestCase):
    def test_no_declared_dependencies_reads_not_assessed_not_coherent(self):
        report = rc.load_report(UNDECLARED)
        findings = rc.check(report, None, None)
        self.assertIn("RC001_REPORT_ROADMAP_NOT_ASSESSED", codes(findings))
        self.assertEqual(rc.NOT_ASSESSED, rc.verdict(findings, report))
        self.assertNotEqual(rc.COHERENT, rc.verdict(findings, report))

    def test_empty_dependency_lists_are_a_considered_answer(self):
        report = rc.load_report(REPORT)
        for i in report["roadmap"]["items"]:
            i["depends_on"] = []
        findings = rc.check(report, None, None)
        self.assertNotIn("RC001_REPORT_ROADMAP_NOT_ASSESSED", codes(findings))
        self.assertEqual(rc.COHERENT, rc.verdict(findings, report))

    def test_not_assessed_is_not_an_error_exit(self):
        self.assertEqual(0, run_cli(["check", "--report", UNDECLARED]))


class TestCrossArtifact(Base):
    def test_plan_phase_drift_is_caught_naming_both_artifacts(self):
        findings = rc.check(self.report, rc.load_plan(DRIFTED_PLAN), self.deck)
        self.assertIn("RC005_PLAN_PHASE_DISAGREES_WITH_REPORT", err_codes(findings))
        detail = " ".join(f.detail for f in rc.errors(findings))
        self.assertIn("report roadmap says", detail)
        self.assertIn("the plan's", detail)

    def test_deck_phase_drift_is_caught(self):
        for s in self.deck["slides"]:
            for c in s.get("claims") or []:
                if c.get("cites") == "R-002":
                    c["phase"] = "0-90"
        findings = rc.check(self.report, self.plan, self.deck)
        self.assertIn("RC006_DECK_PHASE_DISAGREES_WITH_REPORT", err_codes(findings))

    def test_recommendation_with_no_work_behind_it_is_caught(self):
        self.plan["items"] = [i for i in self.plan["items"] if i.get("rec") != "R-003"]
        findings = rc.check(self.report, self.plan, self.deck)
        self.assertIn("RC011_RECOMMENDATION_MISSING_FROM_PLAN", err_codes(findings))

    def test_plan_item_with_no_recommendation_is_caught(self):
        self.plan["items"].append({"id": "W-9", "rec": "R-777", "title": "orphan",
                                   "proposed_phase": "0-90", "prerequisites": [], "effort": {}})
        findings = rc.check(self.report, self.plan, self.deck)
        self.assertIn("RC012_PLAN_ITEM_WITHOUT_RECOMMENDATION", err_codes(findings))

    def test_dependency_the_plan_enforces_but_the_report_omits(self):
        for i in self.report["roadmap"]["items"]:
            if i["rec"] == "R-004":
                i["depends_on"] = ["R-001"]
        findings = rc.check(self.report, self.plan, self.deck)
        self.assertIn("RC007_PLAN_DEPENDENCY_MISSING_FROM_REPORT", codes(findings))

    def test_dependency_the_report_declares_but_the_plan_omits(self):
        for i in self.plan["items"]:
            if i["id"] == "W-5":
                i["prerequisites"] = ["W-2"]
        findings = rc.check(self.report, self.plan, self.deck)
        self.assertIn("RC008_REPORT_DEPENDENCY_MISSING_FROM_PLAN", codes(findings))


class TestCollapseRule(Base):
    def test_last_and_first_can_disagree(self):
        plan = copy.deepcopy(self.plan)
        plan["items"].append({"id": "W-6", "rec": "R-003", "title": "later review",
                              "proposed_phase": "90-180", "prerequisites": ["W-3"], "effort": {}})
        last = rc.plan_view(plan, "last").phase_by_rec["R-003"]
        first = rc.plan_view(plan, "first").phase_by_rec["R-003"]
        self.assertEqual("90-180", last)
        self.assertEqual("0-90", first)

    def test_a_disagreement_that_only_one_rule_produces_is_named(self):
        plan = copy.deepcopy(self.plan)
        plan["items"].append({"id": "W-6", "rec": "R-003", "title": "later review",
                              "proposed_phase": "90-180", "prerequisites": ["W-3"], "effort": {}})
        findings = rc.check(self.report, plan, self.deck, "last")
        self.assertIn("RC013_COLLAPSE_RULE_DECIDES", codes(findings))
        self.assertIn("RC005_PLAN_PHASE_DISAGREES_WITH_REPORT", err_codes(findings))

    def test_the_rule_used_is_named_in_the_finding(self):
        findings = rc.check(self.report, rc.load_plan(DRIFTED_PLAN), self.deck, "last")
        detail = " ".join(f.detail for f in rc.errors(findings))
        self.assertIn("collapse rule: last", detail)

    def test_an_unknown_collapse_rule_is_rejected(self):
        with self.assertRaises(rc.InputError):
            rc.plan_view(self.plan, "median")


class TestProseDependencies(Base):
    def test_prose_dependency_without_a_field_is_caught(self):
        report = rc.load_report(UNDECLARED)
        findings = rc.check(report, None, self.deck)
        self.assertIn("RC009_PROSE_DEPENDENCY_UNBACKED", codes(findings))
        detail = " ".join(f.detail for f in findings)
        self.assertIn("R-004", detail)
        self.assertIn("only as a sentence", detail)

    def test_prose_backed_by_a_field_is_not_flagged(self):
        findings = rc.check(self.report, self.plan, self.deck)
        self.assertNotIn("RC009_PROSE_DEPENDENCY_UNBACKED", codes(findings))

    def test_a_partly_backed_prose_claim_is_still_caught(self):
        for i in self.report["roadmap"]["items"]:
            if i["rec"] == "R-004":
                i["depends_on"] = ["R-001"]
        findings = rc.check(self.report, None, self.deck)
        self.assertIn("RC009_PROSE_DEPENDENCY_UNBACKED", err_codes(findings))

    def test_prose_without_a_dependency_sentence_is_left_alone(self):
        deck = {"meta": {}, "slides": [{"id": "S-1", "bullets": [
            "R-001 and R-003 touch different systems, so they run in parallel.",
            "R-002 is scheduled in the second window."], "claims": [], "speaker_notes": []}]}
        found = rc.deck_prose_dependencies(deck)
        self.assertEqual([], found, "only 'X depends on Y' is read as a claim")

    def test_a_dependency_never_put_in_front_of_the_room_is_flagged(self):
        deck = {"meta": {}, "slides": [{"id": "S-1", "bullets": ["Sequence as agreed."],
                                        "claims": [], "speaker_notes": []}]}
        findings = rc.check(self.report, None, deck)
        self.assertIn("RC010_DEPENDENCY_NEVER_PRESENTED", codes(findings))


class TestHostileInput(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, text):
        p = os.path.join(self.tmp, name)
        with open(p, "w") as fh:
            fh.write(text)
        return p

    def test_missing_file(self):
        with self.assertRaises(rc.InputError) as cm:
            rc.load_report(os.path.join(self.tmp, "nope.json"))
        self.assertIn("file not found", str(cm.exception))

    def test_malformed_json(self):
        p = self.write("bad.json", '{"roadmap": {,}')
        with self.assertRaises(rc.InputError) as cm:
            rc.load_report(p)
        self.assertIn("not valid JSON", str(cm.exception))

    def test_report_without_a_roadmap(self):
        p = self.write("t.json", json.dumps({"meta": {}}))
        with self.assertRaises(rc.InputError) as cm:
            rc.load_report(p)
        self.assertIn("no roadmap", str(cm.exception))

    def test_roadmap_without_items(self):
        p = self.write("t.json", json.dumps({"roadmap": {"phases": []}}))
        with self.assertRaises(rc.InputError) as cm:
            rc.load_report(p)
        self.assertIn("items", str(cm.exception))

    def test_plan_without_items(self):
        p = self.write("t.json", json.dumps({"meta": {}}))
        with self.assertRaises(rc.InputError) as cm:
            rc.load_plan(p)
        self.assertIn("no items", str(cm.exception))

    def test_missing_optional_artifacts_do_not_crash(self):
        report = rc.load_report(REPORT)
        findings = rc.check(report, None, None)
        self.assertEqual(rc.COHERENT, rc.verdict(findings, report))

    def test_a_plan_item_with_no_rec_is_ignored_not_crashed(self):
        plan = rc.load_plan(PLAN)
        plan["items"].append({"id": "W-X", "title": "unlinked", "proposed_phase": "0-90",
                              "prerequisites": [], "effort": {}})
        findings = rc.check(rc.load_report(REPORT), plan, None)
        self.assertNotIn("RC012_PLAN_ITEM_WITHOUT_RECOMMENDATION", err_codes(findings))

    def test_cli_reports_unreadable_input_without_a_traceback(self):
        self.assertEqual(2, run_cli(["check", "--report", "/nonexistent.json"]))


class TestOutputs(Base):
    def test_ascii_is_pure_ascii_uniform_width_and_colourless(self):
        findings = rc.check(self.report, self.plan, self.deck)
        text = rc.render_ascii(self.report, self.plan, self.deck, findings)
        self.assertTrue(all(ord(c) < 128 for c in text))
        self.assertNotIn("\x1b[", text)
        self.assertEqual({rc.W}, set(len(l) for l in text.split("\n") if l))
        self.assertIn("LEGEND", text)

    def test_ascii_shows_the_three_way_table(self):
        findings = rc.check(self.report, self.plan, self.deck)
        text = rc.render_ascii(self.report, self.plan, self.deck, findings)
        for token in ("report", "plan", "deck", "R-004"):
            self.assertIn(token, text)

    def test_render_is_byte_identical_across_runs(self):
        tmp = tempfile.mkdtemp()
        try:
            a, b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
            for out in (a, b):
                run_cli(["report", "--report", REPORT, "--plan", PLAN, "--deck", DECK,
                         "--outdir", out])
            for name in sorted(os.listdir(a)):
                with open(os.path.join(a, name), "rb") as fh:
                    one = fh.read()
                with open(os.path.join(b, name), "rb") as fh:
                    two = fh.read()
                self.assertEqual(one, two, "%s differs between runs" % name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_every_emitted_code_is_documented(self):
        used = set()
        for report_path, plan_path in ((REPORT, PLAN), (BAD_REPORT, PLAN),
                                       (REPORT, DRIFTED_PLAN), (UNDECLARED, PLAN)):
            used |= codes(rc.check(rc.load_report(report_path), rc.load_plan(plan_path), self.deck))
        self.assertTrue(used <= set(rc.RULES), "undocumented codes: %s" % (used - set(rc.RULES)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
