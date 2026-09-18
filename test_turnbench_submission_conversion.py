from __future__ import annotations
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent
NESTED = ROOT / "competitions/assemblyai-voice-agent-2026/turnbench/submission/tests/test_readiness.py"


def _load_nested_suite():
    spec = importlib.util.spec_from_file_location("turnbench_submission_test_readiness", NESTED)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError("test module loader unavailable")
    spec.loader.exec_module(module)
    return unittest.defaultTestLoader.loadTestsFromModule(module)


class OptimizedModeProof(unittest.TestCase):
    def test_nested_suite_under_optimized_python(self):
        run = subprocess.run(
            [sys.executable, "-O", str(NESTED)],
            cwd=str(NESTED.parent),
            capture_output=True,
            text=True,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    suite.addTests(_load_nested_suite())
    suite.addTests(loader.loadTestsFromTestCase(OptimizedModeProof))
    return suite


if __name__ == "__main__":
    unittest.main()
