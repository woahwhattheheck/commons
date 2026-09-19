#!/usr/bin/env python3
"""Tests for the readout deck-agreement engine (UIOWA-088).

Every hostile case here is a way a real readout deck drifts from its report:
a stale percentage, a citation to a finding that was renumbered, a priority gap
quietly dropped to save four minutes, an UNKNOWN rounded into a number so the
slide looks finished. Each one must be caught, and each one is asserted below.

Run: python3 -m unittest -v test_deck_architecture
"""

import copy
import json
import os
import shutil
import tempfile
import unittest

import deck_architecture as da

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(HERE, "data", "example-report.json")
DECK_PATH = os.path.join(HERE, "data", "example-readout-deck.json")
TEMPLATE_PATH = os.path.join(HERE, "templates", "readout-deck-template.json")


def codes(issues):
    return set(i.code for i in issues)


def err_codes(issues):
    return set(i.code for i in da.errors(issues))


class Base(unittest.TestCase):
    def setUp(self):
        self.report = da.load_report(REPORT_PATH)
        self.deck = da.load_deck(DECK_PATH)

    def slide(self, deck, sid):
        for s in deck["slides"]:
            if s["id"] == sid:
                return s
        raise AssertionError("no slide %s" % sid)


class TestBaseline(Base):
    def test_example_deck_agrees_with_example_report(self):
        issues = da.check(self.report, self.deck)
        self.assertEqual([], [i.as_dict() for i in da.errors(issues)])
        self.assertEqual([], [i.as_dict() for i in issues], "example deck should be clean of warnings too")

    def test_agenda_exactly_fills_the_session(self):
        core = [s for s in self.deck["slides"] if s["track"] == "core"]
        self.assertEqual(self.deck["meta"]["session_minutes"], sum(s["minutes"] for s in core))

    def test_every_core_section_present_once_in_order(self):
        core = [s["section"] for s in self.deck["slides"] if s["track"] == "core"]
        self.assertEqual(da.CORE_SECTIONS, core)


class TestFigureAgreement(Base):
    def test_contradicting_figure_is_caught(self):
        # The classic drift: the report was corrected, the slide was not.
        self.slide(self.deck, "S-04")["claims"][0]["value"] = 61
        self.assertIn("R003_FIGURE_DISAGREEMENT", err_codes(da.check(self.report, self.deck)))

    def test_contradicting_unit_is_caught(self):
        self.slide(self.deck, "S-04")["claims"][0]["unit"] = "of 12 deployments"
        self.assertIn("R003_FIGURE_DISAGREEMENT", err_codes(da.check(self.report, self.deck)))

    def test_understating_a_known_figure_is_caught(self):
        # Showing UNKNOWN where the report has a number is also disagreement.
        self.slide(self.deck, "S-04")["claims"][0]["value"] = "UNKNOWN"
        self.assertIn("R003_FIGURE_DISAGREEMENT", err_codes(da.check(self.report, self.deck)))

    def test_unresolved_measure_name_is_caught(self):
        self.slide(self.deck, "S-04")["claims"][0]["measure"] = "single_approval_rate"
        self.assertIn("R013_UNRESOLVED_MEASURE", err_codes(da.check(self.report, self.deck)))

    def test_matching_figure_stays_clean(self):
        # Guard against a checker that flags everything.
        self.slide(self.deck, "S-04")["claims"][0]["value"] = 58
        self.assertEqual(set(), err_codes(da.check(self.report, self.deck)))


