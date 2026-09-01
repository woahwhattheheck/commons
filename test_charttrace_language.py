#!/usr/bin/env python3
"""Forbidden-output and prompt-injection language guards."""

from __future__ import annotations

import unittest

from charttrace.assurance.oracle_run import language_violations
from charttrace.fixtures.oracle import FORBIDDEN_CLAIMS, INJECTION_TEXT, PROMPT_INJECTION


class ChartTraceLanguageTests(unittest.TestCase):
    def test_clean_investigative_language_is_allowed(self) -> None:
        text = (
            "No documentation of communication was located in the supplied "
            "cardiology notes for the interval. This does not establish that "
            "no communication occurred."
        )
        lowered = text.lower()
        for claim in FORBIDDEN_CLAIMS:
            self.assertNotIn(claim, lowered)

    def test_unbounded_absence_tokens_are_listed(self) -> None:
        self.assertIn("patient was not told", FORBIDDEN_CLAIMS)
        self.assertIn("malpractice", FORBIDDEN_CLAIMS)
        self.assertIn("never told", FORBIDDEN_CLAIMS)

    def test_injection_string_is_fixture_only(self) -> None:
        self.assertIn("IGNORE PREVIOUS INSTRUCTIONS", INJECTION_TEXT)
        self.assertIn("DELETE WEAK APPENDIX", INJECTION_TEXT)
        self.assertIn("IGNORE ALL PRIOR INSTRUCTIONS", PROMPT_INJECTION)

    def test_oracle_run_language_violations_alias(self) -> None:
        clean = (
            "No documentation of communication was located in the supplied "
            "cardiology notes for the interval. This does not establish that "
            "no communication occurred."
        )
        self.assertEqual(language_violations(clean), [])
        hits = language_violations("this is malpractice and the patient was not told")
        self.assertTrue(hits)


if __name__ == "__main__":
    unittest.main()
