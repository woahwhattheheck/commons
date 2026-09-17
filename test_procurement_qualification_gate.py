from __future__ import annotations

import copy
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from revenue.procurement_qualification_gate import engine


HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "revenue" / "procurement_qualification_gate" / "municipal_lims_like_replay.json"


def proof(state: str = "PROVEN", ref: str = "evidence://proof") -> dict[str, str]:
    return {"state": state, "evidence_ref": ref if state != "NOT_REQUIRED" else ""}


def ready_document() -> dict:
    return {
        "schema": engine.SCHEMA,
        "evaluation_at": "2026-09-17T09:00:00Z",
        "max_source_age_hours": 48,
        "opportunity": {
            "opportunity_id": "READY-001",
            "buyer": "Example public buyer",
            "scope_label": "Evidence-bound software implementation",
            "pursuit_open": True,
            "deadline_at": "2026-10-01T20:00:00Z",
            "source_kind": "CONTROLLING_PACKET",
            "source_observed_at": "2026-09-17T08:00:00Z",
            "source_ref": "buyer://packet",
            "source_sha256": "a" * 64,
            "controlling_packet_available": True,
        },
        "mandatory_requirements": [
            {
                "requirement_id": "REGISTRATION",
                "description": "Prime registration",
                "applies_to_prime": True,
                "applies_to_workshare": False,
                "state": "PROVEN",
                "evidence_ref": "buyer://packet#registration",
            },
            {
                "requirement_id": "SPECIALIST_SCOPE",
                "description": "Specialist delivery qualification",
                "applies_to_prime": False,
                "applies_to_workshare": True,
                "state": "PROVEN",
                "evidence_ref": "evidence://specialist",
            },
        ],
        "prime_readiness": {name: proof() for name in engine.PRIME_GATES},
        "workshare_readiness": {name: proof() for name in engine.WORKSHARE_GATES},
        "economics": {
            "proposed_workshare_value_cents": 2_000_000,
            "minimum_workshare_value_cents": 500_000,
            "estimated_pursuit_cost_cents": 100_000,
            "pursuit_cost_cap_cents": 250_000,
        },
    }


