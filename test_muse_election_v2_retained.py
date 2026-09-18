from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import unittest

from tools.outbound_send_guard.test_muse_current_authority_v2 import CurrentAuthorityDonorTests
from tools.outbound_send_guard.test_muse_election_v2 import MuseElectionV2Tests


_CANONICAL_SURFACES = (
    "tools/outbound_send_guard/_muse_election_v2_core.py.inc",
    "tools/outbound_send_guard/_muse_election_v2_tests_core.py",
    "tools/outbound_send_guard/muse_current_authority_v2.py",
    "tools/outbound_send_guard/muse_election_v2.py",
    "tools/outbound_send_guard/test_muse_current_authority_v2.py",
    "tools/outbound_send_guard/test_muse_election_v2.py",
)
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


class MuseElectionV2RetainedTests(unittest.TestCase):
    """Retain canonical Muse-v2 normal/optimized proof without a new workflow slot."""

    def test_canonical_surfaces_compile_normal_and_optimized(self):
        root = Path(__file__).resolve().parent
        for relative in _CANONICAL_SURFACES:
            source = (root / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative, optimize=0):
                compile(source, relative, "exec", optimize=0)
            with self.subTest(path=relative, optimize=2):
                compile(source, relative, "exec", optimize=2)

    def test_complete_nested_suites_execute_under_python_o(self):
        root = Path(__file__).resolve().parent
        proc = subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "-v",
                "tools.outbound_send_guard.test_muse_election_v2",
                "tools.outbound_send_guard.test_muse_current_authority_v2",
            ],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )
        output = proc.stderr + proc.stdout
        self.assertEqual(proc.returncode, 0, output)
        count = _reported_test_count(proc.stderr)
        self.assertGreater(count, 0, f"canonical Muse v2 suite executed zero tests:\n{output}")

    def test_stdout_cannot_override_real_zero_test_stderr_summary(self):
        proc = subprocess.CompletedProcess(
            args=[sys.executable, "-O", "-m", "unittest"],
            returncode=0,
            stdout="Ran 99 tests in 0.001s\n\nOK\n",
            stderr="----------------------------------------------------------------------\nRan 0 tests in 0.000s\n\nOK\n",
        )
        count = _reported_test_count(proc.stderr)
        self.assertEqual(count, 0)
        with self.assertRaisesRegex(AssertionError, "executed zero tests"):
            self.assertGreater(count, 0, "canonical Muse v2 suite executed zero tests")

    def test_missing_or_nonterminal_unittest_summary_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "no terminal executed-test summary"):
            _reported_test_count("OK\n")
        with self.assertRaisesRegex(ValueError, "no terminal executed-test summary"):
            _reported_test_count("Ran 3 tests in 0.001s\n\nOK\ntrailing output\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
