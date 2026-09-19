"""Tests for the claim-language audit.

The load-bearing ones are the false-positive tests. A checker that flags
everything gets switched off, taking the rules that were catching something
with it, so several tests here assert that a rule does NOT fire.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest

import claim_audit as ca
import rules as R

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
REGISTER = os.path.join(FIX, "register.json")
BAD = os.path.join(FIX, "exec_summary_BAD.md")
GOOD = os.path.join(FIX, "exec_summary_GOOD.md")


def audit_text(text: str, register=None, doc="t.md"):
    units, problems = ca.segment(doc, text)
    return problems + ca.audit_units(units, register)


def codes(findings) -> set[str]:
    return {f.code for f in findings}


class TestBeforeAfterPair(unittest.TestCase):
    def setUp(self):
        self.register = ca.load_register(REGISTER)

    def test_promotional_draft_is_rejected(self):
        found, _ = ca.audit_document(BAD, self.register)
        errors = [f for f in found if f.severity == R.ERROR]
        self.assertGreaterEqual(len(errors), 20)

    def test_traceable_draft_passes(self):
        found, _ = ca.audit_document(GOOD, self.register)
        self.assertEqual([f.to_dict() for f in found], [])

    def test_every_rule_fires_somewhere_in_the_bad_draft(self):
        found, _ = ca.audit_document(BAD, self.register)
        for code in ("PROMOTIONAL_LANGUAGE", "UNSOURCED_CLAIM",
                     "UNQUANTIFIED_COMPARATIVE", "UNKNOWN_PRESENTED_AS_FINDING",
                     "CONTRADICTED_FINDING_CITED_AS_SUPPORT", "DANGLING_CITATION",
                     "ABSOLUTE_WITHOUT_SOURCE", "EMPTY_SUPPRESSION"):
            self.assertIn(code, codes(found), f"{code} never fired on the bad draft")

    def test_overlapping_terms_report_once(self):
        """'best practice' inside 'industry best practice' is one defect."""
        found = audit_text("Delivery reflects industry best practice.")
        promo = [f for f in found if f.code == "PROMOTIONAL_LANGUAGE"]
        self.assertEqual(len(promo), 1, [f.term for f in promo])


class TestTiering(unittest.TestCase):
    def test_tier_a_fires_even_with_a_number_and_a_citation(self):
        found = audit_text("The 12 services reviewed are world-class [F-SYN-001].",
                           {"F-SYN-001": {"state": "SUPPORTED"}})
        self.assertIn("PROMOTIONAL_LANGUAGE", codes(found))

    def test_tier_b_does_not_fire_when_the_sentence_carries_a_figure(self):
        """'substantially' next to 6.1 -> 4.2 days is an adverb on a measurement."""
        found = audit_text(
            "Lead time improved substantially, from 6.1 days to 4.2 days [F-SYN-002].",
            {"F-SYN-002": {"state": "SUPPORTED"}})
        self.assertEqual(codes(found), set(), [f.message for f in found])

    def test_tier_b_fires_when_the_sentence_has_no_figure(self):
        found = audit_text("Lead time improved substantially [F-SYN-002].",
                           {"F-SYN-002": {"state": "SUPPORTED"}})
        self.assertIn("PROMOTIONAL_LANGUAGE", codes(found))

    def test_tier_c_does_not_fire_when_a_citation_is_present_with_a_figure(self):
        found = audit_text("The control ensures 9 of 9 services are covered [F-SYN-004].",
                           {"F-SYN-004": {"state": "PARTIAL"}})
        self.assertNotIn("PROMOTIONAL_LANGUAGE", codes(found))

    def test_comparative_with_a_number_is_not_flagged(self):
        found = audit_text("Deployment is 1.9 days faster [F-SYN-002].",
                           {"F-SYN-002": {"state": "SUPPORTED"}})
        self.assertEqual(codes(found), set())


class TestRegisterAwareRules(unittest.TestCase):
    REG = {
        "F-U": {"state": "UNKNOWN"},
        "F-C": {"state": "CONTRADICTED"},
        "F-S": {"state": "SUPPORTED"},
    }

    def test_number_against_an_unknown_finding_is_caught(self):
        """The citation resolves perfectly and still cannot support the number."""
        found = audit_text("Restoration completes in under 4 hours [F-U].", self.REG)
        self.assertIn("UNKNOWN_PRESENTED_AS_FINDING", codes(found))

    def test_citing_an_unknown_finding_without_a_number_is_fine(self):
        found = audit_text("Restoration time is not established [F-U].", self.REG)
        self.assertNotIn("UNKNOWN_PRESENTED_AS_FINDING", codes(found))

    def test_contradicted_finding_framed_as_support_is_caught(self):
        found = audit_text("Coverage is complete, as the evidence demonstrates [F-C].",
                           self.REG)
        self.assertIn("CONTRADICTED_FINDING_CITED_AS_SUPPORT", codes(found))

    def test_contradicted_finding_cited_as_a_caveat_is_not_caught(self):
        found = audit_text("The supplied inventory contradicts that position [F-C].",
                           self.REG)
        self.assertNotIn("CONTRADICTED_FINDING_CITED_AS_SUPPORT", codes(found))

    def test_dangling_citation_is_caught(self):
        found = audit_text("Coverage is recorded [F-NOPE].", self.REG)
        self.assertIn("DANGLING_CITATION", codes(found))

    def test_register_must_be_marked_synthetic(self):
        path = os.path.join(tempfile.mkdtemp(), "r.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"findings": []}, fh)
        with self.assertRaises(ValueError):
            ca.load_register(path)


class TestFalsePositives(unittest.TestCase):
    def test_absolute_does_not_match_inside_another_word(self):
        found = audit_text("This was a small change to the wall panel.")
        self.assertEqual(codes(found), set(), [f.message for f in found])

    def test_code_fences_are_not_audited(self):
        text = "```\nworld-class turnkey seamless 42\n```\nOrdinary line.\n"
        self.assertEqual(codes(audit_text(text)), set())

    def test_headings_are_not_audited(self):
        self.assertEqual(codes(audit_text("## Comprehensive robust overview\n")), set())

    def test_table_rule_rows_are_not_audited(self):
        self.assertEqual(codes(audit_text("|---|---|\n")), set())

    def test_markdown_links_are_not_read_as_citations(self):
        """[TEXT-LIKE](url) is a link, not a citation, and must not resolve."""
        found = audit_text("See [F-SYN-001](https://example.invalid/x) for 5 details.",
                           {"F-SYN-001": {"state": "SUPPORTED"}})
        self.assertIn("UNSOURCED_CLAIM", codes(found))
        self.assertNotIn("DANGLING_CITATION", codes(found))


class TestSuppression(unittest.TestCase):
    def test_a_reasoned_suppression_silences_language_rules(self):
        found = audit_text(
            "The rollout is seamless. <!-- audit-ok: quoting the vendor's own "
            "wording verbatim in an appendix -->")
        self.assertEqual(codes(found), set())

    def test_a_bare_suppression_is_itself_a_finding(self):
        found = audit_text("The rollout is seamless. <!-- audit-ok: -->")
        self.assertIn("EMPTY_SUPPRESSION", codes(found))

    def test_suppression_does_not_silence_a_dangling_citation(self):
        """You may overrule a style judgement. You may not overrule a fact."""
        found = audit_text(
            "Coverage is recorded [F-NOPE]. <!-- audit-ok: wording agreed with the "
            "reviewer during the walkthrough -->", {"F-S": {"state": "SUPPORTED"}})
        self.assertIn("DANGLING_CITATION", codes(found))


class TestCliAndDeterminism(unittest.TestCase):
    def test_cli_fails_the_bad_draft_and_passes_the_good_one(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ca.main(["--doc", BAD, "--register", REGISTER]), 1)
            self.assertEqual(ca.main(["--doc", GOOD, "--register", REGISTER]), 0)

    def test_cli_reports_a_missing_register_rather_than_crashing(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = ca.main(["--doc", GOOD, "--register", os.path.join(FIX, "nope.json")])
        self.assertEqual(code, 2)
        self.assertIn("could not load register", err.getvalue())

    def test_language_only_mode_skips_register_rules(self):
        found, _ = ca.audit_document(BAD, None, ca.LANGUAGE_RULES)
        self.assertNotIn("UNSOURCED_CLAIM", codes(found))
        self.assertIn("PROMOTIONAL_LANGUAGE", codes(found))

    def test_two_runs_are_byte_identical(self):
        a = io.StringIO()
        b = io.StringIO()
        with contextlib.redirect_stdout(a):
            ca.main(["--doc", BAD, "--register", REGISTER, "--format", "json"])
        with contextlib.redirect_stdout(b):
            ca.main(["--doc", BAD, "--register", REGISTER, "--format", "json"])
        self.assertEqual(a.getvalue(), b.getvalue())

    def test_corpus_sweep_reports_counts_and_survives_a_bad_file(self):
        root = tempfile.mkdtemp()
        with open(os.path.join(root, "a.md"), "w", encoding="utf-8") as fh:
            fh.write("The rollout is seamless and world-class.\n")
        with open(os.path.join(root, "b.md"), "wb") as fh:
            fh.write(b"\xff\xfe not valid utf-8 \xff")
        payload = ca.scan_corpus(root, ca.LANGUAGE_RULES)
        self.assertEqual(payload["files_scanned"], 1)
        self.assertGreaterEqual(payload["findings_by_rule"]["PROMOTIONAL_LANGUAGE"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
