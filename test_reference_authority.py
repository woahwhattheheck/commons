from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from revenue.reference_authority.reference_authority import (
    ReferenceAuthorityError,
    canonical_bytes,
    compile_registry,
    evidence_digest,
    opportunity_digest,
    requirement_digest,
    record_digest,
    render_markdown,
    strict_json_loads,
    verify_current,
    verify_historical,
)

NOW = datetime(2026, 9, 13, 13, 40, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parent
MODULE = ROOT / "revenue" / "reference_authority" / "reference_authority.py"

def h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def evidence(eid: str, kind: str) -> dict:
    return {
        "evidence_id": eid,
        "engagement_kind": kind,
        "subject": f"Public-safe subject {eid}",
        "performer": "Token Junkie Labs",
        "source_ref": f"https://example.test/evidence/{eid}",
        "source_sha256": h(f"source:{eid}"),
        "observed_result": f"Observed bounded result for {eid}",
        "limitations": ["No customer acceptance inferred", "No certification inferred"],
        "disclosure_summary": f"Bounded capability summary for {eid}",
    }


def packet() -> dict:
    items = [
        evidence("client-one", "CLIENT_ENGAGEMENT"),
        evidence("client-two", "CLIENT_ENGAGEMENT"),
        evidence("internal-tool", "INTERNAL_ENGINEERING"),
        evidence("oss-merge", "OPEN_SOURCE_CONTRIBUTION"),
        evidence("paid-review", "EXTERNAL_REVIEW_PROGRAM"),
        evidence("proposal-only", "PROCUREMENT_PURSUIT"),
    ]
    digs = {e["evidence_id"]: evidence_digest(e) for e in items}
    opp = {"opportunity_id": "opp-iowa", "title": "University assessment pursuit"}
    req = {"requirement_id": "refs-three", "opportunity_id": "opp-iowa", "label": "Three comparable references", "required_count": 3}
    oppdig = opportunity_digest(opp)
    reqdig = requirement_digest(req)
    disclosures = []
    for eid in digs:
        disclosures.append({
            "authority_id": f"disc-{eid}",
            "evidence_id": eid,
            "evidence_digest": digs[eid],
            "opportunity_id": "opp-iowa",
            "opportunity_digest": oppdig,
            "use_class": "PROPOSAL_CAPABILITY",
            "status": "AUTHORIZED",
            "observed_at": "2026-09-13T12:00:00Z",
            "expires_at": "2026-09-20T00:00:00Z",
            "authority_ref": f"https://example.test/authority/disclosure/{eid}",
            "authority_sha256": h(f"disc:{eid}"),
        })
    permissions = [{
        "permission_id": "perm-client-one",
        "evidence_id": "client-one",
        "evidence_digest": digs["client-one"],
        "opportunity_id": "opp-iowa",
        "opportunity_digest": oppdig,
        "requirement_id": "refs-three",
        "requirement_digest": reqdig,
        "status": "AUTHORIZED",
        "observed_at": "2026-09-13T12:10:00Z",
        "expires_at": "2026-09-20T00:00:00Z",
        "permission_ref": "https://example.test/authority/permission/client-one",
        "permission_sha256": h("perm:client-one"),
    }]
    comparisons = [{
        "assessment_id": "cmp-client-one",
        "evidence_id": "client-one",
        "evidence_digest": digs["client-one"],
        "opportunity_id": "opp-iowa",
        "opportunity_digest": oppdig,
        "requirement_id": "refs-three",
        "requirement_digest": reqdig,
        "status": "COMPARABLE",
        "assessed_at": "2026-09-13T12:20:00Z",
        "expires_at": "2026-09-20T00:00:00Z",
        "assessment_ref": "https://example.test/authority/comparison/client-one",
        "assessment_sha256": h("cmp:client-one"),
    }]
    return {
        "schema_version": "commons-reference-authority/v1",
        "opportunity": opp,
        "requirements": [req],
        "evidence": items,
        "disclosure_authorities": disclosures,
        "reference_permissions": permissions,
        "comparability_authorities": comparisons,
    }


def state(result: dict, eid: str, rid: str = "refs-three") -> dict:
    return next(x for x in result["reference_states"] if x["evidence_id"] == eid and x["requirement_id"] == rid)


class ReferenceAuthorityTests(unittest.TestCase):
    def test_client_with_complete_chain_is_ready_for_owner_review(self):
        result = compile_registry(packet(), trusted_now=NOW)
        self.assertEqual("REFERENCE_READY_FOR_OWNER_REVIEW", state(result, "client-one")["status"])
        self.assertEqual(["client-one"], result["requirements"][0]["eligible_reference_ids"])
        self.assertEqual("HOLD_INSUFFICIENT_REFERENCES", result["requirements"][0]["status"])

    def test_capability_kinds_never_satisfy_reference_count(self):
        result = compile_registry(packet(), trusted_now=NOW)
        for eid in ("internal-tool", "oss-merge", "paid-review", "proposal-only"):
            self.assertEqual("HOLD", state(result, eid)["status"])
            self.assertIn("NOT_CLIENT_ENGAGEMENT", state(result, eid)["hold_reasons"])

    def test_capability_items_remain_useful_as_disclosed_examples(self):
        result = compile_registry(packet(), trusted_now=NOW)
        capability_ids = {x["evidence_id"] for x in result["capability_examples"]}
        self.assertTrue({"internal-tool", "oss-merge", "paid-review", "proposal-only"} <= capability_ids)

    def test_client_without_permission_holds(self):
        p = packet()
        p["reference_permissions"] = []
        result = compile_registry(p, trusted_now=NOW)
        self.assertIn("MISSING_REFERENCE_PERMISSION", state(result, "client-one")["hold_reasons"])

    def test_client_without_comparability_holds(self):
        p = packet()
        p["comparability_authorities"] = []
        result = compile_registry(p, trusted_now=NOW)
        self.assertIn("MISSING_COMPARABILITY_AUTHORITY", state(result, "client-one")["hold_reasons"])

    def test_capability_narrative_does_not_authorize_named_reference(self):
        p = packet()
        p["disclosure_authorities"][0]["use_class"] = "CAPABILITY_NARRATIVE"
        result = compile_registry(p, trusted_now=NOW)
        self.assertIn("DISCLOSURE_NOT_PROPOSAL_CAPABILITY", state(result, "client-one")["hold_reasons"])
        self.assertIn("client-one", {x["evidence_id"] for x in result["capability_examples"]})

    def test_permission_digest_tamper_holds(self):
        p = packet()
        p["reference_permissions"][0]["evidence_digest"] = "0" * 64
        result = compile_registry(p, trusted_now=NOW)
        self.assertIn("REFERENCE_PERMISSION_EVIDENCE_DIGEST_MISMATCH", state(result, "client-one")["hold_reasons"])

    def test_comparability_digest_tamper_holds(self):
        p = packet()
        p["comparability_authorities"][0]["evidence_digest"] = "0" * 64
        result = compile_registry(p, trusted_now=NOW)
        self.assertIn("COMPARABILITY_AUTHORITY_EVIDENCE_DIGEST_MISMATCH", state(result, "client-one")["hold_reasons"])

    def test_disclosure_digest_tamper_holds(self):
        p = packet()
        p["disclosure_authorities"][0]["evidence_digest"] = "0" * 64
        result = compile_registry(p, trusted_now=NOW)
        self.assertIn("DISCLOSURE_AUTHORITY_EVIDENCE_DIGEST_MISMATCH", state(result, "client-one")["hold_reasons"])

    def test_expired_permission_does_not_stay_current(self):
        p = packet()
        p["reference_permissions"][0]["expires_at"] = "2026-09-13T13:00:00Z"
        result = compile_registry(p, trusted_now=NOW)
        self.assertIn("EXPIRED_REFERENCE_PERMISSION", state(result, "client-one")["hold_reasons"])

    def test_future_permission_holds(self):
        p = packet()
        p["reference_permissions"][0]["observed_at"] = "2026-09-13T14:00:00Z"
        result = compile_registry(p, trusted_now=NOW)
        self.assertIn("FUTURE_REFERENCE_PERMISSION", state(result, "client-one")["hold_reasons"])

    def test_revocation_overrides_older_permission(self):
        p = packet()
        old = p["reference_permissions"][0]
        p["reference_permissions"].append({**old, "permission_id": "perm-client-one-revoke", "status": "REVOKED", "observed_at": "2026-09-13T13:00:00Z", "permission_sha256": h("revoke")})
        result = compile_registry(p, trusted_now=NOW)
        self.assertIn("REFERENCE_PERMISSION_REVOKED", state(result, "client-one")["hold_reasons"])

    def test_not_comparable_overrides_older_comparison(self):
        p = packet()
        old = p["comparability_authorities"][0]
        p["comparability_authorities"].append({**old, "assessment_id": "cmp-client-one-no", "status": "NOT_COMPARABLE", "assessed_at": "2026-09-13T13:00:00Z", "assessment_sha256": h("not-comparable")})
        result = compile_registry(p, trusted_now=NOW)
        self.assertIn("COMPARABILITY_AUTHORITY_NOT_COMPARABLE", state(result, "client-one")["hold_reasons"])

    def test_revoked_disclosure_removes_capability_and_reference(self):
        p = packet()
        old = p["disclosure_authorities"][0]
        p["disclosure_authorities"].append({**old, "authority_id": "disc-client-one-revoke", "status": "REVOKED", "observed_at": "2026-09-13T13:00:00Z", "authority_sha256": h("revoke-disc")})
        result = compile_registry(p, trusted_now=NOW)
        self.assertIn("DISCLOSURE_AUTHORITY_REVOKED", state(result, "client-one")["hold_reasons"])
        self.assertNotIn("client-one", {x["evidence_id"] for x in result["capability_examples"]})

    def test_cross_opportunity_permission_cannot_be_replayed(self):
        p = packet()
        p["reference_permissions"][0]["opportunity_id"] = "opp-other"
        with self.assertRaisesRegex(ReferenceAuthorityError, "does not match packet opportunity"):
            compile_registry(p, trusted_now=NOW)

    def test_cross_requirement_permission_cannot_be_replayed(self):
        p = packet()
        p["reference_permissions"][0]["requirement_id"] = "refs-other"
        with self.assertRaisesRegex(ReferenceAuthorityError, "requirement_id unknown"):
            compile_registry(p, trusted_now=NOW)

    def test_cross_requirement_comparability_cannot_be_replayed(self):
        p = packet()
        p["comparability_authorities"][0]["requirement_id"] = "refs-other"
        with self.assertRaisesRegex(ReferenceAuthorityError, "requirement_id unknown"):
            compile_registry(p, trusted_now=NOW)

    def test_requirement_label_generation_change_holds_old_authority(self):
        p = packet()
        p["requirements"][0]["label"] = "Materially different reference criterion under same stable id"
        result = compile_registry(p, trusted_now=NOW)
        reasons = state(result, "client-one")["hold_reasons"]
        self.assertIn("REFERENCE_PERMISSION_REQUIREMENT_DIGEST_MISMATCH", reasons)
        self.assertIn("COMPARABILITY_AUTHORITY_REQUIREMENT_DIGEST_MISMATCH", reasons)

    def test_requirement_count_generation_change_holds_old_authority(self):
        p = packet()
        p["requirements"][0]["required_count"] = 1
        result = compile_registry(p, trusted_now=NOW)
        reasons = state(result, "client-one")["hold_reasons"]
        self.assertIn("REFERENCE_PERMISSION_REQUIREMENT_DIGEST_MISMATCH", reasons)
        self.assertIn("COMPARABILITY_AUTHORITY_REQUIREMENT_DIGEST_MISMATCH", reasons)
        self.assertEqual("HOLD_INSUFFICIENT_REFERENCES", result["requirements"][0]["status"])

    def test_opportunity_generation_change_holds_all_old_authority(self):
        p = packet()
        p["opportunity"]["title"] = "Different opportunity generation under same stable id"
        result = compile_registry(p, trusted_now=NOW)
        reasons = state(result, "client-one")["hold_reasons"]
        self.assertIn("DISCLOSURE_AUTHORITY_OPPORTUNITY_DIGEST_MISMATCH", reasons)
        self.assertIn("REFERENCE_PERMISSION_OPPORTUNITY_DIGEST_MISMATCH", reasons)
        self.assertIn("COMPARABILITY_AUTHORITY_OPPORTUNITY_DIGEST_MISMATCH", reasons)
        self.assertNotIn("client-one", {x["evidence_id"] for x in result["capability_examples"]})

    def test_second_real_client_can_satisfy_only_with_full_chain(self):
        p = packet()
        e2 = next(x for x in p["evidence"] if x["evidence_id"] == "client-two")
        d2 = evidence_digest(e2)
        p["reference_permissions"].append({**p["reference_permissions"][0], "permission_id": "perm-client-two", "evidence_id": "client-two", "evidence_digest": d2, "permission_ref": "https://example.test/authority/permission/client-two", "permission_sha256": h("perm:client-two")})
        p["comparability_authorities"].append({**p["comparability_authorities"][0], "assessment_id": "cmp-client-two", "evidence_id": "client-two", "evidence_digest": d2, "assessment_ref": "https://example.test/authority/comparison/client-two", "assessment_sha256": h("cmp:client-two")})
        result = compile_registry(p, trusted_now=NOW)
        self.assertEqual(["client-one", "client-two"], result["requirements"][0]["eligible_reference_ids"])
        self.assertEqual(2, result["requirements"][0]["eligible_count"])

    def test_order_invariant_bytes(self):
        p1 = packet()
        p2 = packet()
        for key in ("requirements", "evidence", "disclosure_authorities", "reference_permissions", "comparability_authorities"):
            p2[key] = list(reversed(p2[key]))
        r1 = compile_registry(p1, trusted_now=NOW)
        r2 = compile_registry(p2, trusted_now=NOW)
        self.assertEqual(canonical_bytes(r1), canonical_bytes(r2))

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(ReferenceAuthorityError, "duplicate JSON key"):
            strict_json_loads('{"a":1,"a":2}')

    def test_unknown_field_rejected(self):
        p = packet()
        p["unknown"] = 1
        with self.assertRaisesRegex(ReferenceAuthorityError, "unknown fields"):
            compile_registry(p, trusted_now=NOW)

    def test_bool_as_int_required_count_rejected(self):
        p = packet()
        p["requirements"][0]["required_count"] = True
        with self.assertRaisesRegex(ReferenceAuthorityError, "bool forbidden"):
            compile_registry(p, trusted_now=NOW)

    def test_email_contact_pii_rejected(self):
        p = packet()
        p["evidence"][0]["performer"] = "person@example.com"
        with self.assertRaisesRegex(ReferenceAuthorityError, "email/contact PII"):
            compile_registry(p, trusted_now=NOW)

    def test_phone_contact_pii_rejected(self):
        p = packet()
        p["evidence"][0]["observed_result"] = "Call +1 (555) 555-1212 for details"
        with self.assertRaisesRegex(ReferenceAuthorityError, "phone/contact PII"):
            compile_registry(p, trusted_now=NOW)

    def test_opaque_authority_reference_supported(self):
        p = packet()
        p["reference_permissions"][0]["permission_ref"] = "opaque:permission-client-one"
        result = compile_registry(p, trusted_now=NOW)
        self.assertEqual("REFERENCE_READY_FOR_OWNER_REVIEW", state(result, "client-one")["status"])

    def test_opaque_authority_reference_syntax_rejected(self):
        p = packet()
        p["reference_permissions"][0]["permission_ref"] = "opaque:../../private"
        with self.assertRaisesRegex(ReferenceAuthorityError, "invalid opaque authority handle"):
            compile_registry(p, trusted_now=NOW)

    def test_secret_shaped_text_rejected(self):
        p = packet()
        p["evidence"][0]["observed_result"] = "api_key=abcdefghijk"
        with self.assertRaisesRegex(ReferenceAuthorityError, "credential-shaped"):
            compile_registry(p, trusted_now=NOW)

    def test_private_path_shaped_text_rejected(self):
        p = packet()
        p["evidence"][0]["observed_result"] = "See /home/alice/private.txt"
        with self.assertRaisesRegex(ReferenceAuthorityError, "path-shaped"):
            compile_registry(p, trusted_now=NOW)

    def test_non_https_ref_rejected(self):
        p = packet()
        p["evidence"][0]["source_ref"] = "file:///tmp/evidence"
        with self.assertRaisesRegex(ReferenceAuthorityError, "public https"):
            compile_registry(p, trusted_now=NOW)

    def test_bad_digest_rejected(self):
        p = packet()
        p["evidence"][0]["source_sha256"] = "abc"
        with self.assertRaisesRegex(ReferenceAuthorityError, "SHA-256"):
            compile_registry(p, trusted_now=NOW)

    def test_historical_receipt_verifies(self):
        p = packet()
        result = compile_registry(p, trusted_now=NOW)
        verified = verify_historical(p, result)
        self.assertEqual("VERIFIED_HISTORICAL_INTEGRITY_ONLY", verified["status"])

    def test_receipt_tamper_fails(self):
        p = packet()
        result = compile_registry(p, trusted_now=NOW)
        result["requirements"][0]["eligible_count"] = 99
        with self.assertRaisesRegex(ReferenceAuthorityError, "receipt SHA-256 mismatch"):
            verify_historical(p, result)

    def test_current_reassessment_drops_expired_old_receipt(self):
        p = packet()
        p["reference_permissions"][0]["expires_at"] = "2026-09-13T13:50:00Z"
        old = compile_registry(p, trusted_now=NOW)
        self.assertEqual("REFERENCE_READY_FOR_OWNER_REVIEW", state(old, "client-one")["status"])
        later = datetime(2026, 9, 13, 14, 0, 0, tzinfo=timezone.utc)
        verified = verify_current(p, old, trusted_now=later)
        self.assertEqual("HOLD", state(verified["current"], "client-one")["status"])
        self.assertIn("EXPIRED_REFERENCE_PERMISSION", state(verified["current"], "client-one")["hold_reasons"])

    def test_output_authority_is_all_false(self):
        result = compile_registry(packet(), trusted_now=NOW)
        self.assertTrue(result["authority"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_markdown_does_not_claim_send_or_permission_request(self):
        text = render_markdown(compile_registry(packet(), trusted_now=NOW))
        self.assertIn("REFERENCE_READY_FOR_OWNER_REVIEW", text)
        self.assertIn("does not authorize disclosure, contact, submission", text)
        self.assertNotIn("permission requested", text.lower())

    def test_cli_compile_create_exclusive_and_verify(self):
        p = packet()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            packet_path = td / "packet.json"
            result_path = td / "result.json"
            md_path = td / "result.md"
            packet_path.write_text(json.dumps(p), encoding="utf-8")
            first = subprocess.run([sys.executable, str(MODULE), "compile", str(packet_path), "--json-out", str(result_path), "--markdown-out", str(md_path)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, first.returncode, first.stderr)
            self.assertTrue(result_path.exists())
            self.assertTrue(md_path.exists())
            verify = subprocess.run([sys.executable, str(MODULE), "verify", str(packet_path), str(result_path)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, verify.returncode, verify.stderr)
            self.assertIn("VERIFIED_WITH_FRESH_CURRENT_REASSESSMENT", verify.stdout)
            second = subprocess.run([sys.executable, str(MODULE), "compile", str(packet_path), "--json-out", str(result_path), "--markdown-out", str(md_path)], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(0, second.returncode)

    def test_optimized_python_suite_can_import_and_compile(self):
        code = "from revenue.reference_authority.reference_authority import compile_registry; print(callable(compile_registry))"
        proc = subprocess.run([sys.executable, "-O", "-c", code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual("True", proc.stdout.strip())


if __name__ == "__main__":
    unittest.main()
