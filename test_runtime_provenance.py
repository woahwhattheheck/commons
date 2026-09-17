"""Retain runtime-provenance verification inside the existing Commons test battery.

A dedicated workflow would be the 68th active workflow and violates the repository's
retained workflow-surface budget. This root bridge makes the complete focused suite
discoverable by host/ci_battery.py, runs it in normal and optimized Python, and
exercises the canonical registry CLI without creating a new workflow slot.
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

    def assert_child_ok(self, proc: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)

    def assert_nonempty_unittest_run(self, proc: subprocess.CompletedProcess[str]) -> None:
        output = proc.stderr + proc.stdout
        match = re.search(r"Ran ([0-9]+) tests? in ", output)
        if match is None:
            self.fail(f"missing unittest execution count:\n{output}")
        count = int(match.group(1))
        self.assertGreater(count, 0, f"zero-test false green:\n{output}")
        self.assertIn("OK", output)

    def test_focused_suite_normal_and_optimized(self) -> None:
        for optimized in (False, True):
            with self.subTest(optimized=optimized):
                proc = self.run_child(*DISCOVER, optimized=optimized)
                self.assert_child_ok(proc)
                self.assert_nonempty_unittest_run(proc)

    def test_zero_discovery_cannot_false_green(self) -> None:
        proc = subprocess.CompletedProcess(
            args=[sys.executable, *DISCOVER],
            returncode=0,
            stdout="",
            stderr="----------------------------------------------------------------------\nRan 0 tests in 0.000s\n\nOK\n",
        )
        self.assert_child_ok(proc)
        with self.assertRaises(AssertionError):
            self.assert_nonempty_unittest_run(proc)

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
