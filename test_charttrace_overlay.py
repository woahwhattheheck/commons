#!/usr/bin/env python3
"""Keep builder/tags/pdfutil/oracle_run importable beside build_oracle."""

from __future__ import annotations

import pathlib
import tempfile
import unittest

from charttrace.assurance.oracle_run import pass_contract, synthetic_run
from charttrace.fixtures.oracle import (
    CANARY_PHI,
    DOCUMENT_PLAN,
    ORACLE,
    PROMPT_INJECTION,
    STRUCTURAL,
    UNIQUE_DOC_PAGES,
    build_oracle,
    structural_counts,
)


class OverlayCompatTests(unittest.TestCase):
    def test_overlay_names_export_the_locked_counts(self) -> None:
        self.assertEqual(ORACLE["raw_input_files"], 18)
        self.assertEqual(ORACLE["raw_pages"], 280)
        self.assertEqual(ORACLE["unique_documents"], 16)
        self.assertEqual(ORACLE["unique_pages"], 240)
        self.assertEqual(len(UNIQUE_DOC_PAGES), 16)
        self.assertTrue(CANARY_PHI.startswith("CANARY-PHI-TOKEN"))
        self.assertIn("IGNORE ALL PRIOR INSTRUCTIONS", PROMPT_INJECTION)

    def test_builder_and_oracle_run_match_structural_oracle(self) -> None:
        oracle = build_oracle()
        self.assertEqual(structural_counts(oracle), STRUCTURAL)
        self.assertEqual(len(DOCUMENT_PLAN), 18)
        with tempfile.TemporaryDirectory(prefix="charttrace-overlay-") as tmp:
            result = synthetic_run(pathlib.Path(tmp))
        failures = pass_contract(result)
        self.assertEqual(failures, [])
        self.assertEqual(result["inventory"]["raw_input_files"], 18)
        self.assertEqual(result["inventory"]["raw_pages"], 280)


if __name__ == "__main__":
    unittest.main()
