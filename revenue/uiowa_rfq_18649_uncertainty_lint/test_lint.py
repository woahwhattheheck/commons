"""Tests for the uncertainty-language lint. Stdlib unittest, no network.

    python3 -m unittest -v test_lint.py

The important test here is `test_precision_meets_the_declared_floor`. A lint
whose precision is not measured drifts into noise, gets switched off, and then
stops catching the thing it was built for. This suite makes the precision claim
in the README a condition of the build rather than a sentence in it.

Everything runs against the frozen `fixtures/labelled_lines.json`, never
against the live repository: the live corpus changes every time a seat lands,
so a test bound to it would be non-hermetic and would start failing for reasons
that have nothing to do with this code.
"""

import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lint  # noqa: E402

LABELS = os.path.join(HERE, "fixtures", "labelled_lines.json")

# Declared in the README. If a change drops below these, the README is wrong
# and the build says so.
PRECISION_FLOOR = 0.90
RECALL_FLOOR = 0.80


class LabelledSetTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data = lint.load_labelled(LABELS)
        cls.score = lint.score_against_labels(cls.data)

    def test_precision_meets_the_declared_floor(self):
        self.assertGreaterEqual(
            self.score["precision"], PRECISION_FLOOR,
            "precision fell to %.2f; false positives: %s"
            % (self.score["precision"],
               [t for k, t in self.score["errors"] if k == "false_positive"]))

    def test_recall_meets_the_declared_floor(self):
        self.assertGreaterEqual(
            self.score["recall"], RECALL_FLOOR,
            "recall fell to %.2f; missed: %s"
            % (self.score["recall"],
               [t for k, t in self.score["errors"] if k == "false_negative"]))

    def test_corpus_lines_are_scored_separately_from_constructed(self):
        # Constructed positives must not be able to flatter the corpus result.
        origins = {row["origin"] for row in self.data["lines"]}
        self.assertEqual(origins, {"corpus", "constructed"})
        for origin in origins:
            subset = {"lines": [r for r in self.data["lines"]
                                if r["origin"] == origin]}
            self.assertTrue(subset["lines"])
            lint.score_against_labels(subset)

    def test_every_labelled_line_records_why(self):
        for row in self.data["lines"]:
            self.assertTrue(row.get("why", "").strip(),
                            "%s has no labelling rationale" % row["id"])
            self.assertIn(row["label"], ("TRUE_POSITIVE", "FALSE_POSITIVE"))

    def test_corpus_lines_name_a_real_source(self):
        for row in self.data["lines"]:
            if row["origin"] != "corpus":
                continue
            self.assertRegex(row["source"], r"^uiowa_rfq_18649_[\w/.-]+:\d+$")

    def test_the_labelled_set_contains_both_labels(self):
        labels = {row["label"] for row in self.data["lines"]}
        self.assertEqual(labels, {"TRUE_POSITIVE", "FALSE_POSITIVE"})


class ClassificationTests(unittest.TestCase):
    """The specific distinctions, asserted one at a time."""

    def _classes(self, text):
        return [f.klass for f in lint.scan_text(text)]

    def test_absence_about_a_service_id_is_flagged(self):
        self.assertIn(lint.FLAG_ASSESSED_ENTITY,
                      self._classes("SVC-PAYROLL has no rollback procedure."))

    def test_the_evidence_scoped_rewrite_is_not_flagged(self):
        self.assertNotIn(
            lint.FLAG_ASSESSED_ENTITY,
            self._classes("We found no rollback procedure for SVC-PAYROLL "
                          "in the 12 runbooks supplied."))

    def test_software_subject_is_not_an_assessment_claim(self):
        self.assertNotIn(
            lint.FLAG_ASSESSED_ENTITY,
            self._classes("The endpoint has no authentication header."))

    def test_hedged_statement_is_not_flagged(self):
        self.assertNotIn(
            lint.FLAG_ASSESSED_ENTITY,
            self._classes("If ESS has no review practice the finding changes."))

    def test_quoting_the_forbidden_form_is_not_committing_it(self):
        self.assertNotIn(
            lint.FLAG_ASSESSED_ENTITY,
            self._classes('The rule forbids writing "ESS has no review '
                          'practice" in a findings table.'))

    def test_row_identifier_is_not_read_as_a_subject(self):
        # The regression for the defect that put precision at 0.29: a hyphen
        # is a word boundary, so `\bIAM\b` matched inside `IAM-OPS-002` and a
        # table row identifier became the subject of a predicate three cells
        # away.
        row = ("| IAM-OPS-002 | operations | GAP | A written rollback "
               "procedure has no demonstrated execution. |")
        self.assertNotIn(lint.FLAG_ASSESSED_ENTITY, self._classes(row))

    def test_subject_is_scoped_to_its_own_table_cell(self):
        row = ("| RIS-AI-002 | AI readiness | GAP | The template lacks a "
               "retirement criterion. |")
        self.assertNotIn(lint.FLAG_ASSESSED_ENTITY, self._classes(row))

    def test_proper_noun_entity_name_is_caught(self):
        self.assertIn(
            lint.FLAG_ASSESSED_ENTITY,
            self._classes("Directory Synchronization Service has no backup "
                          "record."))

    def test_lowercase_the_named_service_is_caught(self):
        # Was missed until the labelled set caught it: the phrase pattern was
        # case-sensitive, so a sentence starting "The identity service..."
        # sailed through.
        self.assertIn(
            lint.FLAG_ASSESSED_ENTITY,
            self._classes("The identity service lacks an escalation path."))

    def test_code_fences_are_skipped(self):
        text = "```\nSVC-PAYROLL has no rollback procedure.\n```\n"
        self.assertEqual(lint.scan_text(text), [])

    def test_existential_phrasing_is_not_a_candidate(self):
        # Documented limitation, asserted so it cannot be reintroduced by
        # accident without someone updating this test and the README.
        self.assertEqual(
            lint.scan_text("There is no incident review practice at ESS."), [])

    def test_default_is_to_pass_when_no_subject_is_found(self):
        findings = lint.scan_text("Nothing here has no clear subject at all.")
        self.assertTrue(findings)
        self.assertNotIn(lint.FLAG_ASSESSED_ENTITY,
                         [f.klass for f in findings])


