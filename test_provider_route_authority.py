#!/usr/bin/env python3
"""Retained Commons battery bridge for provider-route authority tests."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent
NESTED = (
    ROOT / "tests" / "test_provider_route_authority.py",
    ROOT / "tests" / "test_provider_route_authority_races.py",
)


def _run(path: Path, *, optimized: bool) -> subprocess.CompletedProcess[str]:
    argv = [sys.executable]
    if optimized:
        argv.append("-O")
    argv.append(str(path))
    return subprocess.run(
        argv,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


class RetainedProviderRouteAuthorityTests(unittest.TestCase):
    def _assert_nested(self, *, optimized: bool) -> None:
        for path in NESTED:
            with self.subTest(path=path.relative_to(ROOT).as_posix(), optimized=optimized):
                self.assertTrue(path.is_file(), f"missing retained nested suite: {path}")
                result = _run(path, optimized=optimized)
                self.assertEqual(
                    result.returncode,
                    0,
                    f"nested suite failed ({'python -O' if optimized else 'python'}): {path}\n{result.stdout}",
                )

    def test_nested_suites_normal(self) -> None:
        self._assert_nested(optimized=False)

    def test_nested_suites_optimized(self) -> None:
        self._assert_nested(optimized=True)


if __name__ == "__main__":
    unittest.main()