class TestUnknownHandling(Base):
    def test_unknown_may_not_be_asserted_as_a_number(self):
        claim = self.slide(self.deck, "S-04")["claims"][2]
        self.assertEqual("demonstrated_recovery_time_hours", claim["measure"])
        claim["value"] = 4  # "about four hours, probably" -- the exact thing to refuse
        issues = da.check(self.report, self.deck)
        self.assertIn("R004_UNKNOWN_FABRICATION", err_codes(issues))

    def test_unknown_is_not_silently_turned_into_zero(self):
        claim = self.slide(self.deck, "S-04")["claims"][2]
        claim["value"] = 0
        self.assertIn("R004_UNKNOWN_FABRICATION", err_codes(da.check(self.report, self.deck)))

    def test_unknown_resource_estimate_may_not_be_asserted(self):
        claim = self.slide(self.deck, "S-06")["claims"][3]
        self.assertEqual("RES-002", claim["cites"])
        claim["value"] = 120
        self.assertIn("R004_UNKNOWN_FABRICATION", err_codes(da.check(self.report, self.deck)))

    def test_unknown_reaches_the_planning_table_as_unknown(self):
        rows = da.claim_rows(self.report, self.deck)
        target = [r for r in rows
                  if r["cites"] == "F-003" and r["measure"] == "demonstrated_recovery_time_hours"]
        self.assertTrue(target)
        for r in target:
            self.assertEqual("UNKNOWN", r["report_value"])
            self.assertEqual("UNKNOWN", r["deck_value"])
            self.assertEqual("UNKNOWN-IN-REPORT", r["agreement"])
            self.assertNotEqual(0, r["report_value"])

    def test_unknown_renders_as_words_not_a_blank(self):
        issues = da.check(self.report, self.deck)
        md = da.render_markdown(self.report, self.deck, issues)
        txt = da.render_ascii(self.report, self.deck)
        self.assertIn("UNKNOWN (not assessed)", md)
        self.assertIn("UNKNOWN (not assessed)", txt)

    def test_open_inputs_list_every_unknown_measure(self):
        idx = da.ReportIndex(self.report)
        opens = set((ref, name) for ref, name, _ in idx.open_inputs())
        self.assertIn(("F-003", "demonstrated_recovery_time_hours"), opens)
        self.assertIn(("RES-002", "one_time_effort"), opens)
        self.assertIn(("RES-002", "recurring_effort"), opens)
        self.assertIn(("F-005", "review_completion_rate_pct"), opens)


class TestTraceability(Base):
    def test_dangling_citation_is_caught(self):
        self.slide(self.deck, "S-04")["claims"][0]["cites"] = "F-999"
        self.assertIn("R002_DANGLING_CITATION", err_codes(da.check(self.report, self.deck)))

    def test_claim_citing_nothing_is_caught(self):
        self.slide(self.deck, "S-04")["claims"][0].pop("cites")
        self.assertIn("R002_DANGLING_CITATION", err_codes(da.check(self.report, self.deck)))

    def test_dropped_priority_finding_is_caught(self):
        # Cut the RIS recovery gap from the main body to "save time".
        s04 = self.slide(self.deck, "S-04")
        s04["claims"] = [c for c in s04["claims"] if c.get("cites") != "F-003"]
        issues = da.check(self.report, self.deck)
        self.assertIn("R005_OMITTED_PRIORITY_FINDING", err_codes(issues))
        detail = " ".join(i.detail for i in da.errors(issues))
        self.assertIn("F-003", detail)

    def test_medium_priority_finding_may_be_left_off(self):
        # Only HIGH priority gaps are mandatory; the rule must not overreach.
        s04 = self.slide(self.deck, "S-04")
        s04["claims"] = [c for c in s04["claims"] if c.get("cites") != "F-004"]
        s04["appendix_support"] = ["S-A2", "S-A3"]
        self.deck["slides"] = [s for s in self.deck["slides"] if s["id"] != "S-A7"]
        self.assertEqual(set(), err_codes(da.check(self.report, self.deck)))

    def test_unvalidated_strength_is_caught(self):
        # F-005 is a candidate strength the report did NOT validate.
        self.slide(self.deck, "S-03")["claims"].append(
            {"type": "strength", "cites": "F-005", "text": "Quarterly access review runs."})
        self.assertIn("R006_UNVALIDATED_STRENGTH", err_codes(da.check(self.report, self.deck)))

    def test_calling_a_gap_a_strength_is_caught(self):
        self.slide(self.deck, "S-03")["claims"].append(
            {"type": "strength", "cites": "F-002", "text": "IAM approvals are strong."})
        self.assertIn("R006_UNVALIDATED_STRENGTH", err_codes(da.check(self.report, self.deck)))

    def test_phase_disagreement_is_caught(self):
        for c in self.slide(self.deck, "S-05")["claims"]:
            if c["cites"] == "R-002":
                c["phase"] = "0-90"
        self.assertIn("R007_PHASE_DISAGREEMENT", err_codes(da.check(self.report, self.deck)))

    def test_phase_for_a_recommendation_not_on_the_roadmap_is_caught(self):
        self.report["roadmap"]["items"] = [i for i in self.report["roadmap"]["items"] if i["rec"] != "R-002"]
        self.assertIn("R007_PHASE_DISAGREEMENT", err_codes(da.check(self.report, self.deck)))

    def test_decision_pointing_at_a_disagreeing_phase_is_caught(self):
        for d in self.report["decisions"]:
            if d["id"] == "D-001":
                d["phase"] = "180+"
        self.assertIn("R014_DECISION_UNLINKED", err_codes(da.check(self.report, self.deck)))

    def test_decision_pointing_at_a_missing_recommendation_is_caught(self):
        for d in self.report["decisions"]:
            if d["id"] == "D-002":
                d["recommendation"] = "R-404"
        self.assertIn("R014_DECISION_UNLINKED", err_codes(da.check(self.report, self.deck)))


