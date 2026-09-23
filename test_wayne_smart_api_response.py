"""Expose the synthetic SMART API acceptance suite to root unittest discovery."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
import uuid


ROOT = Path(__file__).resolve().parent
NESTED_TEST = ROOT / "revenue" / "wayne_resa_smart_api" / "test_acceptance_lab.py"


def _load_nested_tests(loader: unittest.TestLoader) -> unittest.TestSuite:
    module_name = f"_wayne_smart_api_acceptance_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, NESTED_TEST)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load acceptance tests from {NESTED_TEST}")
    module = importlib.util.module_from_spec(spec)
    original_path = sys.path[:]
    original_modules = sys.modules.copy()
    try:
        # Registration supports import-time helpers such as dataclasses without
        # leaving the uniquely named test module in the process-wide registry.
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        suite = loader.loadTestsFromModule(module)
    finally:
        path_changed = sys.path != original_path
        sys.path[:] = original_path
        for name, imported in tuple(sys.modules.items()):
            source = getattr(imported, "__file__", None)
            is_nested = isinstance(source, str) and Path(source).resolve().is_relative_to(NESTED_TEST.parent)
            if name == module_name or is_nested:
                if name in original_modules:
                    sys.modules[name] = original_modules[name]
                else:
                    sys.modules.pop(name, None)
        if path_changed:
            raise AssertionError("Loading the nested acceptance suite changed sys.path")
    return suite


class OptimizedAcceptanceSuiteTest(unittest.TestCase):
    def test_nested_suite_runs_under_optimized_python(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", "-O", str(NESTED_TEST)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        self.assertRegex(output, r"Ran [1-9]\d* tests?\b", output)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    # Only the nested file is executed by the subprocess above; it cannot
    # rediscover this root bridge and recursively spawn optimized test runs.
    tests.addTests(_load_nested_tests(loader))
    return tests


if __name__ == "__main__":
    unittest.main()
