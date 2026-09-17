"""Retained-battery bridge for the GGUF $12k enterprise close/delivery kit.

Commons' retained `tests` workflow discovers root `test_*.py` files.  The GGUF
close kit keeps its hostile suites under `tests/`, so this bridge re-exports both
suites for ordinary root discovery and explicitly reruns the same suites under
`python -O`.  This preserves the exact source/privacy regression coverage
without consuming a dedicated active Actions workflow slot.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent
TESTS = ROOT / "tests"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load GGUF retained suite: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_core = _load("gguf_enterprise_close_kit_retained", TESTS / "test_gguf_enterprise_close_kit.py")
_confusables = _load(
    "gguf_enterprise_close_kit_confusables_retained",
    TESTS / "test_gguf_enterprise_close_kit_script_confusables.py",
)

GgufEnterpriseCloseKitTests = _core.GgufEnterpriseCloseKitTests
GgufScriptConfusablePrivacyTests = _confusables.GgufScriptConfusablePrivacyTests


class OptimizedModeTests(unittest.TestCase):
    def test_full_close_kit_suite_under_python_optimized(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "tests.test_gguf_enterprise_close_kit",
                "tests.test_gguf_enterprise_close_kit_script_confusables",
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=90,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)


if __name__ == "__main__":
    unittest.main()
