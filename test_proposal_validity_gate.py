from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import unittest

_UNITTEST_TERMINAL = re.compile(
    r"(?m)^Ran\s+(?P<count>\d+)\s+tests?\s+in\s+[^\r\n]+\r?\n"
    r"\r?\nOK(?:\s+\([^\r\n]*\))?\r?\n?\Z"
)


def _reported_test_count(stderr: str) -> int:
    match = _UNITTEST_TERMINAL.search(stderr)
    if match is None:
        raise ValueError(f"unittest stderr has no terminal executed-test summary:\n{stderr}")
    return int(match.group("count"))


class ProposalValidityGateRetainedTests(unittest.TestCase):
    def _run(self, optimized: bool) -> subprocess.CompletedProcess[str]:
        root = Path(__file__).resolve().parent
        args = [sys.executable]
        if optimized:
            args.append("-O")
        args += [
            "-m",
            "unittest",
            "-v",
            "revenue.proposal_validity_gate.test_gate",
            "revenue.proposal_validity_gate.test_boundary",
        ]
        return subprocess.run(
            args,
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )

    def test_nested_suite_executes_normal(self):
        proc = self._run(False)
        output = proc.stderr + proc.stdout
        self.assertEqual(proc.returncode, 0, output)
        self.assertGreater(_reported_test_count(proc.stderr), 0, output)

    def test_nested_suite_executes_under_real_python_o(self):
        proc = self._run(True)
        output = proc.stderr + proc.stdout
        self.assertEqual(proc.returncode, 0, output)
        self.assertGreater(_reported_test_count(proc.stderr), 0, output)

    def test_product_sources_compile_normal_and_optimized(self):
        root = Path(__file__).resolve().parent
        for relative in (
            "revenue/proposal_validity_gate/engine.py",
            "revenue/proposal_validity_gate/boundary.py",
            "revenue/proposal_validity_gate/cli.py",
            "revenue/proposal_validity_gate/test_gate.py",
            "revenue/proposal_validity_gate/test_boundary.py",
        ):
            source = (root / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative, optimize=0):
                compile(source, relative, "exec", optimize=0)
            with self.subTest(path=relative, optimize=2):
                compile(source, relative, "exec", optimize=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
