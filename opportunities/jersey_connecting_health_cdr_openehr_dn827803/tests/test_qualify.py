from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import qualify

NOW = "2026-09-13T12:00:00Z"
PACK = b"TEST-ONLY synthetic buyer tender package\n"
PACK_SHA = hashlib.sha256(PACK).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def public_source():
    return {
        "schema_version": 1,
        "operation_id": "JERSEY-CDR-OPENEHR-DN827803-ZVHJ7P4-20260913",
        "notice_id": qualify.NOTICE_ID,
        "buyer": "Government / States of Jersey",
        "programme": "Connecting Health - Clinical Data Repository (CDR) and openEHR",
        "checked_at": "2026-09-13T11:15:00Z",
        "response_deadline": "2026-09-29T22:30:00Z",
        "response_deadline_basis": "public notice; trust root required before commercial authority",
        "tender_pack": {
            "acquired": False,
            "reviewed": False,
            "sha256": None,
            "state": "TENDER_PACK_NOT_ACQUIRED",
        },
        "sources": [],
        "public_scope_facts": [],
    }


def acquired_source(*, checked_at="2026-09-13T11:15:00Z", deadline="2026-09-29T22:30:00Z", reviewed=True):
    source = public_source()
    source["checked_at"] = checked_at
    source["response_deadline"] = deadline
    source["tender_pack"] = {
        "acquired": True,
        "reviewed": reviewed,
        "sha256": PACK_SHA,
        "state": "TENDER_PACK_ACQUIRED_REVIEWED" if reviewed else "TENDER_PACK_ACQUIRED_UNREVIEWED",
    }
    return source


def base_manifest(source_raw, route="PRIME_CDR"):
    return {
        "schema_version": 1,
        "notice_id": qualify.NOTICE_ID,
        "evaluated_at": "2026-09-13T11:20:00Z",
        "source_ledger_sha256": hashlib.sha256(source_raw).hexdigest(),
        "route": route,
        "partner_prime_confirmed": False,
        "authority": {key: False for key in qualify.AUTHORITY_FLAGS},
        "capabilities": {},
    }


def evidence(claim, idx, *, subject):
    return {
        "evidence_id": f"ev:{idx}:{claim}",
        "claim_id": claim,
        "subject": subject,
        "source_sha256": hashlib.sha256(f"source:{claim}:{idx}".encode()).hexdigest(),
        "source_ref": f"https://evidence.example.test/{idx}/{claim}",
        "statement_sha256": hashlib.sha256(f"statement:{claim}:{idx}".encode()).hexdigest(),
    }


def build_trust(source, source_raw, route, *, include_all=True, complete=True, addenda="2026-09-13T11:45:00Z", extracted="2026-09-13T11:30:00Z"):
    subject = "PRIME" if route == "PRIME_CDR" else "PARTNER"
    buyer_sources = [{
        "source_id": "tender-pack",
        "kind": "TENDER_PACK",
        "sha256": PACK_SHA,
    }]
    requirements = []
    approved = []
    claims = list(qualify.ROUTES[route])
    if not include_all:
        claims = claims[:-1]
    for i, claim in enumerate(claims):
        requirements.append({
            "requirement_id": f"req:{claim}",
            "claim_id": claim,
            "mandatory": True,
            "routes": [route],
            "cure": "NONE",
            "buyer_source_id": "tender-pack",
            "buyer_source_sha256": PACK_SHA,
            "description_sha256": hashlib.sha256(f"requirement:{claim}".encode()).hexdigest(),
        })
        approved.append(evidence(claim, i, subject=subject))
    if route in qualify.TEAMING_ROUTES:
        approved.append(evidence("partner_prime_confirmation", 999, subject="PARTNER"))
    buyer_sources.sort(key=lambda x: x["source_id"])
    requirements.sort(key=lambda x: x["requirement_id"])
    approved.sort(key=lambda x: x["evidence_id"])
    trust = {
        "contract": qualify.TRUST_CONTRACT,
        "schema_version": qualify.TRUST_SCHEMA_VERSION,
        "notice_id": qualify.NOTICE_ID,
        "source_ledger_sha256": hashlib.sha256(source_raw).hexdigest(),
        "tender_pack_sha256": PACK_SHA,
        "extracted_at": extracted,
        "addenda_checked_through": addenda,
        "response_deadline": source["response_deadline"],
        "deadline_source_id": "tender-pack",
        "complete": complete,
        "buyer_sources": buyer_sources,
        "buyer_source_set_sha256": qualify.digest_object(buyer_sources),
        "requirements": requirements,
        "requirement_set_sha256": qualify.digest_object(requirements),
        "approved_evidence": approved,
        "evidence_set_sha256": qualify.digest_object(approved),
    }
    normalized = qualify.normalize_trusted_qualification(trust, trusted_as_of=NOW)
    return trust, qualify.digest_object(normalized)


