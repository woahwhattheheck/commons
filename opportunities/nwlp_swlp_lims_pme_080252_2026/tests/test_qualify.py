from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import qualify  # noqa: E402


def canonical_bytes(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"


def load_json(path: Path) -> dict:
    return qualify.load_json_bytes(path.read_bytes(), str(path))


class QualificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = load_json(ROOT / "sources.json")
        self.manifest = load_json(ROOT / "fixtures" / "public_hold.json")

    def run_case(self, source: dict | None = None, manifest: dict | None = None, qbytes: bytes | None = None):
        source = copy.deepcopy(source if source is not None else self.source)
        manifest = copy.deepcopy(manifest if manifest is not None else self.manifest)
        source_raw = canonical_bytes(source)
        manifest["source_ledger_sha256"] = hashlib.sha256(source_raw).hexdigest()
        result = qualify.evaluate(manifest, source, source_raw, questionnaire_bytes=qbytes)
        return result, result.bytes()

    def acquired_source(self, *, reviewed: bool = True, qbytes: bytes = b"TEST-ONLY synthetic questionnaire fixture\n"):
        source = copy.deepcopy(self.source)
        source["questionnaire"] = {
            "acquired": True,
            "reviewed": reviewed,
            "sha256": hashlib.sha256(qbytes).hexdigest(),
            "state": "QUESTIONNAIRE_ACQUIRED_REVIEWED" if reviewed else "QUESTIONNAIRE_ACQUIRED_UNREVIEWED",
        }
        return source, qbytes

    @staticmethod
    def proven_manifest(route: str) -> dict:
        required = qualify.ROUTES[route]
        return {
            "schema_version": 1,
            "notice_id": qualify.NOTICE_ID,
            "evaluated_at": "2026-09-13T11:05:00Z",
            "source_ledger_sha256": "0" * 64,
            "route": route,
            "partner_prime_confirmed": True,
            "authority": {key: False for key in qualify.FORBIDDEN_AUTHORITY_FLAGS},
            "capabilities": {
                gate: {"status": "PROVEN", "evidence_refs": [f"evidence:{gate}"]}
                for gate in required
            },
        }

    def test_public_fixture_holds_for_missing_questionnaire(self):
        result, _ = self.run_case()
        self.assertEqual(result.state, "HOLD_QUESTIONNAIRE_REQUIRED")
        self.assertEqual(result.exit_code, 3)
        self.assertFalse(result.payload["buyer_submission_authorized"])

    def test_public_fixture_is_byte_deterministic(self):
        result1, rendered1 = self.run_case()
        result2, rendered2 = self.run_case()
        self.assertEqual(result1, result2)
        self.assertEqual(rendered1, rendered2)

    def test_duplicate_top_level_key_rejected(self):
        raw = b'{"schema_version":1,"schema_version":1}\n'
        with self.assertRaisesRegex(qualify.QualificationError, "DUPLICATE_JSON_KEY"):
            qualify.load_json_bytes(raw, "dup.json")

    def test_duplicate_nested_key_rejected(self):
        raw = b'{"questionnaire":{"acquired":false,"acquired":true}}\n'
        with self.assertRaisesRegex(qualify.QualificationError, "DUPLICATE_JSON_KEY"):
            qualify.load_json_bytes(raw, "dup-nested.json")

    def test_bool_alias_for_integer_rejected(self):
        source = copy.deepcopy(self.source)
        source["estimated_value_gbp_ex_vat"] = True
        with self.assertRaisesRegex(qualify.QualificationError, "estimated_value_gbp_ex_vat"):
            self.run_case(source=source)

    def test_authority_escalation_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["authority"]["questionnaire_submission"] = True
        with self.assertRaisesRegex(qualify.QualificationError, "AUTHORITY_ESCALATION_FORBIDDEN"):
            self.run_case(manifest=manifest)

    def test_proven_capability_requires_evidence(self):
        manifest = copy.deepcopy(self.manifest)
        gate = next(iter(manifest["capabilities"]))
        manifest["capabilities"][gate] = {"status": "PROVEN", "evidence_refs": []}
        with self.assertRaisesRegex(qualify.QualificationError, "PROVEN_REQUIRES_EVIDENCE"):
            self.run_case(manifest=manifest)

    def test_questionnaire_digest_mismatch_rejected(self):
        source, qbytes = self.acquired_source(reviewed=True)
        source["questionnaire"]["sha256"] = "a" * 64
        manifest = self.proven_manifest("TEAMING_VALIDATION_EVIDENCE")
        with self.assertRaisesRegex(qualify.QualificationError, "QUESTIONNAIRE_DIGEST_MISMATCH"):
            self.run_case(source=source, manifest=manifest, qbytes=qbytes)

    def test_acquired_questionnaire_requires_actual_bytes(self):
        source, _ = self.acquired_source(reviewed=True)
        manifest = self.proven_manifest("TEAMING_VALIDATION_EVIDENCE")
        result, _ = self.run_case(source=source, manifest=manifest, qbytes=None)
        self.assertEqual(result.state, "HOLD_QUESTIONNAIRE_FILE_REQUIRED")
        self.assertEqual(result.exit_code, 3)

    def test_acquired_but_unreviewed_questionnaire_holds(self):
        source, qbytes = self.acquired_source(reviewed=False)
        manifest = self.proven_manifest("TEAMING_VALIDATION_EVIDENCE")
        result, _ = self.run_case(source=source, manifest=manifest, qbytes=qbytes)
        self.assertEqual(result.state, "HOLD_QUESTIONNAIRE_REVIEW")
        self.assertEqual(result.exit_code, 3)

    def test_missing_route_evidence_holds_after_questionnaire(self):
        source, qbytes = self.acquired_source(reviewed=True)
        manifest = copy.deepcopy(self.manifest)
        manifest["route"] = "PRIME_LIMS"
        manifest["partner_prime_confirmed"] = False
        manifest["capabilities"] = {
            gate: {"status": "UNKNOWN", "evidence_refs": []}
            for gate in qualify.ROUTES["PRIME_LIMS"]
        }
        result, _ = self.run_case(source=source, manifest=manifest, qbytes=qbytes)
        self.assertEqual(result.state, "HOLD_EVIDENCE_GAPS")
        self.assertGreater(len(result.payload["missing_required_capabilities"]), 0)

    def test_teaming_route_requires_confirmed_prime_partner(self):
        source, qbytes = self.acquired_source(reviewed=True)
        manifest = self.proven_manifest("TEAMING_INTEGRATION_SPECIALIST")
        manifest["partner_prime_confirmed"] = False
        result, _ = self.run_case(source=source, manifest=manifest, qbytes=qbytes)
        self.assertEqual(result.state, "HOLD_PARTNER_REQUIRED")
        self.assertEqual(result.exit_code, 3)

    def test_fully_evidenced_teaming_route_can_reach_owner_review_only(self):
        source, qbytes = self.acquired_source(reviewed=True)
        manifest = self.proven_manifest("TEAMING_VALIDATION_EVIDENCE")
        result, rendered = self.run_case(source=source, manifest=manifest, qbytes=qbytes)
        self.assertEqual(result.state, "READY_FOR_OWNER_MARKET_ENGAGEMENT_REVIEW")
        self.assertEqual(result.exit_code, 0)
        self.assertFalse(result.payload["buyer_submission_authorized"])
        self.assertIn(b'"buyer_submission_authorized":false', rendered)

    def test_stale_source_holds_even_with_questionnaire_and_evidence(self):
        source, qbytes = self.acquired_source(reviewed=True)
        source["checked_at"] = "2026-07-01T00:00:00+00:00"
        manifest = self.proven_manifest("TEAMING_VALIDATION_EVIDENCE")
        result, _ = self.run_case(source=source, manifest=manifest, qbytes=qbytes)
        self.assertEqual(result.state, "HOLD_SOURCE_STALE")
        self.assertEqual(result.exit_code, 3)


if __name__ == "__main__":
    unittest.main()
