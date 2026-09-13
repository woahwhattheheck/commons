from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from revenue.multi_framework_evidence_freshness.golden import GOLDEN_CORPUS_SHA256, build_golden_input, golden_corpus_sha256
from revenue.multi_framework_evidence_freshness.gate import (
    GateError,
    compile_packet,
    load_strict_json,
    render_markdown,
    verify_packet,
)

AS_OF = datetime(2026, 9, 13, 14, 0, 0, tzinfo=timezone.utc)


class FreshnessGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = build_golden_input()

    def test_golden_corpus_hash_is_pinned(self):
        self.assertEqual(golden_corpus_sha256(), GOLDEN_CORPUS_SHA256)

    def test_golden_400_exact_counts_and_trace(self):
        packet = compile_packet(self.raw, trusted_as_of=AS_OF)
        self.assertEqual(len(packet["results"]), 400)
        self.assertEqual(packet["counts"], {
            "REUSABLE": 240,
            "STALE": 50,
            "SCOPE_MISMATCH": 40,
            "MISSING_OWNER": 35,
            "INCOMPLETE": 35,
        })
        for row in packet["results"]:
            self.assertIn("source_ref", row["source_trace"])
            self.assertEqual(set(row["source_trace"]["fields"]), {
                "owner", "collection_time", "assessment_period_coverage",
                "framework_control_mapping", "checksum", "freshness_rule",
            })

    def test_zero_reusable_without_required_semantics(self):
        packet = compile_packet(self.raw, trusted_as_of=AS_OF)
        normalized = {r["evidence_id"]: r for r in packet["input"]["evidence"]}
        scope = {(r["framework"], r["control"]) for r in packet["input"]["assessment"]["scope"]}
        for result in packet["results"]:
            if result["state"] != "REUSABLE":
                continue
            row = normalized[result["evidence_id"]]
            self.assertTrue(row["owner_ref"] and row["checksum_sha256"] and row["source_ref"])
            self.assertTrue(row["mappings"])
            self.assertEqual(row["freshness_rule_id"], packet["input"]["freshness_policy"]["rule_id"])
            self.assertTrue({(m["framework"], m["control"]) for m in row["mappings"]}.issubset(scope))
            self.assertLessEqual(row["coverage_start"], packet["input"]["assessment"]["period_start"])
            self.assertGreaterEqual(row["coverage_end"], packet["input"]["assessment"]["period_end"])

    def test_three_run_hash_stability(self):
        packets = [compile_packet(copy.deepcopy(self.raw), trusted_as_of=AS_OF) for _ in range(3)]
        digests = [hashlib.sha256(json.dumps(p, sort_keys=True, separators=(",", ":")).encode()).hexdigest() for p in packets]
        self.assertEqual(len(set(digests)), 1)
        self.assertEqual(len({p["receipt_sha256"] for p in packets}), 1)

    def test_input_order_invariance(self):
        altered = copy.deepcopy(self.raw)
        altered["evidence"] = list(reversed(altered["evidence"]))
        altered["assessment"]["scope"] = list(reversed(altered["assessment"]["scope"]))
        self.assertEqual(
            compile_packet(self.raw, trusted_as_of=AS_OF),
            compile_packet(altered, trusted_as_of=AS_OF),
        )

    def test_missing_owner_precedence(self):
        raw = self._one("REUSE-000")
        raw["evidence"][0]["owner_ref"] = ""
        self.assertEqual(compile_packet(raw, trusted_as_of=AS_OF)["results"][0]["state"], "MISSING_OWNER")

    def test_missing_checksum_is_incomplete(self):
        raw = self._one("REUSE-000")
        raw["evidence"][0]["checksum_sha256"] = ""
        self.assertEqual(compile_packet(raw, trusted_as_of=AS_OF)["results"][0]["state"], "INCOMPLETE")

    def test_missing_mapping_is_incomplete(self):
        raw = self._one("REUSE-000")
        raw["evidence"][0]["mappings"] = []
        self.assertEqual(compile_packet(raw, trusted_as_of=AS_OF)["results"][0]["state"], "INCOMPLETE")

    def test_wrong_freshness_rule_is_incomplete(self):
        raw = self._one("REUSE-000")
        raw["evidence"][0]["freshness_rule_id"] = "freshness-v2"
        packet = compile_packet(raw, trusted_as_of=AS_OF)
        self.assertEqual(packet["results"][0]["state"], "INCOMPLETE")
        self.assertIn("FRESHNESS_RULE_MISMATCH", packet["results"][0]["reasons"])

    def test_scope_mapping_mismatch(self):
        raw = self._one("REUSE-000")
        raw["evidence"][0]["mappings"] = [{"framework": "SOC2", "control": "OUTSIDE"}]
        self.assertEqual(compile_packet(raw, trusted_as_of=AS_OF)["results"][0]["state"], "SCOPE_MISMATCH")

    def test_period_coverage_mismatch(self):
        raw = self._one("REUSE-000")
        raw["evidence"][0]["coverage_start"] = "2026-01-02T00:00:00Z"
        self.assertEqual(compile_packet(raw, trusted_as_of=AS_OF)["results"][0]["state"], "SCOPE_MISMATCH")

    def test_stale_boundary(self):
        raw = self._one("REUSE-000")
        raw["freshness_policy"]["max_age_days"] = 30
        raw["evidence"][0]["collected_at"] = "2026-08-14T14:00:00Z"
        self.assertEqual(compile_packet(raw, trusted_as_of=AS_OF)["results"][0]["state"], "REUSABLE")
        raw["evidence"][0]["collected_at"] = "2026-08-14T13:59:59Z"
        self.assertEqual(compile_packet(raw, trusted_as_of=AS_OF)["results"][0]["state"], "STALE")

    def test_future_collection_is_incomplete(self):
        raw = self._one("REUSE-000")
        raw["evidence"][0]["collected_at"] = "2026-09-13T14:00:01Z"
        packet = compile_packet(raw, trusted_as_of=AS_OF)
        self.assertEqual(packet["results"][0]["state"], "INCOMPLETE")
        self.assertIn("FUTURE_COLLECTION", packet["results"][0]["reasons"])

    def test_bool_max_age_rejected(self):
        raw = self._one("REUSE-000")
        raw["freshness_policy"]["max_age_days"] = True
        with self.assertRaises(GateError):
            compile_packet(raw, trusted_as_of=AS_OF)

    def test_unknown_key_rejected(self):
        raw = self._one("REUSE-000")
        raw["evidence"][0]["surprise"] = 1
        with self.assertRaises(GateError):
            compile_packet(raw, trusted_as_of=AS_OF)

    def test_duplicate_evidence_id_rejected(self):
        raw = self._one("REUSE-000")
        raw["evidence"].append(copy.deepcopy(raw["evidence"][0]))
        with self.assertRaises(GateError):
            compile_packet(raw, trusted_as_of=AS_OF)

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.json"
            p.write_text('{"schema":"a","schema":"b"}', encoding="utf-8")
            with self.assertRaises(GateError):
                load_strict_json(p)

    def test_nonfinite_json_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.json"
            p.write_text('{"x":NaN}', encoding="utf-8")
            with self.assertRaises(GateError):
                load_strict_json(p)

    def test_secret_shaped_ref_rejected(self):
        raw = self._one("REUSE-000")
        raw["evidence"][0]["source_ref"] = "token=abc"
        with self.assertRaises(GateError):
            compile_packet(raw, trusted_as_of=AS_OF)

    def test_receipt_tamper_rejected(self):
        packet = compile_packet(self.raw, trusted_as_of=AS_OF)
        bad = copy.deepcopy(packet)
        bad["counts"]["REUSABLE"] -= 1
        with self.assertRaises(GateError):
            verify_packet(bad)

    def test_markdown_tamper_commitment(self):
        packet = compile_packet(self.raw, trusted_as_of=AS_OF)
        md = render_markdown(packet)
        self.assertEqual(hashlib.sha256(md.encode()).hexdigest(), packet["markdown_sha256"])
        self.assertNotEqual(hashlib.sha256((md + "tamper").encode()).hexdigest(), packet["markdown_sha256"])

    def test_authority_is_all_false(self):
        packet = compile_packet(self.raw, trusted_as_of=AS_OF)
        self.assertTrue(packet["authority"])
        self.assertTrue(all(value is False for value in packet["authority"].values()))

    def test_verify_round_trip(self):
        self.assertTrue(verify_packet(compile_packet(self.raw, trusted_as_of=AS_OF)))

    def _one(self, evidence_id: str):
        raw = copy.deepcopy(self.raw)
        row = next(r for r in raw["evidence"] if r["evidence_id"] == evidence_id)
        raw["evidence"] = [copy.deepcopy(row)]
        return raw


if __name__ == "__main__":
    unittest.main()
