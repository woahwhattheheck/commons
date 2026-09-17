from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent
PRODUCT = ROOT / "competitions" / "emergent-builderfest-2026" / "onewriter"
TRIGGER = "      - 'competitions/emergent-builderfest-2026/onewriter/**'"
_RAN = re.compile(r"\bRan\s+(\d+)\s+tests?\b")


class OneWriterRetainedTests(unittest.TestCase):
    def _run_nested(self, *, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(
            [
                "-m",
                "unittest",
                "discover",
                "-s",
                str(PRODUCT),
                "-p",
                "test_acceptance.py",
                "-v",
            ]
        )
        proc = subprocess.run(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=180,
        )
        output = proc.stdout.decode("utf-8", "replace")
        self.assertEqual(proc.returncode, 0, output)
        matches = _RAN.findall(output)
        self.assertTrue(matches, f"nested unittest emitted no test count:\n{output}")
        self.assertGreater(
            int(matches[-1]),
            0,
            f"nested unittest executed zero tests:\n{output}",
        )
        self.assertRegex(output, r"(?m)^OK$")

    def test_full_nested_suite_runs_normally(self):
        self._run_nested(optimized=False)

    def test_full_nested_suite_runs_under_optimized_python(self):
        self._run_nested(optimized=True)

    def test_product_path_wakes_both_retained_test_triggers(self):
        workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
            encoding="utf-8"
        )
        push, remainder = workflow.split("  pull_request:\n", 1)
        pull_request, _ = remainder.split("  workflow_dispatch:\n", 1)
        self.assertEqual(1, push.count(TRIGGER))
        self.assertEqual(1, pull_request.count(TRIGGER))
        self.assertEqual(2, workflow.count(TRIGGER))


if __name__ == "__main__":
    unittest.main(verbosity=2)