def proven_manifest(source_raw, route, trust):
    m = base_manifest(source_raw, route)
    approved = {row["claim_id"]: row["evidence_id"] for row in trust["approved_evidence"]}
    m["capabilities"] = {
        claim: {"status": "PROVEN", "evidence_refs": [approved.get(claim, f"ev:uncommitted:{claim}")]}
        for claim in qualify.ROUTES[route]
    }
    if route in qualify.TEAMING_ROUTES:
        m["partner_prime_confirmed"] = True
        m["capabilities"]["partner_prime_confirmation"] = {
            "status": "PROVEN",
            "evidence_refs": [approved["partner_prime_confirmation"]],
        }
    return m


class JerseyAuthorityV2Tests(unittest.TestCase):
    def evaluate_ready(self, route="PRIME_CDR", now=NOW, *, source=None):
        source = copy.deepcopy(source or acquired_source())
        source_raw = canonical(source)
        trust, root = build_trust(source, source_raw, route)
        manifest = proven_manifest(source_raw, route, trust)
        return qualify.evaluate(
            manifest,
            source,
            source_raw,
            trusted_as_of=now,
            tender_pack_bytes=PACK,
            trusted_qualification=trust,
            trusted_qualification_sha256=root,
        ), source, source_raw, manifest, trust, root

    def test_public_fixture_stays_hold_without_trust(self):
        source = public_source()
        raw = canonical(source)
        manifest = base_manifest(raw, "TEAMING_ACCEPTANCE_EVIDENCE")
        result = qualify.evaluate(manifest, source, raw, trusted_as_of=NOW)
        self.assertEqual(result.state, "HOLD_TENDER_PACK_REQUIRED")
        self.assertFalse(result.payload["tender_submission_authorized"])
        self.assertTrue(qualify.verify_receipt_integrity(result.payload))

    def test_ready_prime_requires_retained_trust_and_approved_evidence(self):
        result, *_ = self.evaluate_ready()
        self.assertEqual(result.state, "READY_FOR_OWNER_TENDER_REVIEW")
        self.assertEqual(result.exit_code, 0)
        self.assertFalse(result.payload["tender_submission_authorized"])

    def test_ready_team_requires_partner_confirmation_evidence(self):
        result, *_ = self.evaluate_ready("TEAMING_ACCEPTANCE_EVIDENCE")
        self.assertEqual(result.state, "READY_FOR_OWNER_TENDER_REVIEW")

    def test_synthetic_reviewed_pack_without_trust_cannot_ready(self):
        source = acquired_source()
        raw = canonical(source)
        manifest = base_manifest(raw)
        manifest["capabilities"] = {
            claim: {"status": "PROVEN", "evidence_refs": [f"evidence:{claim}"]}
            for claim in qualify.ROUTES["PRIME_CDR"]
        }
        result = qualify.evaluate(manifest, source, raw, trusted_as_of=NOW, tender_pack_bytes=PACK)
        self.assertEqual(result.state, "HOLD_TRUSTED_QUALIFICATION_REQUIRED")

    def test_arbitrary_evidence_strings_do_not_satisfy_trusted_claims(self):
        _, source, raw, manifest, trust, root = self.evaluate_ready()
        first = qualify.ROUTES["PRIME_CDR"][0]
        manifest["capabilities"][first]["evidence_refs"] = ["evidence:invented"]
        result = qualify.evaluate(
            manifest, source, raw, trusted_as_of=NOW, tender_pack_bytes=PACK,
            trusted_qualification=trust, trusted_qualification_sha256=root,
        )
        self.assertEqual(result.state, "HOLD_EVIDENCE_GAPS")
        self.assertIn({"gate": first, "status": "UNAPPROVED_EVIDENCE"}, result.payload["missing_required_capabilities"])

    def test_cross_claim_evidence_reuse_does_not_satisfy_other_gate(self):
        _, source, raw, manifest, trust, root = self.evaluate_ready()
        claims = qualify.ROUTES["PRIME_CDR"]
        manifest["capabilities"][claims[1]]["evidence_refs"] = manifest["capabilities"][claims[0]]["evidence_refs"][:]
        result = qualify.evaluate(
            manifest, source, raw, trusted_as_of=NOW, tender_pack_bytes=PACK,
            trusted_qualification=trust, trusted_qualification_sha256=root,
        )
        self.assertEqual(result.state, "HOLD_EVIDENCE_GAPS")
        self.assertIn({"gate": claims[1], "status": "UNAPPROVED_EVIDENCE"}, result.payload["missing_required_capabilities"])

    def test_removed_mandatory_gate_cannot_replace_retained_root(self):
        _, source, raw, manifest, trust, root = self.evaluate_ready()
        trust["requirements"] = trust["requirements"][:-1]
        trust["requirement_set_sha256"] = qualify.digest_object(trust["requirements"])
        with self.assertRaisesRegex(qualify.QualificationError, "TRUST_ROOT_MISMATCH"):
            qualify.evaluate(
                manifest, source, raw, trusted_as_of=NOW, tender_pack_bytes=PACK,
                trusted_qualification=trust, trusted_qualification_sha256=root,
            )

    def test_incomplete_strategic_floor_holds_even_with_new_valid_root(self):
        source = acquired_source()
        raw = canonical(source)
        trust, root = build_trust(source, raw, "PRIME_CDR", include_all=False)
        manifest = proven_manifest(raw, "PRIME_CDR", trust)
        result = qualify.evaluate(
            manifest, source, raw, trusted_as_of=NOW, tender_pack_bytes=PACK,
            trusted_qualification=trust, trusted_qualification_sha256=root,
        )
        self.assertEqual(result.state, "HOLD_EVIDENCE_GAPS")
        self.assertTrue(any(row["status"] == "UNCOMMITTED_REQUIRED_CLAIM" for row in result.payload["missing_required_capabilities"]))

    def test_flip_requirement_semantics_breaks_retained_root(self):
        _, source, raw, manifest, trust, root = self.evaluate_ready()
        trust["requirements"][0]["mandatory"] = False
        trust["requirement_set_sha256"] = qualify.digest_object(trust["requirements"])
        with self.assertRaisesRegex(qualify.QualificationError, "TRUST_ROOT_MISMATCH"):
            qualify.evaluate(
                manifest, source, raw, trusted_as_of=NOW, tender_pack_bytes=PACK,
                trusted_qualification=trust, trusted_qualification_sha256=root,
            )

    def test_rewrite_source_ledger_and_recompute_self_hash_does_not_replace_retained_root(self):
        _, source, raw, manifest, trust, root = self.evaluate_ready()
        source["buyer"] = "Attacker rewritten ledger"
        attack_raw = canonical(source)
        manifest["source_ledger_sha256"] = hashlib.sha256(attack_raw).hexdigest()
        trust["source_ledger_sha256"] = hashlib.sha256(attack_raw).hexdigest()
        with self.assertRaisesRegex(qualify.QualificationError, "TRUST_ROOT_MISMATCH"):
            qualify.evaluate(
                manifest, source, attack_raw, trusted_as_of=NOW, tender_pack_bytes=PACK,
                trusted_qualification=trust, trusted_qualification_sha256=root,
            )

    def test_forged_deadline_cannot_replace_retained_root(self):
        _, source, _, manifest, trust, root = self.evaluate_ready()
        source["response_deadline"] = "2026-09-13T11:59:00Z"
        attack_raw = canonical(source)
        manifest["source_ledger_sha256"] = hashlib.sha256(attack_raw).hexdigest()
        trust["source_ledger_sha256"] = hashlib.sha256(attack_raw).hexdigest()
        trust["response_deadline"] = source["response_deadline"]
        with self.assertRaisesRegex(qualify.QualificationError, "TRUST_ROOT_MISMATCH"):
            qualify.evaluate(
                manifest, source, attack_raw, trusted_as_of=NOW, tender_pack_bytes=PACK,
                trusted_qualification=trust, trusted_qualification_sha256=root,
            )

    def test_trusted_deadline_closes_at_current_time(self):
        source = acquired_source(deadline="2026-09-13T11:59:00Z")
        raw = canonical(source)
        trust, root = build_trust(source, raw, "PRIME_CDR")
        manifest = proven_manifest(raw, "PRIME_CDR", trust)
        result = qualify.evaluate(
            manifest, source, raw, trusted_as_of=NOW, tender_pack_bytes=PACK,
            trusted_qualification=trust, trusted_qualification_sha256=root,
        )
        self.assertEqual(result.state, "NO_BID_DEADLINE_CLOSED")
        self.assertEqual(result.exit_code, 4)

    def test_historical_manifest_time_cannot_beat_trusted_current_deadline(self):
        source = acquired_source(deadline="2026-09-13T11:59:00Z")
        raw = canonical(source)
        trust, root = build_trust(source, raw, "PRIME_CDR")
        manifest = proven_manifest(raw, "PRIME_CDR", trust)
        manifest["evaluated_at"] = "2026-09-13T11:30:00Z"
        result = qualify.evaluate(
            manifest, source, raw, trusted_as_of=NOW, tender_pack_bytes=PACK,
            trusted_qualification=trust, trusted_qualification_sha256=root,
        )
        self.assertEqual(result.state, "NO_BID_DEADLINE_CLOSED")

    def test_stale_addenda_inventory_holds(self):
        source = acquired_source()
        raw = canonical(source)
        trust, root = build_trust(
            source, raw, "PRIME_CDR",
            addenda="2026-09-11T11:00:00Z",
            extracted="2026-09-11T10:00:00Z",
        )
        manifest = proven_manifest(raw, "PRIME_CDR", trust)
        result = qualify.evaluate(
            manifest, source, raw, trusted_as_of=NOW, tender_pack_bytes=PACK,
            trusted_qualification=trust, trusted_qualification_sha256=root,
        )
        self.assertEqual(result.state, "HOLD_ADDENDA_INVENTORY_STALE")

    def test_incomplete_extraction_holds(self):
        source = acquired_source()
        raw = canonical(source)
        trust, root = build_trust(source, raw, "PRIME_CDR", complete=False)
        manifest = proven_manifest(raw, "PRIME_CDR", trust)
        result = qualify.evaluate(
            manifest, source, raw, trusted_as_of=NOW, tender_pack_bytes=PACK,
            trusted_qualification=trust, trusted_qualification_sha256=root,
        )
        self.assertEqual(result.state, "HOLD_REQUIREMENT_UNIVERSE_UNVERIFIED")

    def test_future_source_check_rejected(self):
        source = acquired_source(checked_at="2026-09-14T00:00:00Z")
        raw = canonical(source)
        manifest = base_manifest(raw)
        with self.assertRaisesRegex(qualify.QualificationError, "AFTER_TRUSTED_TIME"):
            qualify.evaluate(manifest, source, raw, trusted_as_of=NOW, tender_pack_bytes=PACK)

    def test_future_addenda_check_rejected(self):
        source = acquired_source()
        raw = canonical(source)
        trust, _ = build_trust(source, raw, "PRIME_CDR")
        trust["addenda_checked_through"] = "2026-09-14T00:00:00Z"
        root = qualify.digest_object(trust)
        manifest = proven_manifest(raw, "PRIME_CDR", trust)
        with self.assertRaisesRegex(qualify.QualificationError, "AFTER_TRUSTED_TIME"):
            qualify.evaluate(
                manifest, source, raw, trusted_as_of=NOW, tender_pack_bytes=PACK,
                trusted_qualification=trust, trusted_qualification_sha256=root,
            )

    def test_current_verifier_detects_aging(self):
        result, source, raw, manifest, trust, root = self.evaluate_ready()
        self.assertTrue(qualify.verify_current_evaluation(
            result.payload, manifest, source, raw,
            trusted_current_as_of="2026-09-13T12:10:00Z",
            tender_pack_bytes=PACK,
            trusted_qualification=trust,
            trusted_qualification_sha256=root,
        ))
        self.assertFalse(qualify.verify_current_evaluation(
            result.payload, manifest, source, raw,
            trusted_current_as_of="2026-09-15T12:10:00Z",
            tender_pack_bytes=PACK,
            trusted_qualification=trust,
            trusted_qualification_sha256=root,
        ))

    def test_current_verifier_rejects_time_rollback(self):
        result, source, raw, manifest, trust, root = self.evaluate_ready()
        with self.assertRaisesRegex(qualify.QualificationError, "ROLLBACK"):
            qualify.verify_current_evaluation(
                result.payload, manifest, source, raw,
                trusted_current_as_of="2026-09-13T11:59:59Z",
                tender_pack_bytes=PACK,
                trusted_qualification=trust,
                trusted_qualification_sha256=root,
            )

    def test_receipt_tamper_fails_integrity(self):
        result, *_ = self.evaluate_ready()
        receipt = copy.deepcopy(result.payload)
        receipt["tender_submission_authorized"] = True
        self.assertFalse(qualify.verify_receipt_integrity(receipt))

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(qualify.QualificationError, "DUPLICATE_JSON_KEY"):
            qualify.load_json_bytes(b'{"a":1,"a":2}', "x")

    def test_nonfinite_json_rejected(self):
        with self.assertRaisesRegex(qualify.QualificationError, "NONFINITE"):
            qualify.load_json_bytes(b'{"a":NaN}', "x")

    def test_bool_as_int_rejected(self):
        source = public_source()
        source["schema_version"] = True
        raw = canonical(source)
        manifest = base_manifest(raw)
        with self.assertRaisesRegex(qualify.QualificationError, "MUST_BE_INT_NOT_BOOL"):
            qualify.evaluate(manifest, source, raw, trusted_as_of=NOW)

    def test_authority_escalation_rejected(self):
        source = public_source()
        raw = canonical(source)
        manifest = base_manifest(raw)
        manifest["authority"]["tender_submission"] = True
        with self.assertRaisesRegex(qualify.QualificationError, "AUTHORITY_ESCALATION"):
            qualify.evaluate(manifest, source, raw, trusted_as_of=NOW)

    def test_team_without_committed_partner_evidence_cannot_replace_root(self):
        _, source, raw, manifest, trust, root = self.evaluate_ready("TEAMING_ACCEPTANCE_EVIDENCE")
        partner_id = manifest["capabilities"]["partner_prime_confirmation"]["evidence_refs"][0]
        trust["approved_evidence"] = [row for row in trust["approved_evidence"] if row["evidence_id"] != partner_id]
        trust["evidence_set_sha256"] = qualify.digest_object(trust["approved_evidence"])
        with self.assertRaisesRegex(qualify.QualificationError, "TRUST_ROOT_MISMATCH"):
            qualify.evaluate(
                manifest, source, raw, trusted_as_of=NOW, tender_pack_bytes=PACK,
                trusted_qualification=trust, trusted_qualification_sha256=root,
            )

    def test_manifest_nonproven_cannot_carry_refs(self):
        source = public_source()
        raw = canonical(source)
        manifest = base_manifest(raw)
        manifest["capabilities"] = {"x": {"status": "UNKNOWN", "evidence_refs": ["ev:x"]}}
        with self.assertRaisesRegex(qualify.QualificationError, "NONPROVEN_CANNOT_CARRY"):
            qualify.evaluate(manifest, source, raw, trusted_as_of=NOW)


if __name__ == "__main__":
    unittest.main()
