from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HERE = ROOT / "muhl/containers/MUHL_VISIBLE"


class CloudFoundryTests(unittest.TestCase):
    def test_legacy_batch_never_starts_or_restarts_python(self):
        batch = (HERE / "FOUNDRY_FOREVER.bat").read_text(encoding="utf-8")
        self.assertIn("REFUSE_LOCAL_COMPUTE", batch)
        self.assertNotIn("goto loop", batch.lower())
        self.assertNotIn("timeout /t", batch.lower())
        self.assertNotIn("schtasks", batch.lower())
        self.assertNotIn("python muhl_foundry_live.py", batch.lower())

    def test_python_entrypoint_refuses_before_local_compute(self):
        completed = subprocess.run(
            [sys.executable, str(HERE / "muhl_foundry_live.py"), "--rounds", "1"],
            text=True,
            capture_output=True,
            check=False,
            env={},
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("REFUSE_LOCAL_COMPUTE", completed.stderr)

    def test_cloud_workflow_is_bounded_and_github_hosted(self):
        workflow = (ROOT / ".github/workflows/muhlnickel-foundry-cloud.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("runs-on: ubuntu-latest", workflow)
        self.assertIn("timeout-minutes: 15", workflow)
        self.assertIn('"$FOUNDRY_ROUNDS" -gt 100', workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertNotIn("self-hosted", workflow)


if __name__ == "__main__":
    unittest.main()
