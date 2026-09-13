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
from unittest import mock

from revenue.reference_authority import reference_authority as ra
from revenue.reference_authority.reference_authority import (
    HOST_KEY_ENV,
    ReferenceAuthorityError,
    canonical_bytes,
    compile_registry,
    evidence_digest,
    opportunity_digest,
    record_digest,
    render_markdown,
    requirement_digest,
    strict_json_loads,
    verify_current,
    verify_historical,
)

NOW = datetime(2026, 9, 13, 13, 40, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 9, 13, 14, 0, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parent
MODULE = ROOT / "revenue" / "reference_authority" / "reference_authority.py"
KEY_HEX = "11" * 32


def h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def evidence(eid: str) -> dict:
    return {
        "evidence_id": eid,
        "subject": f"Public-safe subject {eid}",
        "performer": "Token Junkie Labs",
        "source_ref": f"https://example.test/evidence/{eid}",
        "source_sha256": h(f"source:{eid}"),
        "observed_result": f"Observed bounded result for {eid}",
        "limitations": ["No customer acceptance inferred", "No certification inferred"],
        "disclosure_summary": f"Bounded capability summary for {eid}",
    }


def packet() -> dict:
    return {
        "schema_version": "commons-reference-authority/v2",
        "opportunity": {"opportunity_id": "opp-iowa", "title": "University assessment pursuit"},
        "requirements": [{"requirement_id": "refs-three", "opportunity_id": "opp-iowa", "label": "Three comparable references", "required_count": 3}],
        "evidence": [evidence(x) for x in ("client-one", "client-two", "internal-tool", "oss-merge", "paid-review", "proposal-only")],
    }


def registry_body(p: dict | None = None) -> dict:
    p = p or packet()
    oppdig = opportunity_digest(p["opportunity"])
    reqdig = requirement_digest(p["requirements"][0])
    kinds = {
        "client-one": ("eng-client-one", "CLIENT_ENGAGEMENT"),
        "client-two": ("eng-client-two", "CLIENT_ENGAGEMENT"),
        "internal-tool": ("eng-internal", "INTERNAL_ENGINEERING"),
        "oss-merge": ("eng-oss", "OPEN_SOURCE_CONTRIBUTION"),
        "paid-review": ("eng-review", "EXTERNAL_REVIEW_PROGRAM"),
        "proposal-only": ("eng-proposal", "PROCUREMENT_PURSUIT"),
    }
    digs = {e["evidence_id"]: evidence_digest(e) for e in p["evidence"]}
    classifications = []
    disclosures = []
    for eid, (engid, kind) in kinds.items():
        if eid not in digs:
            continue
        classifications.append({
            "classification_id": f"class-{eid}", "evidence_id": eid, "evidence_digest": digs[eid],
            "engagement_id": engid, "engagement_kind": kind, "status": "CLASSIFIED",
            "observed_at": "2026-09-13T12:00:00Z", "expires_at": "2099-09-20T00:00:00Z",
            "authority_ref": f"opaque:classification-{eid}", "authority_sha256": h(f"class:{eid}"),
        })
        disclosures.append({
            "authority_id": f"disc-{eid}", "evidence_id": eid, "evidence_digest": digs[eid],
            "opportunity_id": "opp-iowa", "opportunity_digest": oppdig,
            "use_class": "PROPOSAL_CAPABILITY", "status": "AUTHORIZED",
            "observed_at": "2026-09-13T12:00:00Z", "expires_at": "2099-09-20T00:00:00Z",
            "authority_ref": f"opaque:disclosure-{eid}", "authority_sha256": h(f"disc:{eid}"),
        })
    return {
        "schema_version": "commons-reference-authority-trust/v1",
        "key_id": "commons-reference-authority-host-v1",
        "generation_id": "trust-gen-1",
        "issued_at": "2026-09-13T12:30:00Z",
        "requirement_ids": ["refs-three"],
        "classifications": classifications,
        "disclosures": disclosures,
        "permissions": [{
            "permission_id": "perm-client-one", "evidence_id": "client-one", "evidence_digest": digs["client-one"],
            "opportunity_id": "opp-iowa", "opportunity_digest": oppdig,
            "requirement_id": "refs-three", "requirement_digest": reqdig,
            "status": "AUTHORIZED", "observed_at": "2026-09-13T12:10:00Z", "expires_at": "2099-09-20T00:00:00Z",
            "permission_ref": "opaque:permission-client-one", "permission_sha256": h("perm:client-one"),
        }],
        "comparabilities": [{
            "assessment_id": "cmp-client-one", "evidence_id": "client-one", "evidence_digest": digs["client-one"],
            "opportunity_id": "opp-iowa", "opportunity_digest": oppdig,
            "requirement_id": "refs-three", "requirement_digest": reqdig,
            "status": "COMPARABLE", "assessed_at": "2026-09-13T12:20:00Z", "expires_at": "2099-09-20T00:00:00Z",
            "assessment_ref": "opaque:comparison-client-one", "assessment_sha256": h("cmp:client-one"),
        }],
    }


def sign(body: dict) -> dict:
    return ra._sign_registry_for_tests(body, KEY_HEX)


def registry(p: dict | None = None) -> dict:
    return sign(registry_body(p))


def state(result: dict, eid: str, rid: str = "refs-three") -> dict:
    return next(x for x in result["reference_states"] if x["evidence_id"] == eid and x["requirement_id"] == rid)


class ReferenceAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.old_key = os.environ.get(HOST_KEY_ENV)
        os.environ[HOST_KEY_ENV] = KEY_HEX

    def tearDown(self):
        if self.old_key is None:
            os.environ.pop(HOST_KEY_ENV, None)
        else:
            os.environ[HOST_KEY_ENV] = self.old_key

    def compiled(self, p=None, r=None, now=NOW):
        return ra._compile_registry_at(p or packet(), r or registry(p), now)

    def test_complete_trusted_chain_ready_for_owner_review(self):
        result = self.compiled()
        self.assertEqual("REFERENCE_READY_FOR_OWNER_REVIEW", state(result, "client-one")["status"])
        self.assertEqual(1, result["requirements"][0]["eligible_count"])
        self.assertEqual("eng-client-one", result["requirements"][0]["eligible_references"][0]["engagement_id"])

    def test_non_client_kinds_never_satisfy_reference_count(self):
        result = self.compiled()
        for eid in ("internal-tool", "oss-merge", "paid-review", "proposal-only"):
            self.assertEqual("HOLD", state(result, eid)["status"])
            self.assertIn("NOT_CLIENT_ENGAGEMENT", state(result, eid)["hold_reasons"])

    def test_capability_kinds_remain_disclosable_examples(self):
        result = self.compiled()
        ids = {x["evidence_id"] for x in result["capability_examples"]}
        self.assertTrue({"internal-tool", "oss-merge", "paid-review", "proposal-only"} <= ids)

    def test_candidate_packet_cannot_carry_authority_rows(self):
        p = packet(); p["permissions"] = []
        with self.assertRaisesRegex(ReferenceAuthorityError, "unknown fields"):
            self.compiled(p, registry())

    def test_candidate_packet_cannot_choose_engagement_kind(self):
        p = packet(); p["evidence"][0]["engagement_kind"] = "CLIENT_ENGAGEMENT"
        with self.assertRaisesRegex(ReferenceAuthorityError, "unknown fields"):
            self.compiled(p, registry())

    def test_self_authored_registry_random_mac_rejected(self):
        forged = registry_body(); forged["mac"] = {"algorithm":"HMAC-SHA256","key_id":"commons-reference-authority-host-v1","sha256":"0"*64}
        with self.assertRaisesRegex(ReferenceAuthorityError, "MAC verification failed"):
            self.compiled(packet(), forged)

    def test_authenticated_registry_tamper_rejected(self):
        r = registry(); r["permissions"][0]["status"] = "REVOKED"
        with self.assertRaisesRegex(ReferenceAuthorityError, "MAC verification failed"):
            self.compiled(packet(), r)

    def test_missing_host_key_fails_closed(self):
        os.environ.pop(HOST_KEY_ENV, None)
        with self.assertRaisesRegex(ReferenceAuthorityError, "host key unavailable"):
            self.compiled(packet(), registry())

    def test_client_without_permission_holds(self):
        b = registry_body(); b["permissions"] = []
        self.assertIn("MISSING_REFERENCE_PERMISSION", state(self.compiled(r=sign(b)), "client-one")["hold_reasons"])

    def test_client_without_comparability_holds(self):
        b = registry_body(); b["comparabilities"] = []
        self.assertIn("MISSING_COMPARABILITY_AUTHORITY", state(self.compiled(r=sign(b)), "client-one")["hold_reasons"])

    def test_capability_narrative_is_not_reference_permission(self):
        b = registry_body(); next(x for x in b["disclosures"] if x["evidence_id"]=="client-one")["use_class"] = "CAPABILITY_NARRATIVE"
        result = self.compiled(r=sign(b))
        self.assertIn("DISCLOSURE_NOT_PROPOSAL_CAPABILITY", state(result, "client-one")["hold_reasons"])
        self.assertIn("client-one", {x["evidence_id"] for x in result["capability_examples"]})

    def test_permission_evidence_digest_mismatch_holds(self):
        b=registry_body(); b["permissions"][0]["evidence_digest"]="0"*64
        self.assertIn("REFERENCE_PERMISSION_EVIDENCE_DIGEST_MISMATCH", state(self.compiled(r=sign(b)),"client-one")["hold_reasons"])

    def test_classification_evidence_digest_mismatch_holds(self):
        b=registry_body(); next(x for x in b["classifications"] if x["evidence_id"]=="client-one")["evidence_digest"]="0"*64
        self.assertIn("ENGAGEMENT_CLASSIFICATION_EVIDENCE_DIGEST_MISMATCH", state(self.compiled(r=sign(b)),"client-one")["hold_reasons"])

    def test_expired_permission_holds(self):
        b=registry_body(); b["permissions"][0]["expires_at"]="2026-09-13T13:00:00Z"
        self.assertIn("EXPIRED_REFERENCE_PERMISSION", state(self.compiled(r=sign(b)),"client-one")["hold_reasons"])

    def test_future_permission_holds(self):
        b=registry_body(); b["permissions"][0]["observed_at"]="2026-09-13T14:00:00Z"
        self.assertIn("FUTURE_REFERENCE_PERMISSION", state(self.compiled(r=sign(b)),"client-one")["hold_reasons"])

    def test_revocation_overrides_older_permission(self):
        b=registry_body(); old=b["permissions"][0]; b["permissions"].append({**old,"permission_id":"perm-revoke","status":"REVOKED","observed_at":"2026-09-13T13:00:00Z","permission_sha256":h("revoke")})
        self.assertIn("REFERENCE_PERMISSION_REVOKED", state(self.compiled(r=sign(b)),"client-one")["hold_reasons"])

    def test_not_comparable_overrides_older_assessment(self):
        b=registry_body(); old=b["comparabilities"][0]; b["comparabilities"].append({**old,"assessment_id":"cmp-no","status":"NOT_COMPARABLE","assessed_at":"2026-09-13T13:00:00Z","assessment_sha256":h("no")})
        self.assertIn("COMPARABILITY_AUTHORITY_NOT_COMPARABLE", state(self.compiled(r=sign(b)),"client-one")["hold_reasons"])

    def test_revoked_classification_blocks_reference_and_capability(self):
        b=registry_body(); old=next(x for x in b["classifications"] if x["evidence_id"]=="client-one"); b["classifications"].append({**old,"classification_id":"class-client-one-revoke","status":"REVOKED","observed_at":"2026-09-13T13:00:00Z","authority_sha256":h("class-revoke")})
        result=self.compiled(r=sign(b)); self.assertIn("ENGAGEMENT_CLASSIFICATION_REVOKED", state(result,"client-one")["hold_reasons"]); self.assertNotIn("client-one",{x["evidence_id"] for x in result["capability_examples"]})

    def test_requirement_label_generation_change_holds_old_authority(self):
        p=packet(); p["requirements"][0]["label"]="Different reference criterion under same stable id"
        reasons=state(self.compiled(p,registry()),"client-one")["hold_reasons"]
        self.assertIn("REFERENCE_PERMISSION_REQUIREMENT_DIGEST_MISMATCH",reasons); self.assertIn("COMPARABILITY_AUTHORITY_REQUIREMENT_DIGEST_MISMATCH",reasons)

    def test_requirement_count_generation_change_holds_old_authority(self):
        p=packet(); p["requirements"][0]["required_count"]=1
        result=self.compiled(p,registry()); reasons=state(result,"client-one")["hold_reasons"]
        self.assertIn("REFERENCE_PERMISSION_REQUIREMENT_DIGEST_MISMATCH",reasons); self.assertEqual("HOLD_INSUFFICIENT_REFERENCES",result["requirements"][0]["status"])

    def test_opportunity_generation_change_holds_old_authority(self):
        p=packet(); p["opportunity"]["title"]="Different opportunity generation under same id"
        reasons=state(self.compiled(p,registry()),"client-one")["hold_reasons"]
        self.assertIn("DISCLOSURE_AUTHORITY_OPPORTUNITY_DIGEST_MISMATCH",reasons); self.assertIn("REFERENCE_PERMISSION_OPPORTUNITY_DIGEST_MISMATCH",reasons)

    def test_untrusted_renamed_alias_has_no_classification(self):
        p=packet(); clone=copy.deepcopy(p["evidence"][0]); clone["evidence_id"]="client-one-clone"; p["evidence"].append(clone)
        result=self.compiled(p,registry()); self.assertIn("MISSING_ENGAGEMENT_CLASSIFICATION",state(result,"client-one-clone")["hold_reasons"])

    def test_two_trusted_evidence_aliases_same_engagement_count_once(self):
        p=packet(); clone=copy.deepcopy(p["evidence"][0]); clone["evidence_id"]="client-one-clone"; p["evidence"].append(clone); p["requirements"][0]["required_count"]=2
        b=registry_body(p); dig=evidence_digest(clone); oppdig=opportunity_digest(p["opportunity"]); reqdig=requirement_digest(p["requirements"][0])
        # registry_body(p) cannot auto-classify the clone; add a trusted alias explicitly.
        b["classifications"].append({"classification_id":"class-client-one-clone","evidence_id":"client-one-clone","evidence_digest":dig,"engagement_id":"eng-client-one","engagement_kind":"CLIENT_ENGAGEMENT","status":"CLASSIFIED","observed_at":"2026-09-13T12:00:00Z","expires_at":"2099-09-20T00:00:00Z","authority_ref":"opaque:class-clone","authority_sha256":h("class-clone")})
        b["disclosures"].append({"authority_id":"disc-client-one-clone","evidence_id":"client-one-clone","evidence_digest":dig,"opportunity_id":"opp-iowa","opportunity_digest":oppdig,"use_class":"PROPOSAL_CAPABILITY","status":"AUTHORIZED","observed_at":"2026-09-13T12:00:00Z","expires_at":"2099-09-20T00:00:00Z","authority_ref":"opaque:disc-clone","authority_sha256":h("disc-clone")})
        b["permissions"].append({"permission_id":"perm-client-one-clone","evidence_id":"client-one-clone","evidence_digest":dig,"opportunity_id":"opp-iowa","opportunity_digest":oppdig,"requirement_id":"refs-three","requirement_digest":reqdig,"status":"AUTHORIZED","observed_at":"2026-09-13T12:10:00Z","expires_at":"2099-09-20T00:00:00Z","permission_ref":"opaque:perm-clone","permission_sha256":h("perm-clone")})
        b["comparabilities"].append({"assessment_id":"cmp-client-one-clone","evidence_id":"client-one-clone","evidence_digest":dig,"opportunity_id":"opp-iowa","opportunity_digest":oppdig,"requirement_id":"refs-three","requirement_digest":reqdig,"status":"COMPARABLE","assessed_at":"2026-09-13T12:20:00Z","expires_at":"2099-09-20T00:00:00Z","assessment_ref":"opaque:cmp-clone","assessment_sha256":h("cmp-clone")})
        result=self.compiled(p,sign(b)); self.assertEqual(1,result["requirements"][0]["eligible_count"]); self.assertEqual("HOLD_INSUFFICIENT_REFERENCES",result["requirements"][0]["status"]); self.assertEqual(["client-one","client-one-clone"],result["requirements"][0]["eligible_references"][0]["evidence_ids"])

    def test_second_distinct_trusted_engagement_counts_separately(self):
        p=packet(); p["requirements"][0]["required_count"]=2; b=registry_body(p); e2=next(x for x in p["evidence"] if x["evidence_id"]=="client-two"); d2=evidence_digest(e2); oppdig=opportunity_digest(p["opportunity"]); reqdig=requirement_digest(p["requirements"][0])
        b["permissions"].append({**b["permissions"][0],"permission_id":"perm-client-two","evidence_id":"client-two","evidence_digest":d2,"opportunity_digest":oppdig,"requirement_digest":reqdig,"permission_ref":"opaque:perm-client-two","permission_sha256":h("perm2")})
        b["comparabilities"].append({**b["comparabilities"][0],"assessment_id":"cmp-client-two","evidence_id":"client-two","evidence_digest":d2,"opportunity_digest":oppdig,"requirement_digest":reqdig,"assessment_ref":"opaque:cmp-client-two","assessment_sha256":h("cmp2")})
        result=self.compiled(p,sign(b)); self.assertEqual(2,result["requirements"][0]["eligible_count"]); self.assertEqual("SATISFIED_FOR_OWNER_REVIEW",result["requirements"][0]["status"])

    def test_order_invariant_packet_and_registry(self):
        p1=packet(); b1=registry_body(p1); p2=copy.deepcopy(p1); p2["evidence"].reverse(); b2=copy.deepcopy(b1)
        for key in ("classifications","disclosures","permissions","comparabilities"): b2[key].reverse()
        self.assertEqual(canonical_bytes(self.compiled(p1,sign(b1))),canonical_bytes(self.compiled(p2,sign(b2))))

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(ReferenceAuthorityError,"duplicate JSON key"): strict_json_loads('{"a":1,"a":2}')

    def test_unknown_packet_field_rejected(self):
        p=packet(); p["unknown"]=1
        with self.assertRaisesRegex(ReferenceAuthorityError,"unknown fields"): self.compiled(p,registry())

    def test_bool_as_int_rejected(self):
        p=packet(); p["requirements"][0]["required_count"]=True
        with self.assertRaisesRegex(ReferenceAuthorityError,"bool forbidden"): self.compiled(p,registry())

    def test_email_contact_pii_rejected(self):
        p=packet(); p["evidence"][0]["performer"]="person@example.com"
        with self.assertRaisesRegex(ReferenceAuthorityError,"email/contact PII"): self.compiled(p,registry())

    def test_phone_contact_pii_rejected(self):
        p=packet(); p["evidence"][0]["observed_result"]="Call +1 (555) 555-1212 for details"
        with self.assertRaisesRegex(ReferenceAuthorityError,"phone/contact PII"): self.compiled(p,registry())

    def test_opaque_authority_refs_work_only_inside_authenticated_registry(self):
        self.assertEqual("REFERENCE_READY_FOR_OWNER_REVIEW",state(self.compiled(),"client-one")["status"])

    def test_bad_opaque_authority_ref_rejected_before_mac(self):
        b=registry_body(); b["permissions"][0]["permission_ref"]="opaque:../../private"
        with self.assertRaisesRegex(ReferenceAuthorityError,"invalid opaque authority handle"): sign(b)

    def test_secret_shaped_candidate_text_rejected(self):
        p=packet(); p["evidence"][0]["observed_result"]="api_key=abcdefghijk"
        with self.assertRaisesRegex(ReferenceAuthorityError,"credential-shaped"): self.compiled(p,registry())

    def test_private_path_shaped_candidate_text_rejected(self):
        p=packet(); p["evidence"][0]["observed_result"]="See /home/alice/private.txt"
        with self.assertRaisesRegex(ReferenceAuthorityError,"path-shaped"): self.compiled(p,registry())

    def test_non_https_evidence_ref_rejected(self):
        p=packet(); p["evidence"][0]["source_ref"]="file:///tmp/evidence"
        with self.assertRaisesRegex(ReferenceAuthorityError,"public https"): self.compiled(p,registry())

    def test_bad_digest_rejected(self):
        p=packet(); p["evidence"][0]["source_sha256"]="abc"
        with self.assertRaisesRegex(ReferenceAuthorityError,"SHA-256"): self.compiled(p,registry())

    def test_future_registry_generation_rejected(self):
        b=registry_body(); b["issued_at"]="2026-09-13T14:00:00Z"
        with self.assertRaisesRegex(ReferenceAuthorityError,"generation is from the future"): self.compiled(r=sign(b))

    def test_registry_requirement_admission_must_cover_packet(self):
        b=registry_body(); b["requirement_ids"]=[]; b["permissions"]=[]; b["comparabilities"]=[]
        with self.assertRaisesRegex(ReferenceAuthorityError,"does not admit every packet requirement"): self.compiled(r=sign(b))

    def test_historical_receipt_verifies_against_exact_trusted_generation(self):
        p=packet(); r=registry(); result=self.compiled(p,r)
        self.assertEqual("VERIFIED_HISTORICAL_INTEGRITY_ONLY",verify_historical(p,r,result)["status"])

    def test_receipt_tamper_fails(self):
        p=packet(); r=registry(); result=self.compiled(p,r); result["requirements"][0]["eligible_count"]=99
        with self.assertRaisesRegex(ReferenceAuthorityError,"receipt SHA-256 mismatch"): verify_historical(p,r,result)

    def test_historical_registry_substitution_fails(self):
        p=packet(); old=registry(); result=self.compiled(p,old); b=registry_body(); b["generation_id"]="trust-gen-2"; new=sign(b)
        with self.assertRaisesRegex(ReferenceAuthorityError,"historical authority registry generation mismatch"): verify_historical(p,new,result)

    def test_current_reassessment_can_use_new_revocation_generation(self):
        p=packet(); old=registry(); result=self.compiled(p,old); b=registry_body(); b["generation_id"]="trust-gen-2"; oldperm=b["permissions"][0]; b["permissions"].append({**oldperm,"permission_id":"perm-revoke","status":"REVOKED","observed_at":"2026-09-13T13:50:00Z","permission_sha256":h("revoke2")}); new=sign(b)
        checked=ra._verify_current_at(p,old,new,result,LATER); self.assertEqual("VERIFIED_WITH_FRESH_HOST_TIME_REASSESSMENT",checked["status"]); self.assertIn("REFERENCE_PERMISSION_REVOKED",state(checked["current"],"client-one")["hold_reasons"])

    def test_public_current_verifier_has_no_clock_injection(self):
        p=packet(); r=registry(); result=self.compiled(p,r)
        with self.assertRaises(TypeError): verify_current(p,r,r,result,trusted_now=NOW)

    def test_public_compile_has_no_clock_injection(self):
        with self.assertRaises(TypeError): compile_registry(packet(),registry(),trusted_now=NOW)

    def test_output_authority_is_all_false(self):
        result=self.compiled(); self.assertTrue(result["authority"]); self.assertTrue(all(v is False for v in result["authority"].values()))

    def test_markdown_states_authenticated_non_authorizing_boundary(self):
        text=render_markdown(self.compiled()); self.assertIn("Trusted authority generation",text); self.assertIn("distinct trusted engagements",text); self.assertIn("does not authorize disclosure, contact, submission",text)

    def test_failed_write_never_unlinks_pathname_replacement(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"out"; real_fdopen=os.fdopen
            class Exploder:
                def __init__(self,fd): self.fd=fd
                def __enter__(self): return self
                def write(self,data):
                    os.close(self.fd); path.unlink(); path.write_text("replacement",encoding="utf-8"); raise OSError("boom")
                def flush(self): pass
                def fileno(self): return self.fd
                def __exit__(self,*args): return False
            with mock.patch.object(ra.os,"fdopen",side_effect=lambda fd,mode: Exploder(fd)):
                with self.assertRaises(OSError): ra._write(path,b"ours")
            self.assertEqual("replacement",path.read_text(encoding="utf-8"))

    def test_cli_compile_and_current_verify(self):
        p=packet(); r=registry()
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); pp=td/"packet.json"; rp=td/"registry.json"; out=td/"result.json"; md=td/"result.md"; pp.write_text(json.dumps(p)); rp.write_text(json.dumps(r)); env={**os.environ,HOST_KEY_ENV:KEY_HEX}
            first=subprocess.run([sys.executable,str(MODULE),"compile",str(pp),str(rp),"--json-out",str(out),"--markdown-out",str(md)],cwd=ROOT,env=env,capture_output=True,text=True); self.assertEqual(0,first.returncode,first.stderr)
            verify=subprocess.run([sys.executable,str(MODULE),"verify",str(pp),str(rp),str(out)],cwd=ROOT,env=env,capture_output=True,text=True); self.assertEqual(0,verify.returncode,verify.stderr); self.assertIn("VERIFIED_WITH_FRESH_HOST_TIME_REASSESSMENT",verify.stdout)

    def test_cli_forged_registry_fails_hold(self):
        p=packet(); forged=registry_body(); forged["mac"]={"algorithm":"HMAC-SHA256","key_id":"commons-reference-authority-host-v1","sha256":"0"*64}
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); pp=td/"packet.json"; rp=td/"registry.json"; out=td/"result.json"; md=td/"result.md"; pp.write_text(json.dumps(p)); rp.write_text(json.dumps(forged)); env={**os.environ,HOST_KEY_ENV:KEY_HEX}
            proc=subprocess.run([sys.executable,str(MODULE),"compile",str(pp),str(rp),"--json-out",str(out),"--markdown-out",str(md)],cwd=ROOT,env=env,capture_output=True,text=True); self.assertEqual(2,proc.returncode); self.assertIn('"status": "HOLD"',proc.stderr); self.assertFalse(out.exists())

    def test_cli_create_exclusive_preflight(self):
        p=packet(); r=registry()
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); pp=td/"packet.json"; rp=td/"registry.json"; out=td/"result.json"; md=td/"result.md"; pp.write_text(json.dumps(p)); rp.write_text(json.dumps(r)); out.write_text("existing"); env={**os.environ,HOST_KEY_ENV:KEY_HEX}
            proc=subprocess.run([sys.executable,str(MODULE),"compile",str(pp),str(rp),"--json-out",str(out),"--markdown-out",str(md)],cwd=ROOT,env=env,capture_output=True,text=True); self.assertEqual(2,proc.returncode); self.assertEqual("existing",out.read_text())

    def test_optimized_python_imports(self):
        proc=subprocess.run([sys.executable,"-O","-c","from revenue.reference_authority.reference_authority import compile_registry,verify_current; print(callable(compile_registry) and callable(verify_current))"],cwd=ROOT,capture_output=True,text=True); self.assertEqual(0,proc.returncode,proc.stderr); self.assertEqual("True",proc.stdout.strip())


if __name__ == "__main__":
    unittest.main()