class ReportingTests(unittest.TestCase):

    def test_flag_carries_a_suggested_rewrite(self):
        findings = lint.scan_text("SVC-PAYROLL has no rollback procedure.")
        flagged = [f for f in findings
                   if f.klass == lint.FLAG_ASSESSED_ENTITY]
        self.assertTrue(flagged)
        self.assertTrue(flagged[0].as_dict()["suggestion"])

    def test_passing_lines_carry_no_suggestion(self):
        findings = lint.scan_text("The endpoint has no auth header.")
        for f in findings:
            self.assertIsNone(f.as_dict()["suggestion"])

    def test_no_score_rating_or_ranking_field_is_emitted(self):
        # The tool must not become the thing it exists to prevent. No output
        # field may carry a score, a rating, a percentile or a per-author
        # ranking.
        findings = lint.scan_text("SVC-PAYROLL has no rollback procedure.")
        payload = json.dumps([f.as_dict() for f in findings]).lower()
        for banned in ("score", "rating", "percentile", "rank", "grade",
                       "author", "seat"):
            self.assertNotIn('"%s"' % banned, payload)

    def test_summary_counts_reconcile(self):
        text = ("SVC-PAYROLL has no rollback procedure.\n"
                "The endpoint has no auth header.\n"
                "If ESS has no practice the finding changes.\n")
        findings = lint.scan_text(text)
        summary = lint.summarise(findings)
        self.assertEqual(summary["candidates_examined"], len(findings))
        self.assertEqual(sum(summary["by_class"].values()), len(findings))

    def test_scan_is_deterministic(self):
        with open(LABELS, encoding="utf-8") as handle:
            text = handle.read()
        first = [f.as_dict() for f in lint.scan_text(text)]
        for _ in range(3):
            self.assertEqual([f.as_dict() for f in lint.scan_text(text)],
                             first)


class MalformedInputTests(unittest.TestCase):

    def test_empty_and_whitespace_text(self):
        for junk in ("", "\n\n", "   ", "```\n```"):
            self.assertEqual(lint.scan_text(junk), [])

    def test_unterminated_code_fence_does_not_crash(self):
        self.assertEqual(lint.scan_text("```\nSVC-X has no thing.\n"), [])

    def test_missing_directory_yields_no_findings(self):
        self.assertEqual(lint.scan_tree(os.path.join(HERE, "nope")), [])

    def test_unterminated_quote_does_not_crash(self):
        findings = lint.scan_text('He said "SVC-PAYROLL has no procedure.')
        self.assertTrue(findings)

    def test_table_row_with_no_closing_pipe(self):
        findings = lint.scan_text("| SVC-PAYROLL | has no rollback procedure")
        self.assertTrue(findings)


class CommandLineTests(unittest.TestCase):

    def _run(self, *args):
        return subprocess.run([sys.executable, os.path.join(HERE, "cli.py")]
                              + list(args), capture_output=True, text=True,
                              cwd=HERE)

    def test_score_command_reports_both_origins(self):
        proc = self._run("score")
        self.assertIn("corpus", proc.stdout)
        self.assertIn("constructed", proc.stdout)
        self.assertIn("precision", proc.stdout)

    def test_explain_lists_every_class(self):
        proc = self._run("explain")
        self.assertEqual(proc.returncode, 0)
        for klass in (lint.FLAG_ASSESSED_ENTITY, lint.OK_HEDGED,
                      lint.OK_QUOTED, lint.OK_TOOL_SUBJECT,
                      lint.OK_EVIDENCE_SUBJECT, lint.OK_UNCLASSIFIED):
            self.assertIn(klass, proc.stdout)

    def test_scan_on_a_clean_tree_exits_zero(self):
        proc = self._run("scan", os.path.join(HERE, "fixtures"))
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_clean_scan_refuses_to_claim_a_clean_bill_of_health(self):
        proc = self._run("scan", os.path.join(HERE, "fixtures"))
        self.assertIn("not a clean bill of health", proc.stdout)

    def test_scan_json_is_machine_readable(self):
        proc = self._run("scan", os.path.join(HERE, "fixtures"), "--json")
        payload = json.loads(proc.stdout)
        self.assertIn("summary", payload)
        self.assertIn("candidates_examined", payload["summary"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
