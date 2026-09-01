"""Tests for export-language lint rules."""

from __future__ import annotations

import unittest

from charttrace.export.language import sanitize_export_text
from charttrace.review.language_lint import (
    lint_lead,
    lint_packet_texts,
    scoped_nonfinding,
)


class LanguageLintTests(unittest.TestCase):
    def test_scoped_nonfinding_shape(self) -> None:
        text = scoped_nonfinding(scope="cardiology notes", date_range="2020-01–2020-03")
        self.assertIn("No documentation of communication was located", text)
        self.assertIn("cardiology notes", text)
        self.assertNotIn("was not told", text.lower())

    def test_forbids_patient_not_told(self) -> None:
        issues = lint_lead(
            {
                "lead_id": "L1",
                "hypothesis": "The patient was not told about the critical result",
            }
        )
        self.assertTrue(issues)
        self.assertTrue(any("not told" in i.phrase for i in issues))

    def test_forbids_legal_conclusion_language(self) -> None:
        for phrase in (
            "malpractice",
            "negligence",
            "causation",
            "standard of care",
            "actionability",
            "case value",
        ):
            issues = lint_lead({"lead_id": "Lx", "title": f"Shows {phrase} clearly"})
            self.assertTrue(issues, phrase)

    def test_sanitize_replaces_forbidden_export_language(self) -> None:
        text, changed = sanitize_export_text("The patient was not told about labs")
        self.assertTrue(changed)
        self.assertNotIn("was not told", text.lower())
        self.assertIn("No documentation of communication was located", text)

        text2, changed2 = sanitize_export_text("Suggests malpractice and case value")
        self.assertTrue(changed2)
        self.assertNotIn("malpractice", text2.lower())
        self.assertNotIn("case value", text2.lower())

    def test_packet_lint_ok_for_clean(self) -> None:
        report = lint_packet_texts(
            [
                {
                    "lead_id": "L1",
                    "hypothesis": "Possible documentation gap in supplied notes",
                }
            ]
        )
        self.assertTrue(report.ok)


if __name__ == "__main__":
    unittest.main()
