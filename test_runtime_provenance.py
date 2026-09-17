"""Retain runtime-provenance verification inside the existing Commons test battery.

A dedicated workflow would be the 68th active workflow and violates the repository's
retained workflow-surface budget. This root bridge makes the complete focused suite
discoverable by host/ci_battery.py, proves that discovery is non-vacuous in normal
and optimized Python, and exercises the canonical registry CLI without creating a
new workflow slot.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DISCOVER = [
    "-m",
    "unittest",
    "discover",
    "-s",
    "tools/runtime_provenance",
    "-p",
    "test_*.py",
    "-v",
]
UNITTEST_TERMINAL = re.compile(
    r"(?m)^Ran\s+(?P<count>\d+)\s+tests?\s+in\s+[^\r\n]+\r?\n"
    r"\r?\nOK(?:\s+\([^\r\n]*\))?\r?\n?\Z"
)


def reported_test_count(stderr: str) -> int:
    """Return unittest's terminal stderr execution count or fail closed."""
    match = UNITTEST_TERMINAL.search(stderr)
    if match is None:
        raise ValueError(f"unittest stderr has no terminal executed-test summary:\n{stderr}")
    return int(match.group("count"))


class RuntimeProvenanceRetainedTests(unittest.TestCase):
    def run_child(self, *args: str, optimized: bool = False) -> subprocess.CompletedProcess[str]:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(args)
        return subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )

    @staticmethod
    def child_output(proc: subprocess.CompletedProcess[str]) -> str:
        return proc.stderr + proc.stdout

    def assert_child_ok(self, proc: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(proc.returncode, 0, self.child_output(proc))

    def assert_child_nonvacuous(self, proc: subprocess.CompletedProcess[str]) -> int:
        self.assert_child_ok(proc)
        count = reported_test_count(proc.stderr)
        self.assertGreater(count, 0, f"focused discovery executed zero tests:\n{self.child_output(proc)}")
        return count

    def test_focused_suite_normal_and_optimized_is_nonvacuous(self) -> None:
        counts: list[int] = []
        for optimized in (False, True):
            with self.subTest(optimized=optimized):
                proc = self.run_child(*DISCOVER, optimized=optimized)
                counts.append(self.assert_child_nonvacuous(proc))
        self.assertEqual(counts[0], counts[1], "normal and optimized discovery counts diverged")

    def test_empty_discovery_false_green_is_rejected_normal_and_optimized(self) -> None:
        with tempfile.TemporaryDirectory(prefix="runtime-provenance-empty-", dir=ROOT) as empty_dir:
            empty_discover = [
                "-m",
                "unittest",
                "discover",
                "-s",
                empty_dir,
                "-p",
                "test_*.py",
                "-v",
            ]
            for optimized in (False, True):
                with self.subTest(optimized=optimized):
                    proc = self.run_child(*empty_discover, optimized=optimized)
                    self.assertEqual(proc.returncode, 0, self.child_output(proc))
                    self.assertEqual(reported_test_count(proc.stderr), 0)
                    with self.assertRaisesRegex(AssertionError, "executed zero tests"):
                        self.assert_child_nonvacuous(proc)

    def test_stdout_cannot_override_real_zero_test_stderr_summary(self) -> None:
        proc = subprocess.CompletedProcess(
            args=[sys.executable, *DISCOVER],
            returncode=0,
            stdout="Ran 99 tests in 0.001s\n\nOK\n",
            stderr="----------------------------------------------------------------------\nRan 0 tests in 0.000s\n\nOK\n",
        )
        self.assertEqual(reported_test_count(proc.stderr), 0)
        with self.assertRaisesRegex(AssertionError, "executed zero tests"):
            self.assert_child_nonvacuous(proc)

    def test_missing_or_nonterminal_unittest_summary_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "no terminal executed-test summary"):
            reported_test_count("OK\n")
        with self.assertRaisesRegex(ValueError, "no terminal executed-test summary"):
            reported_test_count("Ran 3 tests in 0.001s\n\nOK\ntrailing output\n")

    def test_canonical_registry_verify_is_descriptive_only(self) -> None:
        proc = self.run_child(
            "-m",
            "tools.runtime_provenance.runtime_registry",
            "verify",
            "runtime/agent_runtime_registry.json",
        )
        self.assert_child_ok(proc)
        receipt = json.loads(proc.stdout)
        self.assertFalse(receipt["external_send_authorized"])
        self.assertFalse(receipt["provider_mutation_authorized"])
        self.assertFalse(receipt["payment_authorized"])
        self.assertFalse(receipt["credential_authorized"])
        self.assertFalse(receipt["deployment_mutation_authorized"])

    def test_canonical_registry_digest_is_sha256(self) -> None:
        proc = self.run_child(
            "-m",
            "tools.runtime_provenance.runtime_registry",
            "digest",
            "runtime/agent_runtime_registry.json",
        )
        self.assert_child_ok(proc)
        self.assertRegex(proc.stdout.strip(), r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
