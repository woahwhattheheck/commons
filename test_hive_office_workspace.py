#!/usr/bin/env python3
"""Expose the standalone office workspace's real tests to the root battery."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).parent / "revenue/hive/office-workspace/test_app.py"
spec = importlib.util.spec_from_file_location("hive_office_workspace_tests", path)
tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tests)


def load_tests(loader, standard_tests, pattern):
    return loader.loadTestsFromModule(tests)


if __name__ == "__main__":
    unittest.main(verbosity=2)
