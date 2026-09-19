"""Root-discovery bridge for the existing UIOWA-032 component suite.

Child processes isolate generic module names from other repository components.
The child transcript preserves optional PDF skips rather than calling them passes.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

LANE = Path(__file__).resolve().parent / "revenue" / "uiowa_rfq_18649_document_extraction"


class UIOWA032SourceCustodyTests(unittest.TestCase):
    def test_component_normal_and_optimized(self):
        for flags in ([], ["-O"]):
            with self.subTest(flags=flags):
                command = [sys.executable, *flags, "-m", "unittest", "-v",
                           "test_extract", "test_integrity", "test_fixture_integrity"]
                result = subprocess.run(command, cwd=LANE, capture_output=True,
                                        text=True, encoding="utf-8", timeout=90)
                transcript = result.stdout + result.stderr
                print("UIOWA-032 mode=" + ("optimized" if flags else "normal"))
                print(transcript)
                self.assertEqual(result.returncode, 0, transcript)
                self.assertIn("Ran 46 tests", transcript)


if __name__ == "__main__":
    unittest.main()
