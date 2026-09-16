"""Root-level CI bridge for the SaaS Migration Parity Pilot hostile suites."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

SUITE_DIR = Path(__file__).resolve().parent / "commercial" / "saas-migration-parity-pilot"
SUITE_FILES = (
    SUITE_DIR / "test_parity.py",
    SUITE_DIR / "test_strict_input_hostiles.py",
)
if str(SUITE_DIR) not in sys.path:
    sys.path.insert(0, str(SUITE_DIR))


def _load_suite_module(path: Path, index: int):
    spec = importlib.util.spec_from_file_location(f"saas_migration_parity_pilot_suite_{index}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load parity suite: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SUITE_MODULES = tuple(_load_suite_module(path, idx) for idx, path in enumerate(SUITE_FILES))


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    combined = unittest.TestSuite()
    for module in _SUITE_MODULES:
        combined.addTests(loader.loadTestsFromModule(module))
    return combined


if __name__ == "__main__":
    unittest.main()
