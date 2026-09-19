"""Tests for UIOWA-081: evidence lattice, findings store, summary compiler, renderers.

Run:  python3 -m unittest -v test_exec_summary

The assertions that matter are the ones about what CANNOT happen: an unsourced
sentence cannot reach the document, a citation cannot carry more weight than its
evidence, an unknown scope cannot become a universal claim, and a malformed finding
cannot become citable by being quietly repaired.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import evidence
import render
from findings import Finding, FindingsStore, EvidenceItem, finding_from_dict, load_findings
from summary import (
    Statement,
    check_statement,
    claimed_strength,
    claims_universal_scope,
    compile_summary,
    load_document,
)

FINDINGS_PATH = os.path.join(HERE, "data", "findings.json")
DRAFT_PATH = os.path.join(HERE, "data", "draft_statements.json")


def make_finding(finding_id="F-X", basis="DOCUMENT_REVIEW", confidence="HIGH",
                 corroborating=3, evidence_count=2, established=5, in_scope=5,
                 severity="MINOR", observed="A plain observed fact.", unresolved=()):
    items = tuple(EvidenceItem(f"E-{finding_id}-{n}", "document", f"locator {n}",
                               "2026-08-01") for n in range(evidence_count))
    return Finding(finding_id=finding_id, area="Area", title="Title",
                   observed=observed, basis=basis, confidence=confidence,
                   corroborating_sources=corroborating, severity=severity,
                   units_established=established, units_in_scope=in_scope,
                   evidence=items, unresolved=tuple(unresolved))


# --------------------------------------------------------- the evidence lattice

class TestEvidenceLattice(unittest.TestCase):

    def test_corroborated_high_confidence_document_review_is_settled(self):
        self.assertEqual(
            evidence.max_assertable_strength("DOCUMENT_REVIEW", "HIGH", 3, 4),
            "SETTLED")

    def test_unknown_confidence_collapses_to_not_established(self):
        """The core honesty rule: an unknown does not become a weaker yes."""
        self.assertEqual(
            evidence.max_assertable_strength("DIRECT_OBSERVATION", "UNKNOWN", 5, 9),
            "NOT_ESTABLISHED")

    def test_finding_with_no_evidence_attached_is_not_established(self):
        """A basis and a confidence with nothing attached is an assertion."""
        self.assertEqual(
            evidence.max_assertable_strength("DIRECT_OBSERVATION", "HIGH", 5, 0),
            "NOT_ESTABLISHED")

    def test_single_interview_cannot_reach_indicated(self):
        self.assertEqual(
            evidence.max_assertable_strength("INTERVIEW_SINGLE_SOURCE", "HIGH", 4, 3),
            "SINGLE_SOURCE")

    def test_uncorroborated_self_report_is_not_established(self):
        self.assertEqual(
            evidence.max_assertable_strength("SELF_REPORTED", "HIGH", 0, 3),
            "NOT_ESTABLISHED")

    def test_missing_confidence_raises_and_says_to_record_unknown(self):
        with self.assertRaises(evidence.EvidenceError) as caught:
            evidence.max_assertable_strength("DOCUMENT_REVIEW", None, 2, 2)
        self.assertIn("UNKNOWN", str(caught.exception))

    def test_unknown_basis_raises(self):
        with self.assertRaises(evidence.EvidenceError):
            evidence.max_assertable_strength("VIBES", "HIGH", 2, 2)

    def test_weakest_citation_caps_the_pair(self):
        self.assertEqual(evidence.at_most("SETTLED", "SINGLE_SOURCE"), "SINGLE_SOURCE")
        self.assertEqual(evidence.at_most("INDICATED", "SETTLED"), "INDICATED")


# ------------------------------------------------------------- findings store

class TestFindingsStore(unittest.TestCase):

    def test_malformed_finding_is_rejected_at_load_and_named(self):
        store, rejected, _raw = load_findings(FINDINGS_PATH)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0]["raw_id"], "F-007-MALFORMED")
        self.assertIn("severity", rejected[0]["error"])
        self.assertNotIn("F-007-MALFORMED", store)

    def test_rejected_finding_cannot_be_cited(self):
        """Hostile: a repaired finding would become citable. It must not exist."""
        store, _rejected, _raw = load_findings(FINDINGS_PATH)
        ok, problems = check_statement(
            Statement("S-H", "Something is true.", ("F-007-MALFORMED",)), store)
        self.assertFalse(ok)
        self.assertEqual(problems[0]["code"], "UNKNOWN_FINDING")

    def test_missing_required_field_raises_rather_than_defaulting(self):
        with self.assertRaises(Exception) as caught:
            finding_from_dict({"finding_id": "F-Z", "area": "A", "title": "T",
                               "observed": "O", "basis": "DOCUMENT_REVIEW",
                               "severity": "MINOR", "corroborating_sources": 2,
                               "units_established": 1, "units_in_scope": 2})
        self.assertIn("confidence", str(caught.exception))

    def test_unknown_scope_is_never_universal(self):
        """'We did not count' must not read as 'we counted all of them'."""
        finding = make_finding(established="UNKNOWN", in_scope=5)
        self.assertFalse(finding.scope_is_universal)
        self.assertIn("UNKNOWN", finding.scope_label)

    def test_duplicate_finding_ids_are_refused(self):
        with self.assertRaises(evidence.EvidenceError):
            FindingsStore([make_finding("F-D"), make_finding("F-D")])


# -------------------------------------------------- reading strength off text

class TestClaimDetection(unittest.TestCase):

    def test_bare_assertion_reads_as_settled(self):
        self.assertEqual(claimed_strength("Records are retained everywhere."),
                         "SETTLED")

    def test_hedged_assertion_reads_as_indicated(self):
        self.assertEqual(
            claimed_strength("Evidence indicates that triage is same-day."),
            "INDICATED")

    def test_attributed_assertion_reads_as_single_source(self):
        self.assertEqual(
            claimed_strength("One unit reported that ownership is documented."),
            "SINGLE_SOURCE")

    def test_universal_markers_are_detected(self):
        self.assertTrue(claims_universal_scope("This holds across the institution."))
        self.assertTrue(claims_universal_scope("All units do this."))
        self.assertFalse(claims_universal_scope("Two of five units do this."))


# ----------------------------------------------------------- the seven checks

class TestStatementChecks(unittest.TestCase):

    def setUp(self):
        self.store = FindingsStore([
            make_finding("F-S", basis="DOCUMENT_REVIEW", confidence="HIGH",
                         corroborating=3, evidence_count=3, established=5, in_scope=5,
                         observed="Covers 31% of datasets in all 5 units."),
            make_finding("F-W", basis="INTERVIEW_SINGLE_SOURCE", confidence="MODERATE",
                         corroborating=1, evidence_count=1, established=1, in_scope=5),
            make_finding("F-N", basis="NOT_ESTABLISHED", confidence="UNKNOWN",
                         corroborating=0, evidence_count=0, established="UNKNOWN",
                         in_scope=5, severity="CRITICAL"),
            make_finding("F-P", basis="INTERVIEW_CORROBORATED", confidence="MODERATE",
                         corroborating=2, evidence_count=2, established=2, in_scope=5),
        ])

    def _check(self, text, cites):
        return check_statement(Statement("S-T", text, tuple(cites)), self.store)

    def _codes(self, text, cites):
        _ok, problems = self._check(text, cites)
        return [problem["code"] for problem in problems]

    def test_clean_statement_passes(self):
        ok, problems = self._check(
            "Coverage reaches 31% of datasets across all units.", ["F-S"])
        self.assertTrue(ok, problems)

    def test_no_citation_is_refused(self):
        self.assertEqual(self._codes("Overall the outlook is good.", []),
                         ["NO_CITATION"])

    def test_unknown_finding_is_refused(self):
        self.assertEqual(self._codes("Something holds.", ["F-999"]),
                         ["UNKNOWN_FINDING"])

    def test_overclaim_is_refused_with_the_specific_remedy(self):
        ok, problems = self._check("Ownership is documented.", ["F-W"])
        self.assertFalse(ok)
        self.assertEqual(problems[0]["code"], "OVERCLAIM")
        self.assertIn("SINGLE_SOURCE", problems[0]["reason"])
        self.assertIn("attribution", problems[0]["remedy"])

    def test_correctly_attributed_version_of_the_same_claim_passes(self):
        ok, problems = self._check(
            "One unit reported that ownership is documented.", ["F-W"])
        self.assertTrue(ok, problems)

    def test_a_strong_finding_does_not_launder_a_weak_one(self):
        """Citing a settled finding alongside a single-source one caps at the weaker."""
        codes = self._codes("Ownership is documented and records are retained.",
                            ["F-S", "F-W"])
        self.assertIn("OVERCLAIM", codes)

    def test_not_established_finding_cannot_be_asserted_at_all(self):
        ok, problems = self._check("A review path exists.", ["F-N"])
        self.assertFalse(ok)
        self.assertEqual(problems[0]["code"], "ASSERTS_NOT_ESTABLISHED")
        self.assertIn("open-questions", problems[0]["remedy"])

    def test_hedging_does_not_rescue_a_not_established_finding(self):
        """Hostile: an author tries to slip an unestablished finding in by softening."""
        ok, problems = self._check(
            "Evidence indicates that a review path exists.", ["F-N"])
        self.assertFalse(ok)
        self.assertEqual(problems[0]["code"], "ASSERTS_NOT_ESTABLISHED")

    def test_scope_overreach_is_refused(self):
        codes = self._codes(
            "Evidence indicates that all units triage within the day.", ["F-P"])
        self.assertEqual(codes, ["SCOPE_OVERREACH"])

    def test_scoped_version_of_the_same_claim_passes(self):
        ok, problems = self._check(
            "Evidence indicates that in the 2 of 5 units reviewed, triage is same-day.",
            ["F-P"])
        self.assertTrue(ok, problems)

    def test_unsupported_number_is_refused(self):
        codes = self._codes("Coverage reaches 42% of datasets across all units.",
                            ["F-S"])
        self.assertEqual(codes, ["UNSUPPORTED_NUMBER"])

    def test_scope_numbers_count_as_supported(self):
        ok, problems = self._check(
            "Evidence indicates that 2 of 5 units do this.", ["F-P"])
        self.assertTrue(ok, problems)

    def test_individual_attribution_is_refused(self):
        codes = self._codes("Delays trace to individual performance in intake.",
                            ["F-S"])
        self.assertEqual(codes, ["INDIVIDUAL_ATTRIBUTION"])

    def test_unknown_scope_cannot_support_a_universal_claim(self):
        store = FindingsStore([make_finding("F-U", established="UNKNOWN", in_scope=5)])
        _ok, problems = check_statement(
            Statement("S-U", "This holds across the institution.", ("F-U",)), store)
        self.assertIn("SCOPE_OVERREACH", [p["code"] for p in problems])


# ------------------------------------------------------------- full compile

class TestCompile(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.store, cls.rejected_findings, cls.raw = load_findings(FINDINGS_PATH)
        cls.document = load_document(DRAFT_PATH)
        cls.result = compile_summary(cls.document, cls.store)

    def test_every_check_is_exercised_by_the_fixture_draft(self):
        codes = {problem["code"]
                 for item in self.result["rejected"]
                 for problem in item["problems"]}
        self.assertEqual(codes, {"NO_CITATION", "UNKNOWN_FINDING",
                                 "ASSERTS_NOT_ESTABLISHED", "OVERCLAIM",
                                 "SCOPE_OVERREACH", "UNSUPPORTED_NUMBER",
                                 "INDIVIDUAL_ATTRIBUTION"})

    def test_accepted_statements_all_carry_resolvable_citations(self):
        for entry in self.result["accepted"].values():
            self.assertTrue(entry["statement"].cites)
            for finding in entry["findings"]:
                self.assertIn(finding.finding_id, self.store)

    def test_rejected_text_never_reaches_the_rendered_document(self):
        """The document physically cannot contain an unsupported sentence."""
        rendered = render.render_executive_summary(self.result)
        for item in self.result["rejected"]:
            self.assertNotIn(item["text"], rendered)

    def test_every_rendered_statement_carries_its_finding_ids(self):
        """Asserts the property directly rather than pattern-matching bullet lines:
        the open-questions section also uses bullets and a different citation form."""
        rendered = render.render_executive_summary(self.result)
        for statement_id, entry in self.result["accepted"].items():
            line = next((l for l in rendered.splitlines()
                         if entry["statement"].text in l), None)
            self.assertIsNotNone(line, f"{statement_id} missing from the document")
            for finding in entry["findings"]:
                self.assertIn(f"`{finding.finding_id}`", line)
            self.assertRegex(line, r"\[`F-[^`]+`.*\]$")

    def test_coverage_splits_uncited_by_whether_it_was_assertable(self):
        uncited = {f.finding_id: f.max_strength
                   for f in self.result["uncited_findings"]}
        self.assertIn("F-005", uncited)
        self.assertNotEqual(uncited["F-005"], "NOT_ESTABLISHED")
        self.assertIn("F-003", uncited)
        self.assertEqual(uncited["F-003"], "NOT_ESTABLISHED")

    def test_unresolved_items_are_carried_into_the_summary(self):
        rendered = render.render_executive_summary(self.result)
        self.assertIn("Open questions", rendered)
        self.assertIn("UNKNOWN", rendered)
        self.assertGreaterEqual(len(self.result["unresolved"]), 5)

    def test_traceability_matrix_row_findings_are_all_cited_by_their_statement(self):
        rows = render.render_traceability_matrix_csv(self.result).strip().splitlines()
        self.assertTrue(rows[0].startswith("statement_id,"))
        self.assertGreater(len(rows), 1)
        import csv as _csv
        import io as _io
        for row in _csv.DictReader(_io.StringIO(
                render.render_traceability_matrix_csv(self.result))):
            entry = self.result["accepted"][row["statement_id"]]
            self.assertIn(row["finding_id"], entry["statement"].cites)
            self.assertTrue(row["evidence_locator"])

    def test_compile_report_names_every_rejection_with_a_remedy(self):
        report = render.render_compile_report(self.result, self.rejected_findings)
        for item in self.result["rejected"]:
            self.assertIn(item["statement_id"], report)
            for problem in item["problems"]:
                self.assertIn(problem["code"], report)
        self.assertIn("Remedy", report)
        self.assertIn("F-007-MALFORMED", report)

    def test_rendering_is_deterministic(self):
        self.assertEqual(render.render_executive_summary(self.result),
                         render.render_executive_summary(self.result))
        self.assertEqual(render.render_traceability_matrix_csv(self.result),
                         render.render_traceability_matrix_csv(self.result))

    def test_fiction_is_labelled_as_fiction(self):
        self.assertIn("FICTIONAL", self.raw["_fiction_notice"])
        with open(DRAFT_PATH, encoding="utf-8") as handle:
            draft = json.load(handle)
        self.assertIn("FICTIONAL", draft["_fiction_notice"])
        self.assertIn("FICTIONAL", self.result["title"])

    def test_no_statement_is_dropped_without_appearing_in_the_report(self):
        dropped = {sid for section in self.result["sections"]
                   for sid in section["dropped_statement_ids"]}
        reported = {item["statement_id"] for item in self.result["rejected"]}
        self.assertTrue(dropped)
        self.assertTrue(dropped.issubset(reported))


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestRunnerContractAdoption(unittest.TestCase):
    """build_summary.py must signal a dropped serious finding to a runner."""

    def _run(self):
        import subprocess
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "build_summary.py")],
            capture_output=True, text=True, cwd=HERE, timeout=180, check=False)

    def _status(self, text):
        for line in reversed(text.splitlines()):
            if line.startswith("KIT-STATUS:"):
                return dict(token.split("=", 1)
                            for token in line[len("KIT-STATUS:"):].strip().split(" ")
                            if "=" in token)
        return None

    def test_emits_a_status_line_matching_its_exit_code(self):
        completed = self._run()
        status = self._status(completed.stdout)
        self.assertIsNotNone(status, completed.stdout[-500:])
        self.assertEqual(int(status["code"]), completed.returncode)

    def test_dropped_serious_finding_is_reported_as_findings(self):
        completed = self._run()
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(self._status(completed.stdout)["status"], "FINDINGS")

    def test_not_established_findings_are_counted_as_indeterminate(self):
        status = self._status(self._run().stdout)
        self.assertGreater(int(status["indeterminate"]), 0)

    def test_contract_precedence_puts_indeterminate_above_clean(self):
        import kit_status
        self.assertEqual(kit_status.decide(0, 0), kit_status.CLEAN)
        self.assertEqual(kit_status.decide(0, 2), kit_status.INDETERMINATE)
