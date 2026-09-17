from __future__ import annotations

import subprocess
import sys
import unittest


class CasmiMultiSpectrumRetainedBridge(unittest.TestCase):
    def _run(self, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(["-m", "unittest", "-v", "tests.test_enveda_casmi_multispectrum"])
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(
            completed.returncode,
            0,
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )

    def test_nested_suite_normal(self):
        self._run(False)

    def test_nested_suite_optimized(self):
        self._run(True)


if __name__ == "__main__":
    unittest.main()
