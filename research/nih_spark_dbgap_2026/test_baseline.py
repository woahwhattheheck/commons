from __future__ import annotations

import copy
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from .baseline import (
    ONT_NONE, ContractError, Corpus, ResourceManifest, build_run_receipt, canonical_bytes,
    evaluate_track1, evaluate_track2, load_json_strict, load_json_strict_bytes,
    scan_source_for_query_keyed_hardcoding, semantic_sha256, track1_predict, track2_rank,
    verify_run_receipt,
)

ROOT = Path(__file__).parent
FIX = ROOT / "fixtures"
REPO = ROOT.parents[1]


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.corpus_raw = load_json_strict(FIX / "synthetic_corpus.json")
        self.resources_raw = load_json_strict(FIX / "synthetic_resources.json")
        self.corpus = Corpus.from_obj(self.corpus_raw)
        self.resources = ResourceManifest.from_obj(self.resources_raw)

    def test_json_hostiles(self):
        with self.assertRaises(ContractError):
            load_json_strict_bytes(b'{"a":1,"a":2}')
        with self.assertRaises(ContractError):
            load_json_strict_bytes(b'{"a":NaN}')
        bad = copy.deepcopy(self.corpus_raw)
        bad["concepts"][0]["extra"] = True
        with self.assertRaises(ContractError):
            Corpus.from_obj(bad)
        bad = copy.deepcopy(self.corpus_raw)
        bad["variables"][0]["text"] += " changed"
        with self.assertRaises(ContractError):
            Corpus.from_obj(bad)

    def test_path_ingress_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            target, link = Path(td) / "target.json", Path(td) / "link.json"
            target.write_bytes(b'{"ok":true}')
            try:
                os.symlink(target, link)
            except OSError as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(ContractError):
                load_json_strict(link)

    def test_track1_fixture_maps_and_abstains(self):
        inp = load_json_strict(FIX / "track1_input.json")
        out = track1_predict(self.corpus, inp, abstain_coverage_bp=5000, top_k=4)
        got = {r["query_variable_id"]: r["predicted_concept_id"] for r in out["predictions"]}
        self.assertEqual(got["fixture-track1-bmi-001"], "C_BMI")
        self.assertEqual(got["fixture-track1-ckd-002"], "C_CKD")
        self.assertEqual(got["fixture-track1-none-003"], ONT_NONE)
        stripped = dict(out); claimed = stripped.pop("output_sha256")
        self.assertEqual(claimed, semantic_sha256(stripped))

    def test_track1_order_invariant_and_bool_rejected(self):
        inp = load_json_strict(FIX / "track1_input.json")
        rev = {"schema": inp["schema"], "variables": list(reversed(inp["variables"]))}
        self.assertEqual(track1_predict(self.corpus, inp), track1_predict(self.corpus, rev))
        with self.assertRaises(ContractError):
            track1_predict(self.corpus, {"schema": inp["schema"], "variables": []}, abstain_coverage_bp=True)

    def test_track1_macro_f1_includes_none(self):
        result = evaluate_track1(
            {"a": "C_AGE", "b": ONT_NONE, "c": "C_ASTHMA", "d": "C_ASTHMA"},
            {"a": "C_AGE", "b": ONT_NONE, "c": "C_AGE", "d": "C_ASTHMA"},
        )
        self.assertTrue(result["includes_ont_none"])
        self.assertGreater(result["macro_f1_scaled_1e6"], 0)

    def test_track2_fixture_intersection_and_order(self):
        inp = load_json_strict(FIX / "track2_input.json")
        out = track2_rank(self.corpus, inp, top_k=4)
        by_q = {r["query_id"]: r["ranked_studies"] for r in out["results"]}
        self.assertEqual(by_q["fixture-track2-asthma-001"][0]["study_id"], "phs001")
        self.assertEqual(by_q["fixture-track2-kidney-002"][0]["study_id"], "phs003")
        rev = {"schema": inp["schema"], "queries": list(reversed(inp["queries"]))}
        self.assertEqual(out, track2_rank(self.corpus, rev, top_k=4))

    def test_ndcg_perfect_degraded_and_duplicate(self):
        rel = {"q": {"phs001": 3, "phs002": 1, "phs003": 0}}
        perfect = evaluate_track2({"q": ["phs001", "phs002", "phs003"]}, rel, k=3)
        bad = evaluate_track2({"q": ["phs003", "phs002", "phs001"]}, rel, k=3)
        self.assertEqual(perfect["mean_ndcg_scaled_1e9"], 1_000_000_000)
        self.assertLess(bad["mean_ndcg_scaled_1e9"], perfect["mean_ndcg_scaled_1e9"])
        with self.assertRaises(ContractError):
            evaluate_track2({"q": ["phs001", "phs001"]}, {"q": {"phs001": 2}}, k=2)

    def test_receipt_binds_input_output_policy_and_resources(self):
        inp = load_json_strict(FIX / "track2_input.json")
        out = track2_rank(self.corpus, inp, top_k=2)
        policy = {"top_k": 2}
        rec = build_run_receipt(track=2, corpus=self.corpus, resources=self.resources, input_obj=inp, output_obj=out, source_version="test-v1", policy=policy)
        self.assertTrue(verify_run_receipt(rec, track=2, corpus=self.corpus, resources=self.resources, input_obj=inp, output_obj=out, source_version="test-v1", policy=policy))
        changed = copy.deepcopy(out); changed["results"][0]["ranked_studies"].reverse()
        self.assertFalse(verify_run_receipt(rec, track=2, corpus=self.corpus, resources=self.resources, input_obj=inp, output_obj=changed, source_version="test-v1", policy=policy))

    def test_runtime_has_no_fixture_query_lookup_keys(self):
        runtime = "".join((ROOT / name).read_text(encoding="utf-8") for name in ["core.py", "contracts.py", "track1.py", "track2.py", "baseline.py", "cli.py"])
        ids = ["fixture-track1-bmi-001", "fixture-track2-asthma-001"]
        self.assertEqual(scan_source_for_query_keyed_hardcoding(runtime, ids), [])
        self.assertEqual(scan_source_for_query_keyed_hardcoding(runtime + "# fixture-track2-asthma-001", ids), ["fixture-track2-asthma-001"])

    def test_cli_create_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            out, rec = Path(td) / "out.json", Path(td) / "receipt.json"
            cmd = [sys.executable, "-m", "research.nih_spark_dbgap_2026.cli", "--track", "2", "--corpus", str(FIX / "synthetic_corpus.json"), "--resources", str(FIX / "synthetic_resources.json"), "--input", str(FIX / "track2_input.json"), "--output", str(out), "--receipt", str(rec), "--source-version", "test-v1", "--top-k", "4"]
            first = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("File exists", second.stderr)


if __name__ == "__main__":
    unittest.main()
