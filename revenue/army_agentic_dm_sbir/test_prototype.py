from __future__ import annotations

import copy
import json
import unittest

from prototype import canonical_json, digest, evaluate


def evidence(eid, payload, *, status="ACTIVE", observed="2026-09-01T00:00:00Z", valid="2027-01-01T00:00:00Z"):
    return {
        "id": eid,
        "status": status,
        "source": f"synthetic://{eid}",
        "observed_at": observed,
        "valid_until": valid,
        "payload": payload,
        "payload_sha256": digest(payload),
    }


def fixture():
    return {
        "episode_id": "synthetic-ground-vehicle-power-thermal-v1",
        "generation": 1,
        "as_of": "2026-09-14T00:00:00Z",
        "objectives": ["Select a synthetic power/thermal architecture for demonstration only."],
        "assumptions": [{"id": "a1", "status": "ACCEPTED", "text": "Synthetic duty cycle remains representative."}],
        "risks": [{"id": "r1", "disposition": "MITIGATE", "text": "Supplier lead-time uncertainty."}],
        "bias_checks": [{"id": "b1", "status": "PASS", "text": "No option receives hidden incumbent preference."}],
        "evidence": [
            evidence("mass", {"unit": "kg", "source_class": "synthetic"}),
            evidence("thermal", {"unit": "normalized", "source_class": "synthetic"}),
            evidence("lead", {"unit": "days", "source_class": "synthetic"}),
        ],
        "criteria": [
            {"id": "mass", "weight_bps": 2500, "evidence_ids": ["mass"]},
            {"id": "thermal", "weight_bps": 5000, "evidence_ids": ["thermal"]},
            {"id": "lead", "weight_bps": 2500, "evidence_ids": ["lead"]},
        ],
        "options": [
            {"id": "architecture-a", "criterion_scores": {"mass": 8000, "thermal": 7600, "lead": 7000}},
            {"id": "architecture-b", "criterion_scores": {"mass": 6500, "thermal": 8600, "lead": 6000}},
        ],
    }


class PrototypeTests(unittest.TestCase):
    def test_canonicalization_is_order_invariant(self):
        a = {"b": 2, "a": {"y": 1, "x": 0}}
        b = {"a": {"x": 0, "y": 1}, "b": 2}
        self.assertEqual(canonical_json(a), canonical_json(b))
        self.assertEqual(digest(a), digest(b))

    def test_replay_receipt_is_stable(self):
        p = fixture()
        first = evaluate(p).as_dict()
        second = evaluate(json.loads(json.dumps(p))).as_dict()
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "DECISION_READY")

    def test_stale_evidence_fails_closed(self):
        p = fixture()
        p["evidence"][0]["valid_until"] = "2026-09-01T00:00:00Z"
        out = evaluate(p)
        self.assertEqual(out.status, "HOLD")
        self.assertIn("evidence_stale:mass", out.result["reasons"])

    def test_revoked_evidence_fails_closed(self):
        p = fixture()
        p["evidence"][1]["status"] = "REVOKED"
        out = evaluate(p)
        self.assertEqual(out.status, "HOLD")
        self.assertIn("evidence_not_active:thermal", out.result["reasons"])

    def test_evidence_payload_mutation_without_digest_update_fails(self):
        p = fixture()
        p["evidence"][0]["payload"]["unit"] = "lb"
        out = evaluate(p)
        self.assertEqual(out.status, "HOLD")
        self.assertIn("evidence_digest_mismatch:mass", out.result["reasons"])

    def test_missing_bias_check_fails_closed(self):
        p = fixture()
        p["bias_checks"] = []
        out = evaluate(p)
        self.assertEqual(out.status, "HOLD")
        self.assertIn("bias_checks_required", out.result["reasons"])

    def test_missing_score_fails_closed(self):
        p = fixture()
        del p["options"][0]["criterion_scores"]["lead"]
        out = evaluate(p)
        self.assertEqual(out.status, "HOLD")
        self.assertIn("invalid_or_missing_score:architecture-a:lead", out.result["reasons"])

    def test_post_evaluation_mutation_cannot_rewrite_old_receipt(self):
        p = fixture()
        before = evaluate(p)
        p["options"][0]["criterion_scores"]["thermal"] = 0
        after = evaluate(p)
        self.assertNotEqual(before.input_sha256, after.input_sha256)
        self.assertNotEqual(before.receipt_sha256, after.receipt_sha256)

    def test_what_flips_is_mechanical_and_nonempty(self):
        out = evaluate(fixture())
        self.assertEqual(out.status, "DECISION_READY")
        flips = out.result["what_flips"]
        self.assertTrue(flips)
        self.assertTrue(all("criterion_id" in row for row in flips if row["kind"] != "tie_break"))

    def test_float_authority_is_rejected(self):
        p = fixture()
        p["options"][0]["criterion_scores"]["mass"] = 1.5
        with self.assertRaisesRegex(ValueError, "floats_forbidden"):
            evaluate(p)

    def test_refresh_is_new_generation_not_history_rewrite(self):
        p1 = fixture()
        r1 = evaluate(p1)
        p2 = copy.deepcopy(p1)
        p2["generation"] = 2
        p2["evidence"][2] = evidence("lead", {"unit": "days", "source_class": "synthetic", "refresh": 2})
        p2["options"][1]["criterion_scores"]["lead"] = 9000
        r2 = evaluate(p2)
        self.assertEqual(r1.status, "DECISION_READY")
        self.assertEqual(r2.status, "DECISION_READY")
        self.assertNotEqual(r1.receipt_sha256, r2.receipt_sha256)
        self.assertEqual(r1.result["generation"], 1)
        self.assertEqual(r2.result["generation"], 2)


if __name__ == "__main__":
    unittest.main()
