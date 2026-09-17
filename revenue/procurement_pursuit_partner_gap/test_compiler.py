from __future__ import annotations

import hashlib
import json
import unittest

from revenue.procurement_response_module_library import materializer
from revenue.procurement_pursuit_partner_gap.compiler import (
    Error, REQUEST, TRUTH_BOUNDARY, canon, compile_gap, verify_gap,
)


def raw(v):
    return canon(v)


def sha_text(s):
    return hashlib.sha256(s.encode()).hexdigest()


def source_record(claim_id="claim-cap", claim_kind="CAPABILITY", family="corporate_capability", status="APPROVED", evidence_state="SUPPORTED", source_kind="APPROVED_CAPABILITY_FACT", tags=None):
    return {
        "record_id": "rec-" + claim_id,
        "evidence_id": "ev-" + claim_id,
        "module_id": "mod-" + claim_id,
        "claim_id": claim_id,
        "family": family,
        "title": "Approved claim",
        "claim_text": "TJLabs has the retained capability.",
        "claim_kind": claim_kind,
        "source_kind": source_kind,
        "source_ref": "https://evidence.example/" + claim_id,
        "source_sha256": "a" * 64,
        "observed_at": "2026-09-15T00:00:00Z",
        "expires_at": "2026-10-01T00:00:00Z",
        "owner_status": status,
        "evidence_state": evidence_state,
        "revision": 1,
        "valid_from": "2026-09-01T00:00:00Z",
        "valid_until": "2026-10-01T00:00:00Z",
        "applicability_tags": tags or ["cloud"],
    }


def mat_source(records=None):
    return {
        "schema": materializer.SOURCE_SCHEMA,
        "library_id": "lib1",
        "generated_at": "2026-09-16T00:00:00Z",
        "evidence_max_age_seconds": 604800,
        "truth_boundary": materializer.TRUTH_BOUNDARY,
        "records": records or [source_record()],
    }


def requirement(rid, **kw):
    text = kw.pop("text", "Buyer requires retained capability.")
    out = {
        "requirement_id": rid,
        "text": text,
        "text_sha256": sha_text(text),
        "family": "corporate_capability",
        "claim_kind": "CAPABILITY",
        "applicability_tags": ["cloud"],
        "mapping_approval": "NONE",
        "internal_claim_id": None,
        "partner_eligible": True,
        "capability_key": "cloud-delivery",
        "required_proof_kind": "CAPABILITY_PROOF",
        "partner_deliverable": "Provide current capability proof and own the mapped workshare.",
    }
    out.update(kw)
    return out


def pursuit(pid, requirements, *, authority="BUYER_OFFICIAL", observed="2026-09-15T00:00:00Z", expires="2026-09-30T00:00:00Z"):
    return {
        "pursuit_id": pid,
        "title": "Pursuit " + pid,
        "source": {
            "uri": "https://buyer.example.gov/" + pid,
            "sha256": "b" * 64,
            "observed_at": observed,
            "expires_at": expires,
            "authority": authority,
        },
        "requirements": requirements,
    }


def request(pursuits, proofs=None, mode="RETAINED_CURRENT"):
    return {
        "schema": REQUEST,
        "generated_at": "2026-09-16T01:00:00Z",
        "max_pursuit_source_age_seconds": 604800,
        "truth_boundary": TRUTH_BOUNDARY,
        "carrier_mode": mode,
        "pursuits": pursuits,
        "prime_proofs": proofs or [],
    }


def generation(records=None):
    sr = raw(mat_source(records))
    c, d, r = materializer.compile_materializer(sr)
    return sr, c, d, r


def compile_req(req, records=None, proofs=None, mode="RETAINED_CURRENT", extra_pursuits=None):
    ps = [pursuit("p1", [req])]
    if extra_pursuits:
        ps.extend(extra_pursuits)
    return compile_gap(raw(request(ps, proofs, mode)), *generation(records))


