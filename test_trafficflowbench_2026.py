from __future__ import annotations

"""Retained Commons battery bridge for the TrafficFlowBench nested suite.

The shared Commons battery discovers root ``test_*.py`` files but not arbitrary
``tests/`` modules. Load the exact nested suite by path so the repository test
is both retained and independent of ambient ``tests`` packages on sys.path.
"""

import importlib.util
from pathlib import Path
import unittest

_TEST_PATH = Path(__file__).resolve().parent / "tests" / "test_trafficflowbench_2026.py"
_SPEC = importlib.util.spec_from_file_location("_trafficflowbench_2026_nested_tests", _TEST_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load retained TrafficFlowBench suite: {_TEST_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


if __name__ == "__main__":
    unittest.main(module=_MODULE)
