#!/usr/bin/env python3
"""Keep the L01 current evidence carrier honest about driver failure.

Run 34403631157 failed correctly, but GitHub displayed the archive-bound
driver step as successful because that step used continue-on-error: true.
Only the later completeness step carried the red status. This contract
locks the carrier so the driver step's real exit status is visible while
summary publication, artifact upload, and completeness still run.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent
WORKFLOW = ROOT / ".github/workflows/titan-v3-land-admission-current.yml"
DRIVER = "Run archive-bound historical and current paired evidence"
SUMMARY = "Publish evidence summary"
UPLOAD = "Upload exact evidence"
COMPLETE = "Enforce complete paired execution"


def step_blocks(text: str) -> dict[str, str]:
    parts = re.split(r"(?m)^      - name: ", text)
    blocks: dict[str, str] = {}
    for part in parts[1:]:
        name, _, rest = part.partition("\n")
        blocks[name.strip()] = rest
    return blocks


class TitanL01CarrierHonestyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.steps = step_blocks(cls.text)

    def test_driver_step_is_present(self) -> None:
        self.assertIn(DRIVER, self.steps)
        self.assertIn("id: holdout\n", self.steps[DRIVER])

    def test_driver_step_does_not_launder_failure(self) -> None:
        body = self.steps[DRIVER]
        self.assertNotIn("continue-on-error", body)

    def test_diagnostics_survive_driver_failure(self) -> None:
        for name in (SUMMARY, UPLOAD, COMPLETE):
            self.assertIn(name, self.steps)
            self.assertIn("if: always()\n", self.steps[name])

    def test_summary_records_exact_driver_outcome_and_head(self) -> None:
        body = self.steps[SUMMARY]
        self.assertIn("### Carrier status", body)
        self.assertIn("Driver outcome:", body)
        self.assertIn("steps.holdout.outcome", body)
        self.assertIn("Triggering head:", body)
        self.assertIn("github.event.pull_request.head.sha || github.sha", body)

    def test_completeness_still_requires_successful_driver(self) -> None:
        body = self.steps[COMPLETE]
        self.assertIn('test "${{ steps.holdout.outcome }}" = "success"', body)
        self.assertIn("CURRENT-DELTA.json", body)
        self.assertIn("EXIT_CODE.txt", body)


if __name__ == "__main__":
    unittest.main()
