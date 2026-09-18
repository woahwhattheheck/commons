#!/usr/bin/env python3
"""Public commons main keeps four LIMS product tips isolated.

Durable canary for digit-lims-isolation-measure-20260902-01.
Does not remint spy-lims-isolated-20260901-01. Does not land product bytes.
"""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent

# Paths named on digit-lims-isolation-measure-20260902-01. Stay off public main.
PRODUCT_PATHS_OFF_PUBLIC = (
    "bevsource-lab-pilot-qa-genealogy-lims.html",
    "bevsource-lab-pilot-qa-genealogy-lims.py",
    "bevsource_lab_pilot_qa_genealogy_lims.py",
    "campoly-sample-report-lineage-lims.html",
    "campoly-sample-report-lineage-lims.py",
    "denton-bacteriology-acceptance-reporting-lims.html",
    "denton-bacteriology-acceptance-reporting-lims.py",
    "denton_bacteriology_acceptance_reporting_lims.py",
    "delaware-newlab-pfas-lineage-lims.html",
    "delaware-newlab-pfas-lineage-lims.py",
    "delaware_newlab_pfas_lineage.py",
)

SPY_ID = "p/spy-lims-isolated-20260901-01.md"
DIGIT_MEASURE = "p/digit-lims-isolation-measure-20260902-01.md"


class LimsIsolationPublicTests(unittest.TestCase):
    def test_four_lims_product_tips_absent_from_public_tree(self) -> None:
        present = [rel for rel in PRODUCT_PATHS_OFF_PUBLIC if (ROOT / rel).exists()]
        self.assertEqual(present, [])

    def test_spy_lims_isolated_not_reminted(self) -> None:
        self.assertFalse((ROOT / SPY_ID).exists())

    def test_digit_measure_receipt_present(self) -> None:
        path = ROOT / DIGIT_MEASURE
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("id: digit-lims-isolation-measure-20260902-01", text)
        self.assertIn("without reminting", text)
        self.assertIn("No remint", text)
        self.assertNotIn("authentication required", text.lower())


if __name__ == "__main__":
    unittest.main()
