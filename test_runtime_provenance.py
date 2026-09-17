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
TEST_COUNT = re.compile(r"\bRan\s+(\d+)\s+tests?\s+in\b")


def reported_test_count(output: str) -> int:
    """Return unittest's terminal executed-test count, rejecting missing summaries."""
    matches = TEST_COUNT.findall(output)
    if not matches:
        raise ValueError(f"unittest output has no executed-test summary:\n{output}")
    return int(matches[-1])


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
        output = self.child_output(proc)
        count = reported_test_count(output)
        self.assertGreater(count, 0, f"focused discovery executed zero tests:\n{output}")
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
                    self.assertEqual(reported_test_count(self.child_output(proc)), 0)
                    with self.assertRaisesRegex(AssertionError, "executed zero tests"):
                        self.assert_child_nonvacuous(proc)

    def test_missing_unittest_summary_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "no executed-test summary"):
            reported_test_count("OK")

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
