"""Retain runtime-provenance verification inside the existing Commons test battery.

A dedicated workflow would be the 68th active workflow and violates the repository's
retained workflow-surface budget. This root bridge makes the complete focused suite
discoverable by host/ci_battery.py, proves discovery is non-vacuous, runs it in normal
and optimized Python, and exercises the canonical registry CLI without creating a new
workflow slot.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
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
EMPTY_DISCOVER = [
    "-m",
    "unittest",
    "discover",
    "-s",
    "tools/runtime_provenance",
    "-p",
    "__runtime_provenance_definitely_no_tests_*.py",
    "-v",
]
RUN_COUNT_RE = re.compile(r"\bRan\s+(\d+)\s+tests?\b")


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

    def assert_child_ok(self, proc: subprocess.CompletedProcess[str]) -> str:
        combined = proc.stderr + proc.stdout
        self.assertEqual(proc.returncode, 0, combined)
        return combined

    def require_positive_unittest_count(self, proc: subprocess.CompletedProcess[str]) -> int:
        combined = self.assert_child_ok(proc)
        match = RUN_COUNT_RE.search(combined)
        self.assertIsNotNone(match, "unittest output omitted an executed-test count:\n" + combined)
        count = int(match.group(1)) if match is not None else 0
        self.assertGreater(count, 0, "zero-test unittest discovery is a false green:\n" + combined)
        return count

    def test_focused_suite_normal_and_optimized_is_nonvacuous(self) -> None:
        counts: list[int] = []
        for optimized in (False, True):
            with self.subTest(optimized=optimized):
                proc = self.run_child(*DISCOVER, optimized=optimized)
                counts.append(self.require_positive_unittest_count(proc))
        self.assertEqual(counts[0], counts[1], "normal/optimized focused-suite counts diverged")

    def test_zero_test_discovery_is_explicitly_rejected(self) -> None:
        for optimized in (False, True):
            with self.subTest(optimized=optimized):
                proc = self.run_child(*EMPTY_DISCOVER, optimized=optimized)
                combined = self.assert_child_ok(proc)
                match = RUN_COUNT_RE.search(combined)
                self.assertIsNotNone(match, combined)
                self.assertEqual(int(match.group(1)), 0, combined)
                with self.assertRaisesRegex(AssertionError, "zero-test unittest discovery"):
                    self.require_positive_unittest_count(proc)

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
