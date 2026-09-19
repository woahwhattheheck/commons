"""Expose original-evidence intake conformance to the existing root test battery."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


def load_tests(loader, tests, pattern):
    source = (Path(__file__).resolve().parent / "revenue" /
              "uiowa_rfq_18649_workbench" / "test_intake_transport.py")
    spec = importlib.util.spec_from_file_location("_uiowa_original_intake_tests", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Original-evidence intake test suite cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return loader.loadTestsFromModule(module)


if __name__ == "__main__":
    unittest.main()
