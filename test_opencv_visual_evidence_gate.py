from __future__ import annotations
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent
NESTED = ROOT / "competitions/opencv-ai-2026/visual-evidence-gate/tests/test_visual_gate.py"


def _deps_available() -> bool:
    return importlib.util.find_spec("cv2") is not None and importlib.util.find_spec("numpy") is not None


def _nested_suite():
    if not _deps_available():
        return unittest.TestSuite([unittest.FunctionTestCase(lambda: None, description="OpenCV dependency absent: dedicated workflow owns execution")])
    spec = importlib.util.spec_from_file_location("opencv_visual_gate_tests", NESTED)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError("nested test loader unavailable")
    spec.loader.exec_module(module)
    return unittest.defaultTestLoader.loadTestsFromModule(module)


class OptimizedModeProof(unittest.TestCase):
    def test_nested_suite_under_python_optimized(self):
        if not _deps_available():
            self.skipTest("OpenCV dependency absent; dedicated workflow installs pinned test runtime")
        run = subprocess.run([sys.executable, "-O", str(NESTED)], cwd=str(NESTED.parent), capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    suite.addTests(_nested_suite())
    suite.addTests(loader.loadTestsFromTestCase(OptimizedModeProof))
    return suite


if __name__ == "__main__":
    unittest.main()
