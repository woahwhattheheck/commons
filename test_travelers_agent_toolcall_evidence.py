from __future__ import annotations

import subprocess
import sys
import unittest


MODULES = (
    "revenue.travelers_agent_toolcall_evidence.test_gate",
    "revenue.travelers_agent_toolcall_evidence.test_trace_states",
    "revenue.travelers_agent_toolcall_evidence.test_scope_root",
    "revenue.travelers_agent_toolcall_evidence.test_bundle",
)


# Root placement is intentional: Commons tests.yml path-filters on root test_*.py.
# Run the complete focused carrier in normal and optimized Python without consuming
# a new active workflow slot.  Scope/root and semantic+structural bundle tests are
# deliberately enrolled here so advertised hardening cannot exist off-CI.
class TravelersAgentToolCallEvidenceRetainedBridge(unittest.TestCase):
    def _run(self, optimized: bool) -> None:
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(["-m", "unittest", "-v", *MODULES])
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
