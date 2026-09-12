# SPDX-License-Identifier: Apache-2.0
"""Canonical committed-seed-retry hosted test runner.

Keeps the established real-runtime suite byte-for-byte in test_seed_retry_core.py
and explicitly includes the minimum-one executable-prefix predecessor killers.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _suite() -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(
        _load("seed_retry_core_tests", "test_seed_retry_core.py")))
    suite.addTests(loader.loadTestsFromModule(
        _load("seed_retry_minimum_market_limit_tests", "test_minimum_market_limit.py")))
    return suite


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(_suite())
    raise SystemExit(0 if result.wasSuccessful() else 1)
