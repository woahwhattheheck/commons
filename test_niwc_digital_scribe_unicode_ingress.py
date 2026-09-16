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


def surrogate_value_packet() -> str:
    obj = json.loads(FIXTURE.read_text(encoding="utf-8"))
    obj["events"][0]["assertion"] = "\ud800"
    return json.dumps(obj, ensure_ascii=True)


def hostile_packets() -> tuple[tuple[str, str], ...]:
    return (
        ("value.json", surrogate_value_packet()),
        ("key.json", r'{"\ud800":1}'),
        ("duplicate-key.json", r'{"\ud800":1,"\ud800":2}'),
    )


class EvidenceAARUnicodeIngressTests(unittest.TestCase):
    def test_all_surrogate_shapes_are_contract_errors(self):
        for name, payload in hostile_packets():
            with self.subTest(name=name), self.assertRaises(wb.ContractError):
                if name == "value.json":
                    wb.finalize_bundle(payload.encode("utf-8"))
                else:
                    wb.strict_json_loads(payload.encode("utf-8"))

    def _check_cli(self, optimized: bool):
        with tempfile.TemporaryDirectory() as td:
            for name, payload in hostile_packets():
                path = Path(td) / name
                path.write_text(payload, encoding="utf-8")
                argv = [sys.executable]
                if optimized:
                    argv.append("-O")
                proc = subprocess.run(
                    [*argv, str(MODULE), "compile", str(path)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(proc.returncode, 2, (name, proc.stderr))
                self.assertIn("ERROR:", proc.stderr)
                self.assertNotIn("Traceback", proc.stderr)
                self.assertEqual(proc.stdout, "")

    def test_cli_surrogate_shapes_normal_are_controlled(self):
        self._check_cli(False)

    def test_cli_surrogate_shapes_optimized_are_controlled(self):
        self._check_cli(True)


if __name__ == "__main__":
    unittest.main()
