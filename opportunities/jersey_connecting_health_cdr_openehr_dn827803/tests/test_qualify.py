from __future__ import annotations

import copy
import hashlib
import inspect
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import qualify
import _qualify_engine as engine

FIXED_AS_OF = datetime(2026, 9, 13, 14, 40, tzinfo=timezone.utc)


def raw_json(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode()


def load(path):
    return engine.load_json_bytes(path.read_bytes(), str(path))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def norm_dt(value):
    return engine._utc_text(engine._parse_dt(value, "test"))


def set_digest(rows):
    return sha(engine.canonical_bytes(sorted(rows, key=lambda row: row["id"])))


def req(rid, pack_sha, *, category="acceptance", shared=False, cure="SELF_ONLY"):
    desc = f"Buyer requirement {rid}"
    return {
        "id": rid,
        "source_id": "DOC-001",
        "source_sha256": pack_sha,
        "source_coordinate": f"buyerpack://DN827803/tender.pdf#req={rid}",
        "category": category,
        "mandatory": True,
        "applies_to_routes": ["TEAMING_ACCEPTANCE_EVIDENCE"],
        "cure": cure,
        "allow_shared_evidence": shared,
        "text_sha256": sha(f"raw:{rid}".encode()),
        "description": desc,
        "description_sha256": sha(desc.encode()),
    }


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
    return sha(engine.canonical_bytes(payload))


class Tests(unittest.TestCase):
    def setUp(self):
        self.public_source_raw = (ROOT / "sources.json").read_bytes()
        self.public_source = load(ROOT / "sources.json")
        self.public_manifest = load(ROOT / "fixtures/public_hold.json")
        self.public_root = load(ROOT / "trusted_root.json")

    def public(self, at=FIXED_AS_OF):
        return qualify.evaluate(
            self.public_manifest,
            self.public_source,
            self.public_source_raw,
            trusted_as_of=at,
        )

    def bundle(
        self,
        *,
        requirements=None,
        subject="TEST_ENTITY",
        partner=True,
        checked="2026-09-13T11:15:00Z",
        deadline="2026-09-29T23:30:00+01:00",
        extracted="2026-09-13T12:00:00Z",
        retained="2026-09-13T12:30:00Z",
        max_age=86400,
    ):
        pack = b"TEST-ONLY buyer tender pack bytes\n"
        pack_sha = sha(pack)
        source = copy.deepcopy(self.public_source)
        source["checked_at"] = checked
        source["response_deadline"] = deadline
        source["tender_pack"] = {
            "acquired": True,
            "reviewed": True,
            "sha256": pack_sha,
            "state": "TENDER_PACK_ACQUIRED_REVIEWED",
        }
        source_raw = raw_json(source)
        inventory = [{
            "id": "DOC-001",
            "kind": "TENDER",
            "sha256": pack_sha,
            "coordinate": "buyerpack://DN827803/tender.pdf",
        }]
        requirements = requirements or [
            req("REQ-001", pack_sha, category="acceptance"),
            req("REQ-002", pack_sha, category="reconciliation"),
        ]
        extraction = {
            "schema_version": 2,
            "notice_id": engine.NOTICE_ID,
            "source_ledger_sha256": sha(source_raw),
            "tender_pack_sha256": pack_sha,
            "extracted_at": extracted,
            "response_deadline": norm_dt(deadline),
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
        extraction_raw = raw_json(extraction)
        esource = {
            "id": "EVIDENCE-SOURCE-1",
            "sha256": sha(b"TEST-ONLY immutable evidence source\n"),
            "coordinate": "repo://evidence/test-source",
        }
        records, claims = [], {}
        for requirement in requirements:
            rid = requirement["id"]
            eid = f"EV-{rid}"
            claim = f"{subject} satisfies {rid}"
            row = {
                "id": eid,
                "subject_id": subject,
                "requirement_ids": [rid],
                "category": requirement["category"],
                "source_id": esource["id"],
                "source_sha256": esource["sha256"],
                "source_coordinate": esource["coordinate"],
                "claim": claim,
                "claim_sha256": sha(claim.encode()),
                "reuse_semantics": "SINGLE_REQUIREMENT",
            }
            row["binding_sha256"] = evidence_binding(row)
            records.append(row)
            claims[rid] = {"status": "PROVEN", "evidence_ids": [eid]}
        evidence = {
            "schema_version": 2,
            "notice_id": engine.NOTICE_ID,
            "source_inventory_complete": True,
            "sources": [esource],
            "records": records,
        }
        evidence_raw = raw_json(evidence)
        root = {
            "schema_version": 2,
            "notice_id": engine.NOTICE_ID,
            "retained_at": retained,
            "source_ledger_sha256": sha(source_raw),
            "source_checked_at": norm_dt(checked),
            "response_deadline": norm_dt(deadline),
            "max_source_age_seconds": max_age,
            "tender_pack_sha256": pack_sha,
            "extraction_sha256": sha(extraction_raw),
            "evidence_bundle_sha256": sha(evidence_raw),
        }
        manifest = {
            "schema_version": 2,
            "notice_id": engine.NOTICE_ID,
            "route": "TEAMING_ACCEPTANCE_EVIDENCE",
            "subject_id": subject,
            "partner_prime_confirmed": partner,
            "authority": {key: False for key in engine.AUTHORITY_FLAGS},
            "requirement_claims": claims,
        }
        return dict(
            pack=pack, source=source, source_raw=source_raw, extraction=extraction,
            extraction_raw=extraction_raw, evidence=evidence,
            evidence_raw=evidence_raw, root=root, manifest=manifest,
        )

    def eval(self, b, *, at=FIXED_AS_OF, extraction=True, evidence=True, pack=None):
        return engine.evaluate(
            b["manifest"], b["source"], b["source_raw"], b["root"],
            trusted_as_of=at,
            tender_pack_bytes=b["pack"] if pack is None else pack,
            extraction_raw=b["extraction_raw"] if extraction else None,
            evidence_raw=b["evidence_raw"] if evidence else None,
        )

    def test_public_hold_and_frozen_receipt(self):
        result = self.public()
        self.assertEqual(result.state, "HOLD_TENDER_PACK_REQUIRED")
        self.assertEqual(result.exit_code, 3)
        self.assertFalse(result.payload["tender_submission_authorized"])
        self.assertEqual(result.bytes(), (ROOT / "fixtures/public_hold.expected.json").read_bytes())

    def test_public_api_has_no_trust_root_injection(self):
        for fn in (qualify.evaluate, qualify.evaluate_historical):
            params = inspect.signature(fn).parameters
            self.assertNotIn("trusted_root", params)
            self.assertNotIn("trusted_root_path", params)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(engine.QualificationError, "DUPLICATE_JSON_KEY"):
            engine.load_json_bytes(b'{"a":1,"a":2}', "x")

    def test_bool_as_int_rejected(self):
        manifest = copy.deepcopy(self.public_manifest)
        manifest["schema_version"] = True
        with self.assertRaisesRegex(engine.QualificationError, "MUST_BE_INT_NOT_BOOL"):
            qualify.evaluate(manifest, self.public_source, self.public_source_raw, trusted_as_of=FIXED_AS_OF)

    def test_authority_escalation_rejected(self):
        manifest = copy.deepcopy(self.public_manifest)
        manifest["authority"]["tender_submission"] = True
        with self.assertRaisesRegex(engine.QualificationError, "AUTHORITY_ESCALATION_FORBIDDEN"):
            qualify.evaluate(manifest, self.public_source, self.public_source_raw, trusted_as_of=FIXED_AS_OF)

    def test_source_self_rewrite_cannot_cross_retained_root(self):
        b = self.bundle()
        source = copy.deepcopy(b["source"])
        source["buyer"] = "attacker-selected buyer"
        with self.assertRaisesRegex(engine.QualificationError, "RETAINED_SOURCE_ROOT_MISMATCH"):
            engine.evaluate(
                b["manifest"], source, raw_json(source), b["root"],
                trusted_as_of=FIXED_AS_OF, tender_pack_bytes=b["pack"],
                extraction_raw=b["extraction_raw"], evidence_raw=b["evidence_raw"],
            )

    def test_omitted_gate_cannot_cross_retained_extraction(self):
        b = self.bundle()
        extraction = copy.deepcopy(b["extraction"])
        extraction["requirements"].pop()
        extraction["requirement_count"] -= 1
        extraction["requirement_set_sha256"] = set_digest(extraction["requirements"])
        with self.assertRaisesRegex(engine.QualificationError, "RETAINED_EXTRACTION_ROOT_MISMATCH"):
            engine.evaluate(
                b["manifest"], b["source"], b["source_raw"], b["root"],
                trusted_as_of=FIXED_AS_OF, tender_pack_bytes=b["pack"],
                extraction_raw=raw_json(extraction), evidence_raw=b["evidence_raw"],
            )

    def test_retained_gate_omitted_from_manifest_holds(self):
        b = self.bundle()
        omitted = sorted(b["manifest"]["requirement_claims"])[-1]
        del b["manifest"]["requirement_claims"][omitted]
        result = self.eval(b)
        self.assertEqual(result.state, "HOLD_EVIDENCE_GAPS")
        self.assertIn({"requirement_id": omitted, "status": "UNDECLARED"}, result.payload["missing_required_requirements"])

    def test_requirement_semantic_mutations_cannot_cross_root(self):
        for field, value in [("mandatory", False), ("cure", "PARTNER_ALLOWED"), ("category", "changed"), ("description", "changed description")]:
            with self.subTest(field=field):
                b = self.bundle()
                extraction = copy.deepcopy(b["extraction"])
                row = extraction["requirements"][0]
                row[field] = value
                if field == "description":
                    row["description_sha256"] = sha(value.encode())
                extraction["requirement_set_sha256"] = set_digest(extraction["requirements"])
                with self.assertRaisesRegex(engine.QualificationError, "RETAINED_EXTRACTION_ROOT_MISMATCH"):
                    engine.evaluate(
                        b["manifest"], b["source"], b["source_raw"], b["root"],
                        trusted_as_of=FIXED_AS_OF, tender_pack_bytes=b["pack"],
                        extraction_raw=raw_json(extraction), evidence_raw=b["evidence_raw"],
                    )

    def test_arbitrary_evidence_string_rejected(self):
        b = self.bundle()
        rid = next(iter(b["manifest"]["requirement_claims"]))
        b["manifest"]["requirement_claims"][rid]["evidence_ids"] = [f"evidence:{rid}"]
        with self.assertRaisesRegex(engine.QualificationError, "UNKNOWN_EVIDENCE"):
            self.eval(b)

    def test_unrelated_requirement_evidence_rejected(self):
        b = self.bundle()
        a, other = list(b["manifest"]["requirement_claims"])
        eid = b["manifest"]["requirement_claims"][a]["evidence_ids"][0]
        b["manifest"]["requirement_claims"][other]["evidence_ids"] = [eid]
        with self.assertRaisesRegex(engine.QualificationError, "EVIDENCE_REQUIREMENT_MISMATCH"):
            self.eval(b)

    def test_subject_mismatch_rejected(self):
        b = self.bundle()
        b["manifest"]["subject_id"] = "OTHER_ENTITY"
        with self.assertRaisesRegex(engine.QualificationError, "EVIDENCE_SUBJECT_MISMATCH"):
            self.eval(b)

    def test_pack_digest_mismatch_rejected(self):
        b = self.bundle()
        with self.assertRaisesRegex(engine.QualificationError, "TENDER_PACK_DIGEST_MISMATCH"):
            self.eval(b, pack=b"wrong bytes")

    def test_forged_deadline_cannot_cross_retained_root(self):
        b = self.bundle()
        source = copy.deepcopy(b["source"])
        source["response_deadline"] = "2027-09-29T23:30:00+01:00"
        with self.assertRaisesRegex(engine.QualificationError, "RETAINED_SOURCE_ROOT_MISMATCH"):
            engine.evaluate(
                b["manifest"], source, raw_json(source), b["root"],
                trusted_as_of=FIXED_AS_OF, tender_pack_bytes=b["pack"],
                extraction_raw=b["extraction_raw"], evidence_raw=b["evidence_raw"],
            )

    def test_deadline_passed_holds(self):
        b = self.bundle(max_age=60 * 60 * 24 * 90)
        result = self.eval(b, at=datetime(2026, 9, 30, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(result.state, "HOLD_DEADLINE_PASSED")

    def test_source_stale_holds(self):
        b = self.bundle()
        result = self.eval(b, at=datetime(2026, 9, 15, 14, 0, tzinfo=timezone.utc))
        self.assertEqual(result.state, "HOLD_SOURCE_STALE")

    def test_trusted_time_rollback_rejected(self):
        b = self.bundle()
        with self.assertRaisesRegex(engine.QualificationError, "TRUSTED_TIME_ROLLBACK"):
            self.eval(b, at=datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc))

    def test_extraction_rollback_rejected(self):
        b = self.bundle(extracted="2026-09-13T11:00:00Z")
        with self.assertRaisesRegex(engine.QualificationError, "EXTRACTION_TIME_BEFORE_SOURCE_CHECK"):
            self.eval(b)

    def test_future_extraction_rejected(self):
        b = self.bundle(extracted="2026-09-13T13:00:00Z")
        with self.assertRaisesRegex(engine.QualificationError, "EXTRACTION_TIME_AFTER_ROOT_RETENTION"):
            self.eval(b)

    def test_missing_extraction_holds(self):
        self.assertEqual(self.eval(self.bundle(), extraction=False).state, "HOLD_TRUSTED_EXTRACTION_REQUIRED")

    def test_missing_evidence_holds(self):
        self.assertEqual(self.eval(self.bundle(), evidence=False).state, "HOLD_TRUSTED_EVIDENCE_REQUIRED")

    def test_valid_buyer_bound_bundle_reaches_owner_review_only(self):
        result = self.eval(self.bundle())
        self.assertEqual(result.state, "READY_FOR_OWNER_TENDER_REVIEW")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.payload["authority"], "INTERNAL_QUALIFICATION_ONLY")
        self.assertFalse(result.payload["tender_submission_authorized"])

    def test_teaming_requires_prime(self):
        self.assertEqual(self.eval(self.bundle(partner=False)).state, "HOLD_PARTNER_REQUIRED")

    def test_historical_replay_never_current_ready(self):
        b = self.bundle()
        result = engine.evaluate_historical(
            b["manifest"], b["source"], b["source_raw"], b["root"],
            replay_as_of=FIXED_AS_OF, tender_pack_bytes=b["pack"],
            extraction_raw=b["extraction_raw"], evidence_raw=b["evidence_raw"],
        )
        self.assertEqual(result.state, "HISTORICAL_REPLAY_READY_NOT_CURRENT_AUTHORITY")
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.payload["authority_mode"], "HISTORICAL_REPLAY_ONLY")
        self.assertFalse(result.payload["tender_submission_authorized"])

    def _shared_bundle(self, semantics):
        pack_sha = sha(b"TEST-ONLY buyer tender pack bytes\n")
        requirements = [req("REQ-A", pack_sha, shared=True), req("REQ-B", pack_sha, shared=True)]
        b = self.bundle(requirements=requirements)
        src = b["evidence"]["sources"][0]
        claim = "One immutable acceptance record covers REQ-A and REQ-B"
        row = {
            "id": "EV-SHARED", "subject_id": "TEST_ENTITY",
            "requirement_ids": ["REQ-A", "REQ-B"], "category": "acceptance",
            "source_id": src["id"], "source_sha256": src["sha256"],
            "source_coordinate": src["coordinate"], "claim": claim,
            "claim_sha256": sha(claim.encode()), "reuse_semantics": semantics,
        }
        row["binding_sha256"] = evidence_binding(row)
        b["evidence"]["records"] = [row]
        b["evidence_raw"] = raw_json(b["evidence"])
        b["root"]["evidence_bundle_sha256"] = sha(b["evidence_raw"])
        b["manifest"]["requirement_claims"] = {
            rid: {"status": "PROVEN", "evidence_ids": ["EV-SHARED"]}
            for rid in ("REQ-A", "REQ-B")
        }
        return b

    def test_explicit_same_category_reuse_allowed(self):
        self.assertEqual(self.eval(self._shared_bundle("EXPLICIT_SAME_CATEGORY")).state, "READY_FOR_OWNER_TENDER_REVIEW")

    def test_implicit_cross_gate_reuse_rejected(self):
        with self.assertRaisesRegex(engine.QualificationError, "reuse_semantics:NOT_EXPLICIT"):
            self.eval(self._shared_bundle("SINGLE_REQUIREMENT"))


if __name__ == "__main__":
    unittest.main()
