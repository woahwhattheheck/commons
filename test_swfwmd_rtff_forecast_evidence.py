"""Root CI bridge for the SWFWMD RTFF forecast-evidence hostile suite."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

SUITE_DIR = Path(__file__).resolve().parent / "revenue" / "swfwmd_rtff_forecast_evidence"
SUITE_FILE = SUITE_DIR / "tests" / "test_evidence.py"
if str(SUITE_DIR) not in sys.path:
    sys.path.insert(0, str(SUITE_DIR))
_SPEC = importlib.util.spec_from_file_location("swfwmd_rtff_forecast_evidence_suite", SUITE_FILE)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load evidence suite: {SUITE_FILE}")
_SUITE_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_SUITE_MODULE)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return loader.loadTestsFromModule(_SUITE_MODULE)


if __name__ == "__main__":
    unittest.main()
