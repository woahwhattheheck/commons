"""Retain the UIOWA-032 extraction lane in repository-root test discovery."""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

LANE = Path(__file__).resolve().parent / "revenue" / "uiowa_rfq_18649_document_extraction"


class DocumentExtractionLaneTests(unittest.TestCase):
    def _run_lane(self, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command += ["-m", "unittest", "-v", "test_extract.py"]
        result = subprocess.run(
            command,
            cwd=LANE,
            capture_output=True,
            text=True,
            timeout=45,
        )
        self.assertEqual(
            result.returncode,
            0,
            "UIOWA-032 lane regression failed\nSTDOUT:\n"
            + result.stdout
            + "\nSTDERR:\n"
            + result.stderr,
        )
        self.assertIn("test_missing_pdf_backend_fails_closed_with_named_dependency_error", result.stderr)
        self.assertIn("OK", result.stderr)

    def test_lane_normal(self) -> None:
        self._run_lane(optimized=False)

    def test_lane_optimized(self) -> None:
        self._run_lane(optimized=True)


if __name__ == "__main__":
    unittest.main()