class TestAppendixDiscipline(Base):
    def test_main_body_figure_without_appendix_backing_is_caught(self):
        self.slide(self.deck, "S-04")["appendix_support"] = []
        self.assertIn("R008_MAIN_CLAIM_WITHOUT_APPENDIX", err_codes(da.check(self.report, self.deck)))

    def test_appendix_that_does_not_carry_the_cited_id_is_not_backing(self):
        # Pointing at an appendix slide about something else is not support.
        self.slide(self.deck, "S-04")["appendix_support"] = ["S-A1"]
        issues = da.check(self.report, self.deck)
        self.assertIn("R008_MAIN_CLAIM_WITHOUT_APPENDIX", err_codes(issues))

    def test_appendix_support_naming_a_nonexistent_slide_is_caught(self):
        self.slide(self.deck, "S-04")["appendix_support"] = ["S-A2", "S-A3", "S-A7", "S-A99"]
        issues = da.check(self.report, self.deck)
        self.assertIn("R008_MAIN_CLAIM_WITHOUT_APPENDIX", err_codes(issues))
        self.assertIn("S-A99", " ".join(i.detail for i in da.errors(issues)))

    def test_orphan_appendix_is_warned_not_fatal(self):
        self.deck["slides"].append({
            "id": "S-A9", "section": "appendix", "track": "appendix", "minutes": 0,
            "title": "Orphan", "bullets": ["x"], "claims": [], "appendix_support": [],
            "speaker_notes": [],
        })
        issues = da.check(self.report, self.deck)
        self.assertIn("R009_ORPHAN_APPENDIX", codes(issues))
        self.assertNotIn("R009_ORPHAN_APPENDIX", err_codes(issues))


class TestRoomUsability(Base):
    def test_agenda_overrun_is_caught(self):
        self.deck["meta"]["session_minutes"] = 30
        self.assertIn("R010_AGENDA_OVERRUN", err_codes(da.check(self.report, self.deck)))

    def test_agenda_underrun_is_warned(self):
        self.deck["meta"]["session_minutes"] = 120
        issues = da.check(self.report, self.deck)
        self.assertIn("R016_AGENDA_UNDERRUN", codes(issues))
        self.assertEqual(set(), err_codes(issues))

    def test_missing_session_minutes_is_an_error(self):
        self.deck["meta"]["session_minutes"] = 0
        self.assertIn("R010_AGENDA_OVERRUN", err_codes(da.check(self.report, self.deck)))

    def test_missing_speaker_notes_is_caught(self):
        self.slide(self.deck, "S-05")["speaker_notes"] = []
        self.assertIn("R011_MISSING_SPEAKER_NOTES", err_codes(da.check(self.report, self.deck)))

    def test_too_many_bullets_on_a_core_slide_is_caught(self):
        self.slide(self.deck, "S-01")["bullets"] = ["b%d" % i for i in range(da.MAX_CORE_BULLETS + 2)]
        self.assertIn("R012_DETAIL_IN_MAIN_BODY", err_codes(da.check(self.report, self.deck)))

    def test_an_essay_bullet_on_a_core_slide_is_caught(self):
        self.slide(self.deck, "S-01")["bullets"][0] = "x" * (da.MAX_BULLET_CHARS + 1)
        self.assertIn("R012_DETAIL_IN_MAIN_BODY", err_codes(da.check(self.report, self.deck)))

    def test_appendix_may_be_as_detailed_as_it_likes(self):
        self.slide(self.deck, "S-A2")["bullets"] = ["y" * 400] * 12
        self.assertEqual(set(), err_codes(da.check(self.report, self.deck)))


