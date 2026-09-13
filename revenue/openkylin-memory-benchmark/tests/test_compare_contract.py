import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "kylin_memory_bench.py"
DATASET = ROOT / "sample" / "dataset.jsonl"
REFERENCE = ROOT / "sample" / "reference-agent.json"
FORGETFUL = ROOT / "sample" / "forgetful-agent.json"


class CompareContractTests(unittest.TestCase):
    def _run(self, evidence_paths, out_dir):
        cmd = [
            sys.executable,
            str(CLI),
            "compare",
            "--dataset",
            str(DATASET),
        ]
        for path in evidence_paths:
            cmd.extend(["--evidence", str(path)])
        cmd.extend(["--out-dir", str(out_dir)])
        return subprocess.run(cmd, text=True, capture_output=True, check=False)

    def _write_agent(self, path, agent, source=REFERENCE):
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["agent"] = agent
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_compare_requires_at_least_two_evidence_bundles(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "out"
            proc = self._run([REFERENCE], out_dir)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("at least two evidence bundles", proc.stderr)
            self.assertFalse(out_dir.exists())

    def test_compare_rejects_duplicate_agent_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "out"
            proc = self._run([REFERENCE, REFERENCE], out_dir)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("agent names must be unique", proc.stderr)
            self.assertFalse(out_dir.exists())

    def test_compare_rejects_output_slug_collision_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            left = tmp_path / "left.json"
            right = tmp_path / "right.json"
            out_dir = tmp_path / "out"
            self._write_agent(left, "agent one")
            self._write_agent(right, "agent-one")
            proc = self._run([left, right], out_dir)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("output names collide after sanitization", proc.stderr)
            self.assertFalse(out_dir.exists())

    def test_compare_rejects_case_insensitive_slug_collision_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            upper = tmp_path / "upper.json"
            lower = tmp_path / "lower.json"
            out_dir = tmp_path / "out"
            self._write_agent(upper, "Agent")
            self._write_agent(lower, "agent")
            proc = self._run([upper, lower], out_dir)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("output names collide after sanitization", proc.stderr)
            self.assertFalse(out_dir.exists())

    def test_compare_validates_complete_set_before_writing(self):
        payload = json.loads(FORGETFUL.read_text(encoding="utf-8"))
        payload["records"][0]["channels"]["invalid"] = []
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            invalid = tmp_path / "invalid.json"
            invalid.write_text(json.dumps(payload), encoding="utf-8")
            out_dir = tmp_path / "out"
            proc = self._run([REFERENCE, FORGETFUL, invalid], out_dir)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("unknown channels", proc.stderr)
            self.assertFalse(out_dir.exists())

    def test_documented_demo_runner_is_executable(self):
        self.assertTrue(os.access(ROOT / "run_demo.sh", os.X_OK))


if __name__ == "__main__":
    unittest.main()
