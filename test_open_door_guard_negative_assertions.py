#!/usr/bin/env python3
"""Wire the source-bound negative-assertion bank into ordinary test discovery."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parent
BANK = (
    ROOT
    / "builds"
    / "records"
    / "open-door-negative-assertions"
    / "test_open_door_guard_negative_assertions.py"
)


def _load_bank():
    spec = importlib.util.spec_from_file_location(
        "open_door_negative_assertion_bank", BANK
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load focused guard bank: {BANK}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.ScopeTests.guard = module.load_guard(ROOT / "open_door_guard.py")
    return module


BANK_MODULE = _load_bank()


def load_tests(loader, tests, pattern):
    """Expose the exact focused case class without copying its test bodies."""
    return loader.loadTestsFromTestCase(BANK_MODULE.ScopeTests)


if __name__ == "__main__":
    unittest.main()
