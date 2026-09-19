from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class RelationshipContactGuardOptimizedProof(unittest.TestCase):
    def test_original_guard_suites_pass_under_real_optimized_python(self) -> None:
        root = Path(__file__).resolve().parent
        proc = subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "-q",
                "test_relationship_contact_guard",
                "test_relationship_contact_guard_direct_boundary",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        self.assertEqual(
            proc.returncode,
            0,
            "optimized relationship-contact guard suites failed\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
