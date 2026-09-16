from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULE = ROOT / "competitions" / "niwc-digital-scribe-2026" / "workbench.py"
FIXTURE = ROOT / "competitions" / "niwc-digital-scribe-2026" / "fixtures" / "synthetic_exercise.json"
spec = importlib.util.spec_from_file_location("evidenceaar_unicode", MODULE)
assert spec and spec.loader
wb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wb)


def surrogate_packet() -> str:
    obj = json.loads(FIXTURE.read_text(encoding="utf-8"))
    obj["events"][0]["assertion"] = "\ud800"
    return json.dumps(obj, ensure_ascii=True)


class EvidenceAARUnicodeIngressTests(unittest.TestCase):
    def test_direct_surrogate_is_contract_error(self):
        with self.assertRaises(wb.ContractError):
            wb.finalize_bundle(surrogate_packet().encode("utf-8"))

    def _check_cli(self, optimized: bool):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "surrogate.json"
            path.write_text(surrogate_packet(), encoding="utf-8")
            argv = [sys.executable]
            if optimized:
                argv.append("-O")
            proc = subprocess.run(
                [*argv, str(MODULE), "compile", str(path)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn("ERROR:", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)
            self.assertEqual(proc.stdout, "")

    def test_cli_surrogate_normal_is_controlled(self):
        self._check_cli(False)

    def test_cli_surrogate_optimized_is_controlled(self):
        self._check_cli(True)


if __name__ == "__main__":
    unittest.main()