class TestStructure(Base):
    def test_wrong_report_is_caught(self):
        self.deck["meta"]["report_ref"] = "SOME-OTHER-REPORT"
        self.assertIn("R015_REPORT_MISMATCH", err_codes(da.check(self.report, self.deck)))

    def test_missing_core_section_is_caught(self):
        self.deck["slides"] = [s for s in self.deck["slides"] if s["id"] != "S-06"]
        issues = da.check(self.report, self.deck)
        self.assertIn("R001_SECTION_ORDER", err_codes(issues))
        self.assertIn("resources", " ".join(i.detail for i in da.errors(issues)))

    def test_sections_out_of_order_is_caught(self):
        slides = self.deck["slides"]
        i4 = next(i for i, s in enumerate(slides) if s["id"] == "S-04")
        i5 = next(i for i, s in enumerate(slides) if s["id"] == "S-05")
        slides[i4], slides[i5] = slides[i5], slides[i4]
        self.assertIn("R001_SECTION_ORDER", err_codes(da.check(self.report, self.deck)))

    def test_duplicate_slide_id_is_caught(self):
        dup = copy.deepcopy(self.slide(self.deck, "S-A2"))
        self.deck["slides"].append(dup)
        self.assertIn("R001_SECTION_ORDER", err_codes(da.check(self.report, self.deck)))

    def test_unknown_core_section_name_is_caught(self):
        self.slide(self.deck, "S-03")["section"] = "highlights"
        self.assertIn("R001_SECTION_ORDER", err_codes(da.check(self.report, self.deck)))


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

    def test_missing_file_raises_a_readable_error(self):
        with self.assertRaises(da.DeckDataError) as cm:
            da.load_report(os.path.join(self.tmp, "nope.json"))
        self.assertIn("file not found", str(cm.exception))

    def test_malformed_json_raises_a_readable_error(self):
        p = self.write("bad.json", '{"meta": {"report_id": "X",}')
        with self.assertRaises(da.DeckDataError) as cm:
            da.load_report(p)
        self.assertIn("not valid JSON", str(cm.exception))

    def test_json_that_is_not_an_object_raises(self):
        p = self.write("list.json", "[1, 2, 3]")
        with self.assertRaises(da.DeckDataError):
            da.load_deck(p)

    def test_report_missing_required_keys_names_them(self):
        p = self.write("thin.json", json.dumps({"meta": {"report_id": "X"}, "findings": []}))
        with self.assertRaises(da.DeckDataError) as cm:
            da.load_report(p)
        msg = str(cm.exception)
        for key in ("evidence", "recommendations", "roadmap", "resource_implications", "decisions"):
            self.assertIn(key, msg)

    def test_deck_with_no_slides_raises(self):
        p = self.write("empty.json", json.dumps(
            {"meta": {"deck_id": "D", "report_ref": "X", "session_minutes": 30}, "slides": []}))
        with self.assertRaises(da.DeckDataError) as cm:
            da.load_deck(p)
        self.assertIn("no slides", str(cm.exception))

    def test_slide_missing_id_raises_instead_of_keyerror(self):
        p = self.write("noid.json", json.dumps({
            "meta": {"deck_id": "D", "report_ref": "X", "session_minutes": 30},
            "slides": [{"section": "purpose", "track": "core", "title": "t"}]}))
        with self.assertRaises(da.DeckDataError) as cm:
            da.load_deck(p)
        self.assertIn("id", str(cm.exception))

    def test_report_with_no_findings_at_all_does_not_crash(self):
        # An assessment that produced nothing yet must still check, not explode.
        report = {
            "meta": {"report_id": "EMPTY"}, "evidence": [], "findings": [],
            "recommendations": [], "roadmap": {"phases": [], "items": []},
            "resource_implications": [], "decisions": [],
        }
        deck = {
            "meta": {"deck_id": "D", "report_ref": "EMPTY", "session_minutes": 10},
            "slides": [{"id": "S-01", "section": "purpose", "track": "core", "minutes": 10,
                        "title": "t", "bullets": ["b"], "claims": [],
                        "appendix_support": [], "speaker_notes": ["n"]}],
        }
        issues = da.check(report, deck)
        self.assertIn("R001_SECTION_ORDER", err_codes(issues))  # six sections missing
        self.assertNotIn("R005_OMITTED_PRIORITY_FINDING", err_codes(issues))