class Tests(unittest.TestCase):
    def packet(self, *args, **kwargs):
        return json.loads(compile_req(*args, **kwargs)[0])

    def test_pass_exact_approved_generation(self):
        r = requirement("r1", mapping_approval="APPROVED", internal_claim_id="claim-cap")
        p = self.packet(r)
        x = p["requirement_results"][0]
        self.assertEqual("PASS", x["state"])
        self.assertIn("mod-claim-cap", x["internal_refs"])

    def test_pending_mapping_owner_input(self):
        r = requirement("r1", mapping_approval="PENDING", internal_claim_id="claim-cap")
        self.assertEqual("OWNER_INPUT", self.packet(r)["requirement_results"][0]["state"])

    def test_approved_missing_claim_owner_input(self):
        r = requirement("r1", mapping_approval="APPROVED", internal_claim_id="missing")
        self.assertIn("APPROVED_INTERNAL_CLAIM_NOT_IN_VERIFIED_GENERATION", self.packet(r)["requirement_results"][0]["reasons"])

    def test_internal_not_supported_owner_input(self):
        rec = source_record(status="PENDING")
        r = requirement("r1", mapping_approval="APPROVED", internal_claim_id="claim-cap")
        self.assertEqual("OWNER_INPUT", self.packet(r, records=[rec])["requirement_results"][0]["state"])

    def test_applicability_mismatch_owner_input(self):
        r = requirement("r1", mapping_approval="APPROVED", internal_claim_id="claim-cap", applicability_tags=["health"])
        self.assertIn("INTERNAL_APPLICABILITY_MISMATCH", self.packet(r)["requirement_results"][0]["reasons"])

    def test_partner_required_and_dedup(self):
        req1 = requirement("r1")
        req2 = requirement("r2")
        sr, c, d, rc = generation()
        q = request([pursuit("p1", [req1]), pursuit("p2", [req2])])
        p = json.loads(compile_gap(raw(q), sr, c, d, rc)[0])
        self.assertEqual(2, p["counts"]["PARTNER_REQUIRED"])
        self.assertEqual(1, len(p["partner_capability_shortlist"]))
        self.assertEqual(2, len(p["partner_capability_shortlist"][0]["requirement_refs"]))

    def test_partner_not_eligible_owner_input(self):
        r = requirement("r1", partner_eligible=False)
        self.assertEqual("OWNER_INPUT", self.packet(r)["requirement_results"][0]["state"])

    def test_prime_supported(self):
        r = requirement("r1")
        proof = {
            "proof_id": "pp1", "requirement_id": "r1", "proof_kind": "CAPABILITY_PROOF",
            "source_ref": "https://prime.example/proof", "source_sha256": "c" * 64,
            "verified_at": "2026-09-15T00:00:00Z", "expires_at": "2026-10-01T00:00:00Z",
            "status": "VERIFIED",
        }
        self.assertEqual("PRIME_SUPPORTED", self.packet(r, proofs=[proof])["requirement_results"][0]["state"])

    def test_stale_prime_proof_owner_input(self):
        r = requirement("r1")
        proof = {
            "proof_id": "pp1", "requirement_id": "r1", "proof_kind": "CAPABILITY_PROOF",
            "source_ref": "https://prime.example/proof", "source_sha256": "c" * 64,
            "verified_at": "2026-09-01T00:00:00Z", "expires_at": "2026-09-10T00:00:00Z",
            "status": "VERIFIED",
        }
        p = self.packet(r, proofs=[proof])
        self.assertEqual("OWNER_INPUT", p["requirement_results"][0]["state"])
        self.assertIn("PRIME_PROOF_EXPIRED", p["requirement_results"][0]["reasons"])

    def test_provisional_prime_proof_owner_input(self):
        r = requirement("r1")
        proof = {
            "proof_id": "pp1", "requirement_id": "r1", "proof_kind": "CAPABILITY_PROOF",
            "source_ref": "https://prime.example/proof", "source_sha256": "c" * 64,
            "verified_at": "2026-09-15T00:00:00Z", "expires_at": "2026-10-01T00:00:00Z",
            "status": "PROVISIONAL",
        }
        self.assertEqual("OWNER_INPUT", self.packet(r, proofs=[proof])["requirement_results"][0]["state"])

    def test_sensitive_proof_kind_is_mechanical(self):
        text = "Buyer requires named customer reference."
        r = requirement(
            "r1", text=text, family="references_past_performance", claim_kind="REFERENCE",
            required_proof_kind="REFERENCE_PERMISSION_RECEIPT", capability_key="reference-enterprise",
        )
        proof = {
            "proof_id": "pp1", "requirement_id": "r1", "proof_kind": "REFERENCE_PERMISSION_RECEIPT",
            "source_ref": "https://prime.example/reference", "source_sha256": "c" * 64,
            "verified_at": "2026-09-15T00:00:00Z", "expires_at": "2026-10-01T00:00:00Z",
            "status": "VERIFIED",
        }
        self.assertEqual("PRIME_SUPPORTED", self.packet(r, proofs=[proof])["requirement_results"][0]["state"])

    def test_wrong_proof_kind_rejected_at_schema(self):
        r = requirement("r1", required_proof_kind="POLICY_PROOF")
        with self.assertRaisesRegex(Error, "incompatible"):
            compile_req(r)

    def test_stale_pursuit_owner_input(self):
        r = requirement("r1")
        sr, c, d, rc = generation()
        q = request([pursuit("p1", [r], observed="2025-01-01T00:00:00Z")])
        p = json.loads(compile_gap(raw(q), sr, c, d, rc)[0])
        self.assertEqual("OWNER_INPUT", p["requirement_results"][0]["state"])
        self.assertIn("SOURCE_STALE", p["requirement_results"][0]["reasons"])

    def test_synthetic_source_never_live(self):
        r = requirement("r1")
        sr, c, d, rc = generation()
        q = request([pursuit("p1", [r], authority="SYNTHETIC_FIXTURE")], mode="SYNTHETIC_ONLY")
        p = json.loads(compile_gap(raw(q), sr, c, d, rc)[0])
        self.assertEqual("SYNTHETIC_ONLY", p["live_materialization_status"])
        self.assertEqual("OWNER_INPUT", p["requirement_results"][0]["state"])

    def test_fewer_than_five_retained_carriers_block_live_status(self):
        p = self.packet(requirement("r1"))
        self.assertEqual("LIVE_MATERIALIZATION_BLOCKED_NO_VERIFIED_CARRIER_SET", p["live_materialization_status"])

    def test_five_current_carriers_ready_for_owner_review(self):
        sr, c, d, rc = generation()
        ps = [pursuit(f"p{i}", [requirement(f"r{i}")]) for i in range(5)]
        p = json.loads(compile_gap(raw(request(ps)), sr, c, d, rc)[0])
        self.assertEqual("RETAINED_CURRENT_CARRIER_SET_READY_FOR_OWNER_REVIEW", p["live_materialization_status"])

    def test_internal_evidence_rechecked_at_pursuit_time(self):
        rec = source_record()
        rec["expires_at"] = "2026-09-16T00:30:00Z"
        rec["valid_until"] = "2026-09-16T00:30:00Z"
        r = requirement("r1", mapping_approval="APPROVED", internal_claim_id="claim-cap")
        p = self.packet(r, records=[rec])
        self.assertEqual("OWNER_INPUT", p["requirement_results"][0]["state"])
        self.assertIn("INTERNAL_EVIDENCE_EXPIRED", p["requirement_results"][0]["reasons"])
        self.assertIn("INTERNAL_MODULE_OUTSIDE_VALIDITY_WINDOW", p["requirement_results"][0]["reasons"])

    def test_future_materializer_generation_rejected(self):
        src = mat_source()
        src["generated_at"] = "2026-09-16T02:00:00Z"
        sr = raw(src)
        c, d, rc = materializer.compile_materializer(sr)
        q = raw(request([pursuit("p1", [requirement("r1")])]))
        with self.assertRaisesRegex(Error, "newer than request"):
            compile_gap(q, sr, c, d, rc)

    def test_materializer_generation_tamper_fails(self):
        r = requirement("r1")
        sr, c, d, rc = generation()
        with self.assertRaisesRegex(Error, "verification failed"):
            compile_gap(raw(request([pursuit("p1", [r])])), sr, c + b"x", d, rc)

    def test_packet_receipt_deterministic_and_verified(self):
        r = requirement("r1")
        sr, c, d, rc = generation()
        q = raw(request([pursuit("p1", [r])]))
        first = compile_gap(q, sr, c, d, rc)
        self.assertEqual(first, compile_gap(q, sr, c, d, rc))
        self.assertTrue(verify_gap(q, sr, c, d, rc, *first)["verified"])

    def test_packet_tamper_fails(self):
        r = requirement("r1")
        sr, c, d, rc = generation()
        q = raw(request([pursuit("p1", [r])]))
        p, receipt = compile_gap(q, sr, c, d, rc)
        with self.assertRaisesRegex(Error, "packet mismatch"):
            verify_gap(q, sr, c, d, rc, p + b"x", receipt)

    def test_receipt_tamper_fails(self):
        r = requirement("r1")
        sr, c, d, rc = generation()
        q = raw(request([pursuit("p1", [r])]))
        p, receipt = compile_gap(q, sr, c, d, rc)
        with self.assertRaisesRegex(Error, "receipt mismatch"):
            verify_gap(q, sr, c, d, rc, p, receipt + b"x")

    def test_duplicate_requirement_rejected_globally(self):
        sr, c, d, rc = generation()
        q = request([pursuit("p1", [requirement("r1")]), pursuit("p2", [requirement("r1")])])
        with self.assertRaisesRegex(Error, "duplicate global requirement_id"):
            compile_gap(raw(q), sr, c, d, rc)

    def test_orphan_prime_proof_rejected(self):
        proof = {
            "proof_id": "pp1", "requirement_id": "missing", "proof_kind": "CAPABILITY_PROOF",
            "source_ref": "https://prime.example/proof", "source_sha256": "c" * 64,
            "verified_at": "2026-09-15T00:00:00Z", "expires_at": "2026-10-01T00:00:00Z",
            "status": "VERIFIED",
        }
        sr, c, d, rc = generation()
        with self.assertRaisesRegex(Error, "orphan"):
            compile_gap(raw(request([pursuit("p1", [requirement("r1")])], [proof])), sr, c, d, rc)

    def test_requirement_text_hash_required(self):
        r = requirement("r1")
        r["text_sha256"] = "0" * 64
        with self.assertRaisesRegex(Error, "text_sha256 mismatch"):
            compile_req(r)

    def test_bool_partner_eligible_rejected(self):
        r = requirement("r1")
        r["partner_eligible"] = 1
        with self.assertRaisesRegex(Error, "bool required"):
            compile_req(r)

    def test_http_sources_rejected(self):
        sr, c, d, rc = generation()
        q = request([pursuit("p1", [requirement("r1")])])
        q["pursuits"][0]["source"]["uri"] = "http://buyer.example/p"
        with self.assertRaisesRegex(Error, "https URI"):
            compile_gap(raw(q), sr, c, d, rc)

    def test_duplicate_json_key_rejected(self):
        sr, c, d, rc = generation()
        with self.assertRaisesRegex(Error, "duplicate JSON key"):
            compile_gap(b'{"schema":"x","schema":"y"}', sr, c, d, rc)

    def test_noninteger_json_number_rejected(self):
        sr, c, d, rc = generation()
        with self.assertRaisesRegex(Error, "non-integer"):
            compile_gap(b'{"x":1.2}', sr, c, d, rc)

    def test_authority_all_false(self):
        p = self.packet(requirement("r1"))
        self.assertTrue(all(v is False for v in p["authority"].values()))
        self.assertFalse(p["partner_capability_shortlist"][0]["contact_authorized"])


if __name__ == "__main__":
    unittest.main()
