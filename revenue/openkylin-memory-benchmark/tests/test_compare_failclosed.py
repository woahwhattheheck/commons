import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "sample" / "dataset.jsonl"
REFERENCE = ROOT / "sample" / "reference-agent.json"
FORGETFUL = ROOT / "sample" / "forgetful-agent.json"
CLI = ROOT / "kylin_memory_bench.py"


class CompareFailClosedTests(unittest.TestCase):
    def _compare(self, evidence: list[Path], out_dir: Path) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(CLI), "compare", "--dataset", str(DATASET)]
        for path in evidence:
            cmd.extend(("--evidence", str(path)))
        cmd.extend(("--out-dir", str(out_dir)))
        return subprocess.run(cmd, text=True, capture_output=True, check=False)

    def test_requires_two_evidence_bundles_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "reports"
            proc = self._compare([REFERENCE], out)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("at least two evidence bundles", proc.stderr)
            self.assertFalse(out.exists())

    def test_rejects_duplicate_agent_names_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            duplicate = json.loads(FORGETFUL.read_text(encoding="utf-8"))
            duplicate["agent"] = "reference-agent"
            duplicate_path = tmp_path / "duplicate.json"
            duplicate_path.write_text(json.dumps(duplicate), encoding="utf-8")
            out = tmp_path / "reports"
            proc = self._compare([REFERENCE, duplicate_path], out)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("agent names must be unique", proc.stderr)
            self.assertFalse(out.exists())

    def test_rejects_slug_collisions_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            first = json.loads(REFERENCE.read_text(encoding="utf-8"))
            second = json.loads(FORGETFUL.read_text(encoding="utf-8"))
            first["agent"] = "agent one"
            second["agent"] = "agent-one"
            first_path = tmp_path / "first.json"
            second_path = tmp_path / "second.json"
            first_path.write_text(json.dumps(first), encoding="utf-8")
            second_path.write_text(json.dumps(second), encoding="utf-8")
            out = tmp_path / "reports"
            proc = self._compare([first_path, second_path], out)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("filenames collide", proc.stderr)
            self.assertFalse(out.exists())

    def test_documented_demo_runner_is_executable(self):
        self.assertTrue(os.access(ROOT / "run_demo.sh", os.X_OK))


if __name__ == "__main__":
    unittest.main()