class TestRenderAndCli(Base):
    def test_blank_template_does_not_pass_as_a_finished_deck(self):
        template = da.load_deck(TEMPLATE_PATH)
        issues = da.check(self.report, template)
        self.assertTrue(da.errors(issues), "an unfilled template must not report agreement")
        self.assertIn("R015_REPORT_MISMATCH", err_codes(issues))
        self.assertIn("R013_UNRESOLVED_MEASURE", err_codes(issues))

    def test_ascii_render_is_pure_ascii_uniform_width_and_colorless(self):
        txt = da.render_ascii(self.report, self.deck)
        self.assertTrue(all(ord(ch) < 128 for ch in txt), "ASCII view must contain no non-ASCII bytes")
        self.assertNotIn("\x1b[", txt, "ASCII view must contain no terminal color escapes")
        widths = set(len(line) for line in txt.split("\n") if line)
        self.assertEqual({da.BOX_W}, widths)
        for mark in ("[ok]", "[??]"):
            self.assertIn(mark, txt)

    def test_ascii_render_shows_the_track_map_and_open_inputs(self):
        txt = da.render_ascii(self.report, self.deck)
        self.assertIn("EXECUTIVE PATH", txt)
        self.assertIn("PRACTITIONER DRILL-DOWN", txt)
        self.assertIn("OPEN INPUTS", txt)

    def test_failed_agreement_is_stamped_on_the_rendered_deck(self):
        # A drifted deck must not render as a clean handout.
        self.slide(self.deck, "S-04")["claims"][0]["value"] = 61
        issues = da.check(self.report, self.deck)
        md = da.render_markdown(self.report, self.deck, issues)
        self.assertIn("FAILED", md)
        self.assertIn("Do not present it", md)

    def test_planning_table_has_a_row_for_every_claim(self):
        rows = da.claim_rows(self.report, self.deck)
        claims = sum(len(s.get("claims", []) or []) for s in self.deck["slides"])
        no_claim_slides = sum(1 for s in self.deck["slides"] if not (s.get("claims") or []))
        self.assertEqual(claims + no_claim_slides, len(rows))
        self.assertEqual(set(), set(r["agreement"] for r in rows) - {
            "MATCH", "UNKNOWN-IN-REPORT", "LINK-ONLY", "NO-CLAIMS"})

    def test_render_is_byte_identical_across_runs(self):
        tmp = tempfile.mkdtemp()
        try:
            a, b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
            for out in (a, b):
                rc = da.main(["render", "--report", REPORT_PATH, "--deck", DECK_PATH, "--outdir", out])
                self.assertEqual(0, rc)
            for name in sorted(os.listdir(a)):
                with open(os.path.join(a, name), "rb") as fh:
                    one = fh.read()
                with open(os.path.join(b, name), "rb") as fh:
                    two = fh.read()
                self.assertEqual(one, two, "%s differs between runs" % name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_cli_check_exits_zero_on_agreement_and_one_on_drift(self):
        tmp = tempfile.mkdtemp()
        try:
            self.assertEqual(0, da.main(["check", "--report", REPORT_PATH, "--deck", DECK_PATH]))
            drifted = copy.deepcopy(self.deck)
            for s in drifted["slides"]:
                if s["id"] == "S-04":
                    s["claims"][0]["value"] = 61
            p = os.path.join(tmp, "drifted.json")
            with open(p, "w") as fh:
                json.dump(drifted, fh)
            self.assertEqual(1, da.main(["check", "--report", REPORT_PATH, "--deck", p]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_cli_reports_unreadable_input_without_a_traceback(self):
        self.assertEqual(2, da.main(["check", "--report", "/nonexistent/report.json", "--deck", DECK_PATH]))

    def test_every_rule_code_used_by_the_checker_is_documented(self):
        used = set()
        for mutate in (
            lambda d, r: d["slides"][0].__setitem__("speaker_notes", []),
            lambda d, r: d["meta"].__setitem__("report_ref", "X"),
        ):
            deck, report = copy.deepcopy(self.deck), copy.deepcopy(self.report)
            mutate(deck, report)
            used |= codes(da.check(report, deck))
        self.assertTrue(used <= set(da.RULES), "undocumented rule codes: %s" % (used - set(da.RULES)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
