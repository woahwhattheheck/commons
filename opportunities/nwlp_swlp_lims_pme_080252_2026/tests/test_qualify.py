from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import qualify  # noqa: E402

NOW = datetime(2026, 9, 16, 22, 0, tzinfo=timezone.utc)
QBYTES = b"TEST-ONLY synthetic buyer questionnaire bytes\n"


def cb(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"


def source(acquired: bool = False, reviewed: bool = False) -> dict:
    qsha = hashlib.sha256(QBYTES).hexdigest() if acquired else None
    return {
        "schema_version": 1,
        "notice_id": qualify.NOTICE_ID,
        "ocid": qualify.OCID,
        "atamis_contract_reference": qualify.ATAMIS_REF,
        "estimated_value_gbp_ex_vat": 28000000,
        "checked_at": "2026-09-13T11:01:00Z",
        "response_deadline": "2026-10-01T12:00:00+01:00",
        "questionnaire": {
            "acquired": acquired,
            "reviewed": reviewed,
            "sha256": qsha,
            "state": (
                "QUESTIONNAIRE_ACQUIRED_REVIEWED"
                if acquired and reviewed
                else "QUESTIONNAIRE_ACQUIRED_UNREVIEWED"
                if acquired
                else "QUESTIONNAIRE_NOT_ACQUIRED"
            ),
        },
    }


def manifest(source_raw: bytes, route: str = "TEAMING_VALIDATION_EVIDENCE", *, proven: bool = False, caller_partner: bool = False) -> dict:
    caps = {}
    for gate in set().union(*[set(v) for v in qualify.ROUTES.values()]):
        caps[gate] = {
            "status": "PROVEN" if proven and gate in qualify.ROUTES[route] else "UNKNOWN",
            "evidence_refs": [f"ev:{gate}"] if proven and gate in qualify.ROUTES[route] else [],
        }
    return {
        "schema_version": 1,
        "notice_id": qualify.NOTICE_ID,
        "evaluated_at": "2026-07-01T00:00:00Z",
        "source_ledger_sha256": hashlib.sha256(source_raw).hexdigest(),
        "route": route,
        "partner_prime_confirmed": caller_partner,
        "authority": {key: False for key in qualify.FORBIDDEN_AUTHORITY_FLAGS},
        "capabilities": caps,
    }


def qauth(source_raw: bytes) -> dict:
    return {
        "schema_version": 1,
        "kind": "questionnaire_extraction",
        "notice_id": qualify.NOTICE_ID,
        "atamis_contract_reference": qualify.ATAMIS_REF,
        "source_ledger_sha256": hashlib.sha256(source_raw).hexdigest(),
        "questionnaire_sha256": hashlib.sha256(QBYTES).hexdigest(),
        "extraction_id": "extract:test:v1",
        "document_version": "test-v1",
        "extracted_at": "2026-09-15T12:00:00Z",
        "complete_addenda_set": True,
        "addenda": [{"id": "base-questionnaire", "sha256": hashlib.sha256(QBYTES).hexdigest()}],
        "required_gates_by_route": {route: list(gates) for route, gates in qualify.ROUTES.items()},
    }


def eauth(source_raw: bytes, qdigest: str) -> dict:
    claims = []
    for gate in sorted(set().union(*[set(v) for v in qualify.ROUTES.values()])):
        routes = [route for route, gates in qualify.ROUTES.items() if gate in gates]
        claims.append({
            "evidence_id": f"ev:{gate}",
            "capability": gate,
            "evidence_kind": "TEST_CERTIFICATE",
            "artifact_sha256": hashlib.sha256(gate.encode()).hexdigest(),
            "routes": routes,
        })
    return {
        "schema_version": 1,
        "kind": "capability_evidence",
        "notice_id": qualify.NOTICE_ID,
        "source_ledger_sha256": hashlib.sha256(source_raw).hexdigest(),
        "questionnaire_authority_sha256": qdigest,
        "generation": "evidence:test:v1",
        "issued_at": "2026-09-15T13:00:00Z",
        "valid_until": "2026-09-30T23:59:59Z",
        "claims": claims,
    }


def pauth(route: str, qdigest: str, generation: str = "evidence:test:v1") -> dict:
    return {
        "schema_version": 1,
        "kind": "partner_prime",
        "notice_id": qualify.NOTICE_ID,
        "atamis_contract_reference": qualify.ATAMIS_REF,
        "route": route,
        "qualified_prime": True,
        "partner_id": "partner:test:prime",
        "questionnaire_authority_sha256": qdigest,
        "evidence_generation": generation,
        "proof_sha256": hashlib.sha256(b"partner-proof").hexdigest(),
        "valid_from": "2026-09-15T00:00:00Z",
        "valid_until": "2026-09-30T23:59:59Z",
    }


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self._roots = (
            qualify.TRUSTED_QUESTIONNAIRE_AUTHORITY_SHA256,
            qualify.TRUSTED_EVIDENCE_AUTHORITY_SHA256,
            qualify.TRUSTED_PARTNER_AUTHORITY_SHA256,
        )

    def tearDown(self):
        (
            qualify.TRUSTED_QUESTIONNAIRE_AUTHORITY_SHA256,
            qualify.TRUSTED_EVIDENCE_AUTHORITY_SHA256,
            qualify.TRUSTED_PARTNER_AUTHORITY_SHA256,
        ) = self._roots

    def trusted_bundle(self, route="TEAMING_VALIDATION_EVIDENCE"):
        src = source(True, True)
        sraw = cb(src)
        man = manifest(sraw, route, proven=True, caller_partner=True)
        qa = cb(qauth(sraw))
        qualify.TRUSTED_QUESTIONNAIRE_AUTHORITY_SHA256 = frozenset({hashlib.sha256(qa).hexdigest()})
        ea_obj = eauth(sraw, hashlib.sha256(qa).hexdigest())
        ea = cb(ea_obj)
        qualify.TRUSTED_EVIDENCE_AUTHORITY_SHA256 = frozenset({hashlib.sha256(ea).hexdigest()})
        pa = None
        if route in qualify.TEAMING_ROUTES:
            pa = cb(pauth(route, hashlib.sha256(qa).hexdigest(), ea_obj["generation"]))
            qualify.TRUSTED_PARTNER_AUTHORITY_SHA256 = frozenset({hashlib.sha256(pa).hexdigest()})
        return src, sraw, man, qa, ea, pa

    def test_public_missing_questionnaire_holds_with_verifier_time(self):
        src = source()
        sraw = cb(src)
        result = qualify.evaluate(manifest(sraw), src, sraw, now=NOW)
        self.assertEqual(result.state, "HOLD_QUESTIONNAIRE_REQUIRED")
        self.assertEqual(result.payload["evaluated_at"], "2026-09-16T22:00:00Z")
        self.assertFalse(result.payload["buyer_submission_authorized"])

    def test_caller_backdating_cannot_hide_stale_source(self):
        src = source()
        src["checked_at"] = "2026-07-01T00:00:00Z"
        sraw = cb(src)
        man = manifest(sraw)
        man["evaluated_at"] = "2026-07-02T00:00:00Z"
        result = qualify.evaluate(man, src, sraw, now=NOW)
        self.assertEqual(result.state, "HOLD_SOURCE_STALE")
        self.assertGreater(result.payload["source_age_days"], 30)

    def test_deadline_is_verifier_owned_and_cannot_be_replayed(self):
        src = source()
        sraw = cb(src)
        man = manifest(sraw)
        man["evaluated_at"] = "2026-09-13T11:05:00Z"
        after_deadline = datetime(2026, 10, 1, 11, 0, 0, tzinfo=timezone.utc)
        result = qualify.evaluate(man, src, sraw, now=after_deadline)
        self.assertEqual(result.state, "HOLD_DEADLINE_PASSED")

    def test_current_ready_requires_independent_questionnaire_authority(self):
        src = source(True, True)
        sraw = cb(src)
        man = manifest(sraw, proven=True, caller_partner=True)
        result = qualify.evaluate(man, src, sraw, questionnaire_bytes=QBYTES, now=NOW)
        self.assertEqual(result.state, "HOLD_QUESTIONNAIRE_AUTHORITY_REQUIRED")

    def test_untrusted_authority_digest_is_invalid_input(self):
        src = source(True, True)
        sraw = cb(src)
        man = manifest(sraw, proven=True)
        with self.assertRaisesRegex(qualify.QualificationError, "UNTRUSTED_SHA256"):
            qualify.evaluate(man, src, sraw, questionnaire_bytes=QBYTES, questionnaire_authority_raw=cb(qauth(sraw)), now=NOW)

    def test_gate_universe_shrink_rejected(self):
        src = source(True, True)
        sraw = cb(src)
        man = manifest(sraw, proven=True)
        qa_obj = qauth(sraw)
        qa_obj["required_gates_by_route"]["TEAMING_VALIDATION_EVIDENCE"].pop()
        qa = cb(qa_obj)
        qualify.TRUSTED_QUESTIONNAIRE_AUTHORITY_SHA256 = frozenset({hashlib.sha256(qa).hexdigest()})
        with self.assertRaisesRegex(qualify.QualificationError, "GATE_UNIVERSE_SHRINK"):
            qualify.evaluate(man, src, sraw, questionnaire_bytes=QBYTES, questionnaire_authority_raw=qa, now=NOW)

    def test_addenda_incomplete_rejected(self):
        src = source(True, True)
        sraw = cb(src)
        man = manifest(sraw, proven=True)
        qa_obj = qauth(sraw)
        qa_obj["complete_addenda_set"] = False
        qa = cb(qa_obj)
        qualify.TRUSTED_QUESTIONNAIRE_AUTHORITY_SHA256 = frozenset({hashlib.sha256(qa).hexdigest()})
        with self.assertRaisesRegex(qualify.QualificationError, "ADDENDA_INCOMPLETE"):
            qualify.evaluate(man, src, sraw, questionnaire_bytes=QBYTES, questionnaire_authority_raw=qa, now=NOW)

    def test_generic_evidence_transplant_rejected(self):
        src, sraw, man, qa, ea, pa = self.trusted_bundle()
        first, second = qualify.ROUTES["TEAMING_VALIDATION_EVIDENCE"][:2]
        man["capabilities"][second]["evidence_refs"] = [f"ev:{first}"]
        with self.assertRaisesRegex(qualify.QualificationError, "EVIDENCE_CAPABILITY_MISMATCH"):
            qualify.evaluate(man, src, sraw, questionnaire_bytes=QBYTES, questionnaire_authority_raw=qa, evidence_authority_raw=ea, partner_authority_raw=pa, now=NOW)

    def test_partner_self_attestation_does_not_authorize(self):
        src, sraw, man, qa, ea, _ = self.trusted_bundle()
        man["partner_prime_confirmed"] = True
        result = qualify.evaluate(man, src, sraw, questionnaire_bytes=QBYTES, questionnaire_authority_raw=qa, evidence_authority_raw=ea, now=NOW)
        self.assertEqual(result.state, "HOLD_PARTNER_AUTHORITY_REQUIRED")
        self.assertFalse(result.payload["partner_prime_confirmed"])

    def test_partner_cross_route_replay_rejected(self):
        src, sraw, man, qa, ea, _ = self.trusted_bundle("TEAMING_VALIDATION_EVIDENCE")
        wrong = cb(pauth("TEAMING_INTEGRATION_SPECIALIST", hashlib.sha256(qa).hexdigest()))
        qualify.TRUSTED_PARTNER_AUTHORITY_SHA256 = frozenset({hashlib.sha256(wrong).hexdigest()})
        with self.assertRaisesRegex(qualify.QualificationError, "ROUTE_REPLAY"):
            qualify.evaluate(man, src, sraw, questionnaire_bytes=QBYTES, questionnaire_authority_raw=qa, evidence_authority_raw=ea, partner_authority_raw=wrong, now=NOW)

    def test_questionnaire_cross_opportunity_replay_rejected(self):
        src = source(True, True)
        sraw = cb(src)
        man = manifest(sraw, proven=True)
        qa_obj = qauth(sraw)
        qa_obj["notice_id"] = "OTHER-2026"
        qa = cb(qa_obj)
        qualify.TRUSTED_QUESTIONNAIRE_AUTHORITY_SHA256 = frozenset({hashlib.sha256(qa).hexdigest()})
        with self.assertRaisesRegex(qualify.QualificationError, "notice_id:MISMATCH"):
            qualify.evaluate(man, src, sraw, questionnaire_bytes=QBYTES, questionnaire_authority_raw=qa, now=NOW)

    def test_evidence_source_replay_rejected(self):
        src, sraw, man, qa, _, _ = self.trusted_bundle()
        ea_obj = eauth(sraw, hashlib.sha256(qa).hexdigest())
        ea_obj["source_ledger_sha256"] = "0" * 64
        ea = cb(ea_obj)
        qualify.TRUSTED_EVIDENCE_AUTHORITY_SHA256 = frozenset({hashlib.sha256(ea).hexdigest()})
        with self.assertRaisesRegex(qualify.QualificationError, "EVIDENCE_AUTHORITY_SOURCE_REPLAY"):
            qualify.evaluate(man, src, sraw, questionnaire_bytes=QBYTES, questionnaire_authority_raw=qa, evidence_authority_raw=ea, now=NOW)

    def test_fully_trusted_teaming_route_reaches_owner_review_only(self):
        src, sraw, man, qa, ea, pa = self.trusted_bundle()
        # Caller boolean is deliberately false: retained partner authority owns truth.
        man["partner_prime_confirmed"] = False
        result = qualify.evaluate(man, src, sraw, questionnaire_bytes=QBYTES, questionnaire_authority_raw=qa, evidence_authority_raw=ea, partner_authority_raw=pa, now=NOW)
        self.assertEqual(result.state, "READY_FOR_OWNER_MARKET_ENGAGEMENT_REVIEW")
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.payload["partner_prime_confirmed"])
        self.assertFalse(result.payload["caller_partner_prime_confirmed"])
        self.assertFalse(result.payload["buyer_submission_authorized"])
        self.assertEqual(result.payload["questionnaire_authority_sha256"], hashlib.sha256(qa).hexdigest())

    def test_expired_evidence_authority_rejected(self):
        src, sraw, man, qa, _, _ = self.trusted_bundle()
        ea_obj = eauth(sraw, hashlib.sha256(qa).hexdigest())
        ea_obj["valid_until"] = "2026-09-16T20:00:00Z"
        ea = cb(ea_obj)
        qualify.TRUSTED_EVIDENCE_AUTHORITY_SHA256 = frozenset({hashlib.sha256(ea).hexdigest()})
        with self.assertRaisesRegex(qualify.QualificationError, "EVIDENCE_AUTHORITY_EXPIRED"):
            qualify.evaluate(man, src, sraw, questionnaire_bytes=QBYTES, questionnaire_authority_raw=qa, evidence_authority_raw=ea, now=NOW)

    def test_historical_integrity_is_separate_and_never_ready(self):
        src = source()
        sraw = cb(src)
        result = qualify.historical_integrity(manifest(sraw), src, sraw)
        self.assertEqual(result.state, "HISTORICAL_INTEGRITY_VERIFIED")
        self.assertFalse(result.payload["commercial_readiness"])
        self.assertFalse(result.payload["buyer_submission_authorized"])

    def test_duplicate_json_and_bool_alias_still_rejected(self):
        with self.assertRaisesRegex(qualify.QualificationError, "DUPLICATE_JSON_KEY"):
            qualify.load_json_bytes(b'{"a":1,"a":2}', "dup")
        src = source()
        src["estimated_value_gbp_ex_vat"] = True
        sraw = cb(src)
        with self.assertRaisesRegex(qualify.QualificationError, "MUST_BE_INT_NOT_BOOL"):
            qualify.evaluate(manifest(sraw), src, sraw, now=NOW)

    def test_questionnaire_digest_mismatch_rejected(self):
        src = source(True, True)
        src["questionnaire"]["sha256"] = "a" * 64
        sraw = cb(src)
        with self.assertRaisesRegex(qualify.QualificationError, "QUESTIONNAIRE_DIGEST_MISMATCH"):
            qualify.evaluate(manifest(sraw), src, sraw, questionnaire_bytes=QBYTES, now=NOW)

    def test_acquired_questionnaire_requires_actual_bytes(self):
        src = source(True, True)
        sraw = cb(src)
        result = qualify.evaluate(manifest(sraw), src, sraw, now=NOW)
        self.assertEqual(result.state, "HOLD_QUESTIONNAIRE_FILE_REQUIRED")

    def test_unreviewed_questionnaire_holds_before_authority(self):
        src = source(True, False)
        sraw = cb(src)
        result = qualify.evaluate(manifest(sraw), src, sraw, questionnaire_bytes=QBYTES, now=NOW)
        self.assertEqual(result.state, "HOLD_QUESTIONNAIRE_REVIEW")

    def test_authority_escalation_still_rejected(self):
        src = source()
        sraw = cb(src)
        man = manifest(sraw)
        man["authority"]["questionnaire_submission"] = True
        with self.assertRaisesRegex(qualify.QualificationError, "AUTHORITY_ESCALATION_FORBIDDEN"):
            qualify.evaluate(man, src, sraw, now=NOW)

    def test_missing_gate_holds_even_with_trusted_authorities(self):
        src, sraw, man, qa, ea, pa = self.trusted_bundle()
        gate = qualify.ROUTES["TEAMING_VALIDATION_EVIDENCE"][0]
        man["capabilities"][gate] = {"status": "UNKNOWN", "evidence_refs": []}
        result = qualify.evaluate(man, src, sraw, questionnaire_bytes=QBYTES, questionnaire_authority_raw=qa, evidence_authority_raw=ea, partner_authority_raw=pa, now=NOW)
        self.assertEqual(result.state, "HOLD_EVIDENCE_GAPS")
        self.assertEqual(result.payload["missing_required_capabilities"][0]["gate"], gate)

    def test_source_checked_at_in_future_rejected(self):
        src = source()
        src["checked_at"] = "2026-09-17T00:00:00Z"
        sraw = cb(src)
        with self.assertRaisesRegex(qualify.QualificationError, "source.checked_at:IN_FUTURE"):
            qualify.evaluate(manifest(sraw), src, sraw, now=NOW)

    def test_evidence_cross_route_replay_rejected(self):
        src, sraw, man, qa, ea, pa = self.trusted_bundle()
        ea_obj = qualify.load_json_bytes(ea, "evidence")
        gate = qualify.ROUTES["TEAMING_VALIDATION_EVIDENCE"][0]
        for claim in ea_obj["claims"]:
            if claim["capability"] == gate:
                claim["routes"] = ["PRIME_LIMS"]
                break
        ea2 = cb(ea_obj)
        qualify.TRUSTED_EVIDENCE_AUTHORITY_SHA256 = frozenset({hashlib.sha256(ea2).hexdigest()})
        with self.assertRaisesRegex(qualify.QualificationError, "EVIDENCE_ROUTE_MISMATCH"):
            qualify.evaluate(man, src, sraw, questionnaire_bytes=QBYTES, questionnaire_authority_raw=qa, evidence_authority_raw=ea2, partner_authority_raw=pa, now=NOW)

    def test_questionnaire_authority_source_replay_rejected(self):
        src = source(True, True)
        sraw = cb(src)
        man = manifest(sraw, proven=True)
        qa_obj = qauth(sraw)
        qa_obj["source_ledger_sha256"] = "0" * 64
        qa = cb(qa_obj)
        qualify.TRUSTED_QUESTIONNAIRE_AUTHORITY_SHA256 = frozenset({hashlib.sha256(qa).hexdigest()})
        with self.assertRaisesRegex(qualify.QualificationError, "QUESTIONNAIRE_AUTHORITY_SOURCE_REPLAY"):
            qualify.evaluate(man, src, sraw, questionnaire_bytes=QBYTES, questionnaire_authority_raw=qa, now=NOW)

    def test_partner_expiration_rejected(self):
        src, sraw, man, qa, ea, _ = self.trusted_bundle()
        pa_obj = pauth("TEAMING_VALIDATION_EVIDENCE", hashlib.sha256(qa).hexdigest())
        pa_obj["valid_until"] = "2026-09-16T20:00:00Z"
        pa = cb(pa_obj)
        qualify.TRUSTED_PARTNER_AUTHORITY_SHA256 = frozenset({hashlib.sha256(pa).hexdigest()})
        with self.assertRaisesRegex(qualify.QualificationError, "PARTNER_AUTHORITY_OUTSIDE_VALIDITY"):
            qualify.evaluate(man, src, sraw, questionnaire_bytes=QBYTES, questionnaire_authority_raw=qa, evidence_authority_raw=ea, partner_authority_raw=pa, now=NOW)


if __name__ == "__main__":
    unittest.main()
