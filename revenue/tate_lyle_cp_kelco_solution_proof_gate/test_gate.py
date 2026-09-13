from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

try:
    from .acceptance import fixture
    from .gate import (
        GateError, HOLD, compile_artifacts, evaluate, normalize_packet, policy_commitment,
        snapshot_commitment, strict_json_loads, verify_artifacts, write_artifacts_exclusive,
    )
except ImportError:
    from acceptance import fixture
    from gate import (
        GateError, HOLD, compile_artifacts, evaluate, normalize_packet, policy_commitment,
        snapshot_commitment, strict_json_loads, verify_artifacts, write_artifacts_exclusive,
    )

EVAL = "2026-09-13T14:30:00Z"
EXPECTED_COUNTS = {
    "SPEC_REVISION_MISMATCH": 20,
    "REGION_USE_CLAIM_MISMATCH": 15,
    "LEGACY_MAPPING_MISMATCH": 15,
    "STABILITY_MISMATCH": 15,
    "OWNER_VERSION_MISMATCH": 10,
}


def commitments(packet):
    n = normalize_packet(packet)
    return snapshot_commitment(n), policy_commitment(n)


class GateTests(unittest.TestCase):
    def test_canonical_acceptance_exact(self):
        p = fixture()
        s, pol = commitments(p)
        r = evaluate(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        self.assertEqual(r["decision"], HOLD)
        self.assertEqual(r["summary"]["record_count"], 120)
        self.assertEqual(r["summary"]["pass_count"], 90)
        self.assertEqual(r["summary"]["hold_count"], 30)
        self.assertEqual(r["summary"]["seeded_defect_code_count"], 75)
        self.assertEqual(r["summary"]["defect_code_counts"], EXPECTED_COUNTS)
        self.assertEqual(sum(len([c for c in row["codes"] if c in EXPECTED_COUNTS]) for row in r["rows"]), 75)

    def test_all_30_seeded_rows_hold_and_90_clean_pass(self):
        p = fixture()
        s, pol = commitments(p)
        r = evaluate(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        by_id = {row["record_id"]: row for row in r["rows"]}
        for i in range(30):
            self.assertEqual(by_id[f"PACK-{i:04d}"]["state"], "HOLD")
        for i in range(30, 120):
            self.assertEqual(by_id[f"PACK-{i:04d}"]["state"], "PASS")

    def test_two_runs_byte_identical_and_verify(self):
        p = fixture()
        s, pol = commitments(p)
        a = compile_artifacts(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        b = compile_artifacts(copy.deepcopy(p), expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        self.assertEqual(a, b)
        self.assertTrue(verify_artifacts(p, a, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL))
        receipt = json.loads(a["receipt.json"])
        self.assertEqual(len(receipt["manifest_sha256"]), 64)

    def test_source_and_network_writes_zero(self):
        p = fixture()
        s, pol = commitments(p)
        r = evaluate(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        self.assertEqual(r["authority"]["source_writes"], 0)
        self.assertEqual(r["authority"]["network_writes"], 0)
        for k, v in r["authority"].items():
            if k not in {"source_writes", "network_writes"}:
                self.assertFalse(v)

    def test_spec_defect_has_exact_record_id(self):
        p = fixture(); s, pol = commitments(p)
        r = evaluate(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        row = next(x for x in r["rows"] if x["record_id"] == "PACK-0019")
        self.assertIn("SPEC_REVISION_MISMATCH", row["codes"])
        self.assertEqual(row["source_sha256"], p["solution_packs"][19]["source_sha256"])

    def test_region_use_claim_defect(self):
        p = fixture(); s, pol = commitments(p)
        r = evaluate(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        self.assertIn("REGION_USE_CLAIM_MISMATCH", r["rows"][0]["codes"])

    def test_legacy_mapping_defect(self):
        p = fixture(); s, pol = commitments(p)
        r = evaluate(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        self.assertIn("LEGACY_MAPPING_MISMATCH", r["rows"][0]["codes"])

    def test_stability_defect(self):
        p = fixture(); s, pol = commitments(p)
        r = evaluate(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        self.assertIn("STABILITY_MISMATCH", r["rows"][15]["codes"])

    def test_owner_version_defect(self):
        p = fixture(); s, pol = commitments(p)
        r = evaluate(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        self.assertIn("OWNER_VERSION_MISMATCH", r["rows"][20]["codes"])

    def test_allergen_evidence_missing_holds(self):
        p = fixture(); p["solution_packs"][40]["allergen_evidence_sha256"] = ""
        s, pol = commitments(p)
        r = evaluate(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        row = next(x for x in r["rows"] if x["record_id"] == "PACK-0040")
        self.assertIn("ALLERGEN_EVIDENCE_MISSING", row["codes"])

    def test_label_evidence_missing_holds(self):
        p = fixture(); p["solution_packs"][41]["label_evidence_sha256"] = "bad"
        s, pol = commitments(p)
        r = evaluate(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        row = next(x for x in r["rows"] if x["record_id"] == "PACK-0041")
        self.assertIn("LABEL_EVIDENCE_MISSING", row["codes"])

    def test_snapshot_commitment_mismatch_holds_all(self):
        p = fixture(); _, pol = commitments(p)
        r = evaluate(p, expected_snapshot_sha256="0"*64, expected_policy_sha256=pol, evaluation_time=EVAL)
        self.assertEqual(r["summary"]["pass_count"], 0)
        self.assertIn("SNAPSHOT_COMMITMENT_MISMATCH", r["summary"]["global_holds"])

    def test_policy_commitment_mismatch_holds_all(self):
        p = fixture(); s, _ = commitments(p)
        r = evaluate(p, expected_snapshot_sha256=s, expected_policy_sha256="f"*64, evaluation_time=EVAL)
        self.assertEqual(r["summary"]["pass_count"], 0)
        self.assertIn("POLICY_COMMITMENT_MISMATCH", r["summary"]["global_holds"])

    def test_stale_snapshot_holds_all(self):
        p = fixture(); p["policy"]["max_snapshot_age_seconds"] = 1
        s, pol = commitments(p)
        r = evaluate(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        self.assertIn("STALE_SNAPSHOT", r["summary"]["global_holds"])

    def test_future_snapshot_holds_all(self):
        p = fixture(); p["snapshot"]["captured_at"] = "2026-09-13T15:00:00Z"
        s, pol = commitments(p)
        r = evaluate(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        self.assertIn("FUTURE_SNAPSHOT", r["summary"]["global_holds"])

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(GateError):
            strict_json_loads('{"x":1,"x":2}')

    def test_duplicate_record_id_rejected(self):
        p = fixture(); p["solution_packs"].append(copy.deepcopy(p["solution_packs"][50]))
        with self.assertRaises(GateError):
            normalize_packet(p)

    def test_pii_key_rejected(self):
        p = fixture(); p["solution_packs"][50]["email"] = "x@example.invalid"
        with self.assertRaises(GateError):
            normalize_packet(p)

    def test_tamper_result_fails_recompile(self):
        p = fixture(); s, pol = commitments(p)
        a = compile_artifacts(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        t = dict(a); t["result.json"] += b" "
        self.assertFalse(verify_artifacts(p, t, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL))

    def test_tamper_manifest_fails_recompile(self):
        p = fixture(); s, pol = commitments(p)
        a = compile_artifacts(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        t = dict(a); t["evidence_manifest.json"] += b" "
        self.assertFalse(verify_artifacts(p, t, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL))

    def test_exclusive_artifact_write(self):
        p = fixture(); s, pol = commitments(p)
        a = compile_artifacts(p, expected_snapshot_sha256=s, expected_policy_sha256=pol, evaluation_time=EVAL)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)/"bundle"
            write_artifacts_exclusive(out, a)
            self.assertEqual({x.name for x in out.iterdir()}, set(a))
            with self.assertRaises(FileExistsError):
                write_artifacts_exclusive(out, a)


if __name__ == "__main__":
    unittest.main(verbosity=2)
