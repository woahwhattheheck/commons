#!/usr/bin/env python3
"""Retained root bridge for the canonical outbound route-quarantine suite."""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULE = "tools.outbound_send_guard.test_route_quarantine"
_UNITTEST_TERMINAL = re.compile(
    r"(?m)^Ran\s+(?P<count>\d+)\s+tests?\s+in\s+[^\r\n]+\r?\n"
    r"\r?\nOK(?:\s+\([^\r\n]*\))?\r?\n?\Z"
)


def _reported_test_count(stderr: str) -> int:
    """Return unittest's terminal stderr execution count or fail closed."""
    match = _UNITTEST_TERMINAL.search(stderr)
    if match is None:
        raise ValueError(f"unittest stderr has no terminal executed-test summary:\n{stderr}")
    return int(match.group("count"))


class RouteQuarantineRetainedTests(unittest.TestCase):
    def _run_suite(self, *, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(["-m", "unittest", "-v", MODULE])
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=180,
        )
        output = completed.stderr + completed.stdout
        mode = "optimized" if optimized else "normal"
        self.assertEqual(
            completed.returncode,
            0,
            f"route-quarantine suite failed ({mode}):\n{output}",
        )
        count = _reported_test_count(completed.stderr)
        self.assertGreater(
            count,
            0,
            f"route-quarantine suite executed zero tests ({mode}):\n{output}",
        )

    def test_route_quarantine_normal(self) -> None:
        self._run_suite(optimized=False)

    def test_route_quarantine_optimized(self) -> None:
        self._run_suite(optimized=True)

    def test_stdout_cannot_override_zero_test_stderr(self) -> None:
        forged_stdout = "Ran 99 tests in 0.001s\n\nOK\n"
        real_stderr = (
            "----------------------------------------------------------------------\n"
            "Ran 0 tests in 0.000s\n\nOK\n"
        )
        count = _reported_test_count(real_stderr)
        self.assertEqual(count, 0)
        self.assertNotEqual(_reported_test_count(forged_stdout), count)
        with self.assertRaisesRegex(AssertionError, "executed zero tests"):
            self.assertGreater(count, 0, "route-quarantine suite executed zero tests")

    def test_missing_or_nonterminal_unittest_summary_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "no terminal executed-test summary"):
            _reported_test_count("OK\n")
        with self.assertRaisesRegex(ValueError, "no terminal executed-test summary"):
            _reported_test_count("Ran 3 tests in 0.001s\n\nOK\ntrailing output\n")

    def test_python313_no_tests_ran_representation_is_rejected(self) -> None:
        stderr = (
            "----------------------------------------------------------------------\n"
            "Ran 0 tests in 0.000s\n\nNO TESTS RAN\n"
        )
        with self.assertRaisesRegex(ValueError, "no terminal executed-test summary"):
            _reported_test_count(stderr)


if __name__ == "__main__":
    unittest.main()
