from __future__ import annotations

from pathlib import Path
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
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=180,
        )
        output = proc.stdout.decode("utf-8", "replace")
        self.assertEqual(proc.returncode, 0, output)
        self.assertIn("OK", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
