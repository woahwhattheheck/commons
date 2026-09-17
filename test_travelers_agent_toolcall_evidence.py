from __future__ import annotations

import subprocess
import sys
import unittest


MODULE = "revenue.travelers_agent_toolcall_evidence.test_gate"


# Root placement is intentional: Commons tests.yml path-filters on root test_*.py.
# Run the focused carrier in normal and optimized Python without consuming a new
# active workflow slot.
class TravelersAgentToolCallEvidenceRetainedBridge(unittest.TestCase):
    def _run(self, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(["-m", "unittest", "-v", MODULE])
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )

    def test_normal(self) -> None:
        self._run(False)

    def test_optimized(self) -> None:
        self._run(True)


if __name__ == "__main__":
    unittest.main()
