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
import qualify


FIXED_AS_OF = datetime(2026, 9, 13, 14, 40, tzinfo=timezone.utc)


def canonical_file(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def load(path):
    return qualify.load_json_bytes(path.read_bytes(), str(path))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def normalize_dt(value):
    return qualify._utc_text(qualify._parse_dt(value, "test"))


def requirement(
    rid,
    *,
    category="acceptance",
    routes=None,
    cure="SELF_ONLY",
    shared=False,
    description=None,
    source_sha=None,
    source_coordinate="buyerpack://DN827803/tender.pdf",
):
    if routes is None:
        routes = ["TEAMING_ACCEPTANCE_EVIDENCE"]
    if description is None:
        description = f"Buyer requirement {rid}"
    if source_sha is None:
        source_sha = "a" * 64
    return {
        "id": rid,
        "source_id": "DOC-001",
        "source_sha256": source_sha,
        "source_coordinate": source_coordinate + f"#req={rid}",
        "category": category,
        "mandatory": True,
        "applies_to_routes": routes,
        "cure": cure,
        "allow_shared_evidence": shared,
        "text_sha256": sha(f"raw:{rid}".encode()),
        "description": description,
        "description_sha256": sha(description.encode()),
    }


def set_digest(rows):
    return sha(qualify.canonical_bytes(sorted(rows, key=lambda item: item["id"])))


def evidence_binding(row):
    payload = {
        "subject_id": row["subject_id"],
        "requirement_ids": sorted(row["requirement_ids"]),
        "category": row["category"],
        "source_id": row["source_id"],
        "source_sha256": row["source_sha256"],
        "source_coordinate": row["source_coordinate"],
        "claim_sha256": row["claim_sha256"],
        "reuse_semantics": row["reuse_semantics"],
    }
    return sha(qualify.canonical_bytes(payload))


class Tests(unittest.TestCase):
    def setUp(self):
        self.public_source_raw = (ROOT / "sources.json").read_bytes()
        self.public_source = load(ROOT / "sources.json")
        self.public_manifest = load(ROOT / "fixtures/public_hold.json")
        self.public_root = load(ROOT / "trusted_root.json")

    def current_public(self, *, as_of=FIXED_AS_OF):
        return qualify.evaluate(
            self.public_manifest,
            self.public_source,
            self.public_source_raw,
            self.public_root,
            trusted_as_of=as_of,
        )

    def ready_bundle(
        self,
        *,
        requirements=None,
        subject_id="TEST_ENTITY",
        route="TEAMING_ACCEPTANCE_EVIDENCE",
        partner_prime_confirmed=True,
        source_checked_at="2026-09-13T11:15:00Z",
        response_deadline="2026-09-29T23:30:00+01:00",
        extracted_at="2026-09-13T12:00:00Z",
        retained_at="2026-09-13T12:30:00Z",
        max_source_age_seconds=86400,
    ):
        pack = b"TEST-ONLY buyer tender pack bytes\n"
        pack_sha = sha(pack)
        source = copy.deepcopy(self.public_source)
        source["checked_at"] = source_checked_at
        source["response_deadline"] = response_deadline
        source["tender_pack"] = {
            "acquired": True,
            "reviewed": True,
            "sha256": pack_sha,
            "state": "TENDER_PACK_ACQUIRED_REVIEWED",
        }
        source_raw = canonical_file(source)
        source_sha = sha(source_raw)

        inventory = [{
            "id": "DOC-001",
            "kind": "TENDER",
            "sha256": pack_sha,
            "coordinate": "buyerpack://DN827803/tender.pdf",
        }]
        if requirements is None:
            requirements = [
                requirement("REQ-001", category="acceptance", source_sha=pack_sha),
                requirement("REQ-002", category="reconciliation", source_sha=pack_sha),
            ]
        extraction = {
            "schema_version": 2,
            "notice_id": qualify.NOTICE_ID,
            "source_ledger_sha256": source_sha,
            "tender_pack_sha256": pack_sha,
            "extracted_at": extracted_at,
            "response_deadline": normalize_dt(response_deadline),
            "inventory_complete": True,
            "mandatory_requirements_complete": True,
            "inventory_count": len(inventory),
            "inventory_set_sha256": set_digest(inventory),
            "deadline_source_id": "DOC-001",
            "deadline_source_coordinate": "buyerpack://DN827803/tender.pdf",
            "deadline_text_sha256": sha(b"Response deadline clause"),
            "inventory": inventory,
            "requirement_count": len(requirements),
            "requirement_set_sha256": set_digest(requirements),
            "requirements": requirements,
        }
        extraction_raw = canonical_file(extraction)

        evidence_source_bytes = b"TEST-ONLY immutable evidence source\n"
        evidence_source = {
            "id": "EVIDENCE-SOURCE-1",
            "sha256": sha(evidence_source_bytes),
            "coordinate": "repo://evidence/test-source",
        }
        records = []
        claims = {}
        for req in requirements:
            eid = f"EV-{req['id']}"
            claim = f"{subject_id} satisfies {req['id']}"
            row = {
                "id": eid,
                "subject_id": subject_id,
                "requirement_ids": [req["id"]],
                "category": req["category"],
                "source_id": evidence_source["id"],
                "source_sha256": evidence_source["sha256"],
                "source_coordinate": evidence_source["coordinate"],
                "claim": claim,
                "claim_sha256": sha(claim.encode()),
                "reuse_semantics": "SINGLE_REQUIREMENT",
            }
            row["binding_sha256"] = evidence_binding(row)
            records.append(row)
            claims[req["id"]] = {"status": "PROVEN", "evidence_ids": [eid]}

        evidence = {
            "schema_version": 2,
            "notice_id": qualify.NOTICE_ID,
            "source_inventory_complete": True,
            "sources": [evidence_source],
            "records": records,
        }
        evidence_raw = canonical_file(evidence)

        trusted_root = {
            "schema_version": 2,
            "notice_id": qualify.NOTICE_ID,
            "retained_at": retained_at,
            "source_ledger_sha256": source_sha,
            "source_checked_at": normalize_dt(source_checked_at),
            "response_deadline": normalize_dt(response_deadline),
            "max_source_age_seconds": max_source_age_seconds,
            "tender_pack_sha256": pack_sha,
            "extraction_sha256": sha(extraction_raw),
            "evidence_bundle_sha256": sha(evidence_raw),
        }
        manifest = {
            "schema_version": 2,
            "notice_id": qualify.NOTICE_ID,
            "route": route,
            "subject_id": subject_id,
            "partner_prime_confirmed": partner_prime_confirmed,
            "authority": {key: False for key in qualify.AUTHORITY_FLAGS},
            "requirement_claims": claims,
        }
        return {
            "pack": pack,
            "source": source,
            "source_raw": source_raw,
            "extraction": extraction,
            "extraction_raw": extraction_raw,
            "evidence": evidence,
            "evidence_raw": evidence_raw,
            "root": trusted_root,
            "manifest": manifest,
        }

    def evaluate_bundle(self, bundle, *, as_of=FIXED_AS_OF):
        return qualify.evaluate(
            bundle["manifest"],
            bundle["source"],
            bundle["source_raw"],
            bundle["root"],
            trusted_as_of=as_of,
            tender_pack_bytes=bundle["pack"],
            extraction_raw=bundle["extraction_raw"],
            evidence_raw=bundle["evidence_raw"],
        )

    def test_public_holds_tender_pack(self):
        result = self.current_public()
        self.assertEqual(result.state, "HOLD_TENDER_PACK_REQUIRED")
        self.assertEqual(result.exit_code, 3)
        self.assertFalse(result.payload["tender_submission_authorized"])

    def test_public_receipt_is_deterministic_with_explicit_trusted_time(self):
        receipt = self.current_public().bytes()
        self.assertEqual(receipt, self.current_public().bytes())
        self.assertEqual(receipt, (ROOT / "fixtures" / "public_hold.expected.json").read_bytes())

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(qualify.QualificationError, "DUPLICATE_JSON_KEY"):
            qualify.load_json_bytes(b'{"a":1,"a":2}', "x")

    def test_bool_as_int_rejected(self):
        manifest = copy.deepcopy(self.public_manifest)
        manifest["schema_version"] = True
        with self.assertRaisesRegex(qualify.QualificationError, "MUST_BE_INT_NOT_BOOL"):
            qualify.evaluate(
                manifest,
                self.public_source,
                self.public_source_raw,
                self.public_root,
                trusted_as_of=FIXED_AS_OF,
            )

    def test_authority_escalation_rejected(self):
        manifest = copy.deepcopy(self.public_manifest)
        manifest["authority"]["tender_submission"] = True
        with self.assertRaisesRegex(
            qualify.QualificationError, "AUTHORITY_ESCALATION_FORBIDDEN"
        ):
            qualify.evaluate(
                manifest,
                self.public_source,
                self.public_source_raw,
                self.public_root,
                trusted_as_of=FIXED_AS_OF,
            )

    def test_rewrite_source_and_recompute_caller_state_cannot_cross_retained_root(self):
        bundle = self.ready_bundle()
        source = copy.deepcopy(bundle["source"])
        source["buyer"] = "attacker-selected buyer"
        source_raw = canonical_file(source)
        with self.assertRaisesRegex(
            qualify.QualificationError, "RETAINED_SOURCE_ROOT_MISMATCH"
        ):
            qualify.evaluate(
                bundle["manifest"],
                source,
                source_raw,
                bundle["root"],
                trusted_as_of=FIXED_AS_OF,
                tender_pack_bytes=bundle["pack"],
                extraction_raw=bundle["extraction_raw"],
                evidence_raw=bundle["evidence_raw"],
            )

    def test_omit_mandatory_gate_fails_against_retained_extraction(self):
        bundle = self.ready_bundle()
        extraction = copy.deepcopy(bundle["extraction"])
        extraction["requirements"].pop()
        extraction["requirement_count"] = len(extraction["requirements"])
        extraction["requirement_set_sha256"] = set_digest(extraction["requirements"])
        raw = canonical_file(extraction)
        with self.assertRaisesRegex(
            qualify.QualificationError, "RETAINED_EXTRACTION_ROOT_MISMATCH"
        ):
            qualify.evaluate(
                bundle["manifest"],
                bundle["source"],
                bundle["source_raw"],
                bundle["root"],
                trusted_as_of=FIXED_AS_OF,
                tender_pack_bytes=bundle["pack"],
                extraction_raw=raw,
                evidence_raw=bundle["evidence_raw"],
            )

    def test_mutating_requirement_semantics_fails_against_retained_extraction(self):
        for field, value in [
            ("mandatory", False),
            ("cure", "PARTNER_ALLOWED"),
            ("category", "changed-category"),
            ("description", "changed description"),
        ]:
            with self.subTest(field=field):
                bundle = self.ready_bundle()
                extraction = copy.deepcopy(bundle["extraction"])
                row = extraction["requirements"][0]
                row[field] = value
                if field == "description":
                    row["description_sha256"] = sha(value.encode())
                extraction["requirement_set_sha256"] = set_digest(extraction["requirements"])
                raw = canonical_file(extraction)
                with self.assertRaisesRegex(
                    qualify.QualificationError, "RETAINED_EXTRACTION_ROOT_MISMATCH"
                ):
                    qualify.evaluate(
                        bundle["manifest"],
                        bundle["source"],
                        bundle["source_raw"],
                        bundle["root"],
                        trusted_as_of=FIXED_AS_OF,
                        tender_pack_bytes=bundle["pack"],
                        extraction_raw=raw,
                        evidence_raw=bundle["evidence_raw"],
                    )

    def test_arbitrary_evidence_string_cannot_satisfy_requirement(self):
        bundle = self.ready_bundle()
        rid = next(iter(bundle["manifest"]["requirement_claims"]))
        bundle["manifest"]["requirement_claims"][rid]["evidence_ids"] = [
            f"evidence:{rid}"
        ]
        with self.assertRaisesRegex(
            qualify.QualificationError, "UNKNOWN_EVIDENCE"
        ):
            self.evaluate_bundle(bundle)

    def test_evidence_from_one_requirement_cannot_satisfy_unrelated_requirement(self):
        bundle = self.ready_bundle()
        rids = list(bundle["manifest"]["requirement_claims"])
        first_evidence = bundle["manifest"]["requirement_claims"][rids[0]]["evidence_ids"][0]
        bundle["manifest"]["requirement_claims"][rids[1]]["evidence_ids"] = [
            first_evidence
        ]
        with self.assertRaisesRegex(
            qualify.QualificationError, "EVIDENCE_REQUIREMENT_MISMATCH"
        ):
            self.evaluate_bundle(bundle)

    def test_subject_mismatch_rejected(self):
        bundle = self.ready_bundle()
        bundle["manifest"]["subject_id"] = "OTHER_ENTITY"
        with self.assertRaisesRegex(
            qualify.QualificationError, "EVIDENCE_SUBJECT_MISMATCH"
        ):
            self.evaluate_bundle(bundle)

    def test_pack_digest_mismatch_rejected(self):
        bundle = self.ready_bundle()
        with self.assertRaisesRegex(
            qualify.QualificationError, "TENDER_PACK_DIGEST_MISMATCH"
        ):
            qualify.evaluate(
                bundle["manifest"],
                bundle["source"],
                bundle["source_raw"],
                bundle["root"],
                trusted_as_of=FIXED_AS_OF,
                tender_pack_bytes=b"wrong bytes",
                extraction_raw=bundle["extraction_raw"],
                evidence_raw=bundle["evidence_raw"],
            )

    def test_forged_deadline_in_caller_source_cannot_extend_root(self):
        bundle = self.ready_bundle()
        source = copy.deepcopy(bundle["source"])
        source["response_deadline"] = "2027-09-29T23:30:00+01:00"
        source_raw = canonical_file(source)
        with self.assertRaisesRegex(
            qualify.QualificationError, "RETAINED_SOURCE_ROOT_MISMATCH"
        ):
            qualify.evaluate(
                bundle["manifest"],
                source,
                source_raw,
                bundle["root"],
                trusted_as_of=FIXED_AS_OF,
                tender_pack_bytes=bundle["pack"],
                extraction_raw=bundle["extraction_raw"],
                evidence_raw=bundle["evidence_raw"],
            )

    def test_after_buyer_deadline_fails_closed(self):
        bundle = self.ready_bundle(max_source_age_seconds=60 * 60 * 24 * 90)
        after_deadline = datetime(2026, 9, 30, 0, 0, tzinfo=timezone.utc)
        result = self.evaluate_bundle(bundle, as_of=after_deadline)
        self.assertEqual(result.state, "HOLD_DEADLINE_PASSED")
        self.assertEqual(result.exit_code, 3)

    def test_source_aging_fails_closed(self):
        bundle = self.ready_bundle()
        stale = datetime(2026, 9, 15, 14, 0, tzinfo=timezone.utc)
        result = self.evaluate_bundle(bundle, as_of=stale)
        self.assertEqual(result.state, "HOLD_SOURCE_STALE")

    def test_trusted_time_rollback_rejected(self):
        bundle = self.ready_bundle()
        rollback = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        with self.assertRaisesRegex(
            qualify.QualificationError, "TRUSTED_TIME_ROLLBACK"
        ):
            self.evaluate_bundle(bundle, as_of=rollback)

    def test_future_extraction_rejected(self):
        bundle = self.ready_bundle(extracted_at="2026-09-13T13:00:00Z")
        with self.assertRaisesRegex(
            qualify.QualificationError, "EXTRACTION_TIME_AFTER_ROOT_RETENTION"
        ):
            self.evaluate_bundle(bundle)

    def test_missing_extraction_holds(self):
        bundle = self.ready_bundle()
        result = qualify.evaluate(
            bundle["manifest"],
            bundle["source"],
            bundle["source_raw"],
            bundle["root"],
            trusted_as_of=FIXED_AS_OF,
            tender_pack_bytes=bundle["pack"],
            extraction_raw=None,
            evidence_raw=bundle["evidence_raw"],
        )
        self.assertEqual(result.state, "HOLD_TRUSTED_EXTRACTION_REQUIRED")

    def test_missing_evidence_bundle_holds(self):
        bundle = self.ready_bundle()
        result = qualify.evaluate(
            bundle["manifest"],
            bundle["source"],
            bundle["source_raw"],
            bundle["root"],
            trusted_as_of=FIXED_AS_OF,
            tender_pack_bytes=bundle["pack"],
            extraction_raw=bundle["extraction_raw"],
            evidence_raw=None,
        )
        self.assertEqual(result.state, "HOLD_TRUSTED_EVIDENCE_REQUIRED")

    def test_valid_buyer_bound_bundle_can_reach_owner_review_only(self):
        bundle = self.ready_bundle()
        result = self.evaluate_bundle(bundle)
        self.assertEqual(result.state, "READY_FOR_OWNER_TENDER_REVIEW")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.payload["authority"], "INTERNAL_QUALIFICATION_ONLY")
        self.assertFalse(result.payload["tender_submission_authorized"])

    def test_teaming_route_still_requires_prime(self):
        bundle = self.ready_bundle(partner_prime_confirmed=False)
        result = self.evaluate_bundle(bundle)
        self.assertEqual(result.state, "HOLD_PARTNER_REQUIRED")

    def test_historical_replay_can_never_emit_current_ready_authority(self):
        bundle = self.ready_bundle()
        result = qualify.evaluate_historical(
            bundle["manifest"],
            bundle["source"],
            bundle["source_raw"],
            bundle["root"],
            replay_as_of=FIXED_AS_OF,
            tender_pack_bytes=bundle["pack"],
            extraction_raw=bundle["extraction_raw"],
            evidence_raw=bundle["evidence_raw"],
        )
        self.assertEqual(
            result.state, "HISTORICAL_REPLAY_READY_NOT_CURRENT_AUTHORITY"
        )
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.payload["authority_mode"], "HISTORICAL_REPLAY_ONLY")
        self.assertFalse(result.payload["tender_submission_authorized"])

    def test_explicit_same_category_cross_requirement_reuse(self):
        pack_sha = sha(b"TEST-ONLY buyer tender pack bytes\n")
        requirements = [
            requirement(
                "REQ-A",
                category="acceptance",
                source_sha=pack_sha,
                shared=True,
            ),
            requirement(
                "REQ-B",
                category="acceptance",
                source_sha=pack_sha,
                shared=True,
            ),
        ]
        bundle = self.ready_bundle(requirements=requirements)
        source = bundle["evidence"]["sources"][0]
        claim = "One immutable acceptance record explicitly covers REQ-A and REQ-B"
        shared = {
            "id": "EV-SHARED",
            "subject_id": "TEST_ENTITY",
            "requirement_ids": ["REQ-A", "REQ-B"],
            "category": "acceptance",
            "source_id": source["id"],
            "source_sha256": source["sha256"],
            "source_coordinate": source["coordinate"],
            "claim": claim,
            "claim_sha256": sha(claim.encode()),
            "reuse_semantics": "EXPLICIT_SAME_CATEGORY",
        }
        shared["binding_sha256"] = evidence_binding(shared)
        evidence = copy.deepcopy(bundle["evidence"])
        evidence["records"] = [shared]
        evidence_raw = canonical_file(evidence)
        bundle["evidence"] = evidence
        bundle["evidence_raw"] = evidence_raw
        bundle["root"]["evidence_bundle_sha256"] = sha(evidence_raw)
        for rid in ["REQ-A", "REQ-B"]:
            bundle["manifest"]["requirement_claims"][rid] = {
                "status": "PROVEN",
                "evidence_ids": ["EV-SHARED"],
            }
        result = self.evaluate_bundle(bundle)
        self.assertEqual(result.state, "READY_FOR_OWNER_TENDER_REVIEW")

    def test_implicit_cross_requirement_reuse_rejected(self):
        pack_sha = sha(b"TEST-ONLY buyer tender pack bytes\n")
        requirements = [
            requirement(
                "REQ-A",
                category="acceptance",
                source_sha=pack_sha,
                shared=True,
            ),
            requirement(
                "REQ-B",
                category="acceptance",
                source_sha=pack_sha,
                shared=True,
            ),
        ]
        bundle = self.ready_bundle(requirements=requirements)
        source = bundle["evidence"]["sources"][0]
        claim = "Ambiguous reused evidence"
        shared = {
            "id": "EV-SHARED",
            "subject_id": "TEST_ENTITY",
            "requirement_ids": ["REQ-A", "REQ-B"],
            "category": "acceptance",
            "source_id": source["id"],
            "source_sha256": source["sha256"],
            "source_coordinate": source["coordinate"],
            "claim": claim,
            "claim_sha256": sha(claim.encode()),
            "reuse_semantics": "SINGLE_REQUIREMENT",
        }
        shared["binding_sha256"] = evidence_binding(shared)
        evidence = copy.deepcopy(bundle["evidence"])
        evidence["records"] = [shared]
        evidence_raw = canonical_file(evidence)
        bundle["evidence_raw"] = evidence_raw
        bundle["root"]["evidence_bundle_sha256"] = sha(evidence_raw)
        bundle["manifest"]["requirement_claims"] = {
            "REQ-A": {"status": "PROVEN", "evidence_ids": ["EV-SHARED"]},
            "REQ-B": {"status": "PROVEN", "evidence_ids": ["EV-SHARED"]},
        }
        with self.assertRaisesRegex(
            qualify.QualificationError, "reuse_semantics:NOT_EXPLICIT"
        ):
            self.evaluate_bundle(bundle)


if __name__ == "__main__":
    unittest.main()
