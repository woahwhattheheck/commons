#!/usr/bin/env python3
"""Forbidden-output and prompt-injection language guards."""

from __future__ import annotations

import unittest

from charttrace.fixtures.oracle import FORBIDDEN_CLAIMS, INJECTION_TEXT


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


if __name__ == "__main__":
    unittest.main()
