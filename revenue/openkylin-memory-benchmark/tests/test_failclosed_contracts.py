import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
import kylin_memory_bench as bench

DATASET = ROOT / "sample" / "dataset.jsonl"
REFERENCE = ROOT / "sample" / "reference-agent.json"
FORGETFUL = ROOT / "sample" / "forgetful-agent.json"


class FailClosedContractTests(unittest.TestCase):
    def _main_compare(self, evidence_paths, out_dir):
        argv = ["compare", "--dataset", str(DATASET)]
        for path in evidence_paths:
            argv.extend(("--evidence", str(path)))
        argv.extend(("--out-dir", str(out_dir)))
        return bench.main(argv)

    def test_compare_requires_two_evidence_bundles_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "reports"
            self.assertEqual(self._main_compare([REFERENCE], out), 2)
            self.assertFalse(out.exists())

    def test_compare_rejects_duplicate_agent_names_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "reports"
            self.assertEqual(self._main_compare([REFERENCE, REFERENCE], out), 2)
            self.assertFalse(out.exists())

    def test_compare_rejects_slug_collisions_before_writing(self):
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
            self.assertEqual(self._main_compare([first_path, second_path], out), 2)
            self.assertFalse(out.exists())

    def test_compare_rejects_case_insensitive_slug_collision_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            upper = json.loads(REFERENCE.read_text(encoding="utf-8"))
            lower = json.loads(FORGETFUL.read_text(encoding="utf-8"))
            upper["agent"] = "Agent"
            lower["agent"] = "agent"
            upper_path = tmp_path / "upper.json"
            lower_path = tmp_path / "lower.json"
            upper_path.write_text(json.dumps(upper), encoding="utf-8")
            lower_path.write_text(json.dumps(lower), encoding="utf-8")
            out = tmp_path / "reports"
            self.assertEqual(self._main_compare([upper_path, lower_path], out), 2)
            self.assertFalse(out.exists())

    def test_score_provenance_hashes_exact_evidence_bytes_that_were_scored(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            evidence = tmp_path / "evidence.json"
            original = REFERENCE.read_bytes()
            evidence.write_bytes(original)
            mutated = json.loads(original.decode("utf-8"))
            mutated["agent"] = "MUTATED-AFTER-READ"
            mutated_bytes = json.dumps(mutated).encode("utf-8")
            out = tmp_path / "reports"

            real_loader = bench._load_evidence_with_sha

            def load_then_mutate(path, scenario_ids):
                payload, digest = real_loader(path, scenario_ids)
                if Path(path) == evidence:
                    evidence.write_bytes(mutated_bytes)
                return payload, digest

            with mock.patch.object(bench, "_load_evidence_with_sha", side_effect=load_then_mutate):
                rc = bench.main([
                    "score", "--dataset", str(DATASET), "--evidence", str(evidence),
                    "--out-dir", str(out),
                ])

            self.assertEqual(rc, 0)
            report = json.loads((out / "reference-agent.report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["agent"], "reference-agent")
            self.assertEqual(report["provenance"]["evidence_sha256"], hashlib.sha256(original).hexdigest())
            self.assertNotEqual(report["provenance"]["evidence_sha256"], hashlib.sha256(mutated_bytes).hexdigest())

    def test_score_provenance_hashes_exact_dataset_bytes_that_were_scored(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset = tmp_path / "dataset.jsonl"
            original = DATASET.read_bytes()
            dataset.write_bytes(original)
            mutated_bytes = original + b"\n# mutated after capture\n"
            out = tmp_path / "reports"

            real_loader = bench._read_dataset_with_sha

            def load_then_mutate(path):
                scenarios, digest = real_loader(path)
                if Path(path) == dataset:
                    dataset.write_bytes(mutated_bytes)
                return scenarios, digest

            with mock.patch.object(bench, "_read_dataset_with_sha", side_effect=load_then_mutate):
                rc = bench.main([
                    "score", "--dataset", str(dataset), "--evidence", str(REFERENCE),
                    "--out-dir", str(out),
                ])

            self.assertEqual(rc, 0)
            report = json.loads((out / "reference-agent.report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["provenance"]["dataset_sha256"], hashlib.sha256(original).hexdigest())
            self.assertNotEqual(report["provenance"]["dataset_sha256"], hashlib.sha256(mutated_bytes).hexdigest())

    def test_documented_demo_runner_is_executable(self):
        self.assertTrue(os.access(ROOT / "run_demo.sh", os.X_OK))


if __name__ == "__main__":
    unittest.main()
