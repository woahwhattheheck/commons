#!/usr/bin/env python3
"""Forbidden-output and prompt-injection language guards."""

from __future__ import annotations

import unittest

from charttrace.assurance.oracle_run import language_violations
from charttrace.fixtures.oracle import FORBIDDEN_CLAIMS, PROMPT_INJECTION


class ChartTraceLanguageTests(unittest.TestCase):
    def test_clean_packet_language(self) -> None:
        text = (
            "No documentation of communication was located in the supplied cardiology "
            "notes for 2023-03-01-2023-08-27. This does not establish that no "
            "communication occurred."
        )
        self.assertEqual(language_violations(text), [])

    def test_unbounded_absence_is_rejected(self) -> None:
        self.assertIn(
            "the patient was not told",
            [c.lower() for c in FORBIDDEN_CLAIMS]
            + [x.lower() for x in language_violations("the patient was not told")],
        )
        hits = language_violations("This proves malpractice and the patient was not told.")
        self.assertTrue(hits)

    def test_injection_string_is_fixture_only(self) -> None:
        self.assertIn("IGNORE ALL PRIOR INSTRUCTIONS", PROMPT_INJECTION)
        self.assertEqual(language_violations("released packet with scoped gaps only"), [])


if __name__ == "__main__":
    unittest.main()