class ProcurementQualificationGateTests(unittest.TestCase):
    def test_prime_ready_requires_every_prime_gate(self) -> None:
        result = engine.compile_assessment(ready_document())
        self.assertEqual(result["decision"], "PRIME_READY")
        self.assertTrue(result["prime"]["eligible"])
        self.assertTrue(result["workshare"]["eligible"])
        self.assertFalse(any(result["authority"].values()))
        self.assertTrue(result["economics"]["workshare_value_meets_floor"])
        self.assertTrue(result["economics"]["pursuit_cost_within_cap"])

    def test_missing_prime_evidence_routes_to_paid_workshare(self) -> None:
        doc = ready_document()
        doc["prime_readiness"]["past_performance"] = proof("UNPROVEN", "")
        result = engine.compile_assessment(doc)
        self.assertEqual(result["decision"], "WORKSHARE_ONLY")
        self.assertFalse(result["prime"]["eligible"])
        self.assertTrue(result["workshare"]["eligible"])
        self.assertIn("PRIME_PAST_PERFORMANCE_UNPROVEN", result["prime"]["blockers"])
        self.assertIn(
            "TARGET_QUALIFIED_PRIME_NOT_BUYER_AS_DIRECT_PRIME",
            result["next_actions"],
        )

    def test_missing_controlling_packet_blocks_prime_not_workshare(self) -> None:
        doc = ready_document()
        doc["opportunity"]["source_kind"] = "OFFICIAL_NOTICE"
        doc["opportunity"]["controlling_packet_available"] = False
        result = engine.compile_assessment(doc)
        self.assertEqual(result["decision"], "WORKSHARE_ONLY")
        self.assertIn("CONTROLLING_PACKET_NOT_AVAILABLE", result["prime"]["blockers"])

    def test_expired_opportunity_is_no_bid(self) -> None:
        doc = ready_document()
        doc["opportunity"]["deadline_at"] = "2026-09-16T20:00:00Z"
        result = engine.compile_assessment(doc)
        self.assertEqual(result["decision"], "NO_BID")
        self.assertFalse(result["prime"]["eligible"])
        self.assertFalse(result["workshare"]["eligible"])
        self.assertIn("DEADLINE_PASSED", result["prime"]["blockers"])

    def test_failed_workshare_requirement_does_not_poison_prime_route(self) -> None:
        doc = ready_document()
        doc["mandatory_requirements"][1]["state"] = "FAILED"
        doc["mandatory_requirements"][1]["evidence_ref"] = "buyer://failure"
        result = engine.compile_assessment(doc)
        self.assertEqual(result["decision"], "PRIME_READY")
        self.assertTrue(result["prime"]["eligible"])
        self.assertFalse(result["workshare"]["eligible"])

    def test_failed_workshare_requirement_is_no_bid_when_prime_is_not_ready(self) -> None:
        doc = ready_document()
        doc["prime_readiness"]["past_performance"] = proof("UNPROVEN", "")
        doc["mandatory_requirements"][1]["state"] = "FAILED"
        doc["mandatory_requirements"][1]["evidence_ref"] = "buyer://failure"
        result = engine.compile_assessment(doc)
        self.assertEqual(result["decision"], "NO_BID")
        self.assertFalse(result["prime"]["eligible"])
        self.assertFalse(result["workshare"]["eligible"])

    def test_economics_floor_and_cost_cap_fail_closed(self) -> None:
        low = ready_document()
        low["prime_readiness"]["past_performance"] = proof("UNPROVEN", "")
        low["economics"]["proposed_workshare_value_cents"] = 499_999
        result = engine.compile_assessment(low)
        self.assertEqual(result["decision"], "NO_BID")
        self.assertIn("WORKSHARE_VALUE_BELOW_FLOOR", result["workshare"]["blockers"])
        self.assertIn("PRIME_PAST_PERFORMANCE_UNPROVEN", result["prime"]["blockers"])

        costly = ready_document()
        costly["economics"]["estimated_pursuit_cost_cents"] = 250_001
        result = engine.compile_assessment(costly)
        self.assertEqual(result["decision"], "NO_BID")
        self.assertIn("PURSUIT_COST_EXCEEDS_CAP", result["prime"]["blockers"])

    def test_stale_source_requires_refresh_and_blocks_external_posture(self) -> None:
        doc = ready_document()
        doc["max_source_age_hours"] = 1
        doc["opportunity"]["source_observed_at"] = "2026-09-16T08:00:00Z"
        result = engine.compile_assessment(doc)
        self.assertEqual(result["decision"], "NO_BID")
        self.assertIn("SOURCE_STALE", result["prime"]["blockers"])
        self.assertIn("SOURCE_STALE_REFRESH_REQUIRED", result["workshare"]["blockers"])

    def test_proven_state_requires_evidence(self) -> None:
        doc = ready_document()
        doc["prime_readiness"]["security_assurance"]["evidence_ref"] = ""
        with self.assertRaisesRegex(engine.QualificationError, "PROVEN requires evidence_ref"):
            engine.compile_assessment(doc)

    def test_controlling_packet_claim_requires_controlling_source(self) -> None:
        doc = ready_document()
        doc["opportunity"]["source_kind"] = "OFFICIAL_NOTICE"
        with self.assertRaisesRegex(engine.QualificationError, "requires CONTROLLING_PACKET"):
            engine.compile_assessment(doc)

    def test_future_source_rejected(self) -> None:
        doc = ready_document()
        doc["opportunity"]["source_observed_at"] = "2026-09-18T08:00:00Z"
        with self.assertRaisesRegex(engine.QualificationError, "future evidence"):
            engine.compile_assessment(doc)

    def test_duplicate_requirement_id_rejected(self) -> None:
        doc = ready_document()
        doc["mandatory_requirements"].append(copy.deepcopy(doc["mandatory_requirements"][0]))
        with self.assertRaisesRegex(engine.QualificationError, "duplicate mandatory requirement_id"):
            engine.compile_assessment(doc)

    def test_bundle_is_deterministic_and_tamper_evident(self) -> None:
        doc = ready_document()
        first = engine.compile_bundle(doc)
        second = engine.compile_bundle(copy.deepcopy(doc))
        self.assertEqual(first, second)
        self.assertTrue(engine.verify_bundle(first))
        tampered = copy.deepcopy(first)
        tampered["assessment"]["decision"] = "NO_BID"
        self.assertFalse(engine.verify_bundle(tampered))

    def test_strict_json_rejects_duplicate_keys_floats_and_nonfinite(self) -> None:
        with self.assertRaisesRegex(engine.QualificationError, "duplicate JSON key"):
            engine.load_json_strict(io.StringIO('{"x":1,"x":2}'))
        with self.assertRaisesRegex(engine.QualificationError, "floating JSON number"):
            engine.load_json_strict(io.StringIO('{"x":1.5}'))
        with self.assertRaisesRegex(engine.QualificationError, "non-finite JSON constant"):
            engine.load_json_strict(io.StringIO('{"x":NaN}'))

    def test_historical_source_digest_is_exact(self) -> None:
        doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
        source = (
            HERE
            / "revenue"
            / "procurement_qualification_gate"
            / "municipal_lims_like_source.txt"
        ).read_bytes()
        import hashlib

        self.assertEqual(
            hashlib.sha256(source).hexdigest(),
            doc["opportunity"]["source_sha256"],
        )

    def test_historical_municipal_lims_like_replay_is_workshare_only(self) -> None:
        doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
        result = engine.compile_assessment(doc)
        self.assertEqual(result["decision"], "WORKSHARE_ONLY")
        self.assertFalse(result["prime"]["eligible"])
        self.assertTrue(result["workshare"]["eligible"])
        self.assertIn(
            "MANDATORY_RETAINED_REFERENCE_3Y_FAILED",
            result["prime"]["blockers"],
        )
        self.assertEqual(
            result["truth_boundary"],
            "INTERNAL_PURSUIT_POSTURE_ONLY_NOT_BUYER_SCORING_NOT_WIN_PROBABILITY",
        )

    def test_optimized_mode_matches_semantics(self) -> None:
        script = (
            "import json, pathlib;"
            "from revenue.procurement_qualification_gate import engine;"
            "p=pathlib.Path('revenue/procurement_qualification_gate/municipal_lims_like_replay.json');"
            "d=json.loads(p.read_text());"
            "print(engine.compile_bundle(d)['assessment']['decision'])"
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = str(HERE)
        normal = subprocess.run(
            [sys.executable, "-c", script],
            cwd=HERE,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        optimized = subprocess.run(
            [sys.executable, "-O", "-c", script],
            cwd=HERE,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(normal.stdout, optimized.stdout)
        self.assertEqual(normal.stdout.strip(), "WORKSHARE_ONLY")


if __name__ == "__main__":
    unittest.main()
