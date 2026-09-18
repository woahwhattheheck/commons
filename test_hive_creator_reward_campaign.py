"""Retained-battery bridge for the HIVE creator-reward campaign desk.

Commons' retained `tests` workflow discovers root `test_*.py`. The product directory uses a
hyphenated path and intentionally keeps its historical standalone module names, so this bridge
loads that exact suite with the product directory temporarily first on sys.path and re-exports the
patched unittest classes for ordinary root-file discovery. A separate root test executes the same
successor suite under `python -O`, so optimized-mode predecessor coverage remains part of the
retained battery without consuming another active workflow slot.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest


PRODUCT = Path(__file__).resolve().parent / "revenue" / "hive" / "creator-reward-campaign"
if not PRODUCT.is_dir():
    raise RuntimeError(f"missing HIVE creator-reward product directory: {PRODUCT}")

sys.path.insert(0, str(PRODUCT))
try:
    import test_desk as _nested
finally:
    try:
        sys.path.remove(str(PRODUCT))
    except ValueError:
        pass

DeskTests = _nested.DeskTests
HttpTests = _nested.HttpTests


class OptimizedModeTests(unittest.TestCase):
    def test_full_successor_suite_under_python_optimized(self):
        completed = subprocess.run(
            [
                sys.executable,
                '-O',
                '-W',
                'error::ResourceWarning',
                str(PRODUCT / 'test_desk.py'),
            ],
            cwd=PRODUCT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=90,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)


if __name__ == "__main__":
    unittest.main()
