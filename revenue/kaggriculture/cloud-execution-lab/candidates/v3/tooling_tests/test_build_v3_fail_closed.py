"""Focused regression coverage for build_v3 package-custody guards."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import build_v3  # noqa: E402


class BuildV3FailClosedTests(unittest.TestCase):
    def test_require_raises_with_original_message(self):
        with self.assertRaisesRegex(AssertionError, "custody-probe"):
            build_v3._require(False, "custody-probe")

    def test_require_survives_python_optimization(self):
        env = dict(os.environ)
        env["PYTHONOPTIMIZE"] = "1"
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                "import build_v3; build_v3._require(False, 'optimization-probe')",
            ],
            cwd=HERE,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("optimization-probe", completed.stderr)


if __name__ == "__main__":
    unittest.main()
