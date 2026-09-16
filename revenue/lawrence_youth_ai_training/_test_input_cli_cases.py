from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revenue.lawrence_youth_ai_training import gate
from revenue.lawrence_youth_ai_training._test_support import *

class InputAndCliTests(unittest.TestCase):
    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(gate.QualificationInputError):
            gate.strict_json_loads(b'{"a":1,"a":2}', "duplicate")

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(gate.QualificationInputError):
            gate.strict_json_loads(b'{"a":NaN}', "nonfinite")

    def test_old_current_clock_flag_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "snapshot.json"
            path.write_text(json.dumps(snapshot()), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "revenue.lawrence_youth_ai_training.cli",
                    "evaluate-current",
                    str(path),
                    "--expected-rfp-sha256",
                    SHA,
                    "--evaluated-at",
                    NOW,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unrecognized arguments", proc.stderr)

    def test_cli_historical_is_explicitly_non_authorizing(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "snapshot.json"
            path.write_text(json.dumps(snapshot()), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "revenue.lawrence_youth_ai_training.cli",
                    "evaluate-historical",
                    str(path),
                    "--expected-rfp-sha256",
                    SHA,
                    "--evaluated-at",
                    NOW,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 3)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["receipt"]["current_authority"])
        self.assertEqual(payload["receipt"]["decision"], gate.HOLD)


