from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from revenue.reference_authority import reference_authority as ra

NOW = datetime(2026, 9, 14, 23, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 9, 15, 0, 0, 0, tzinfo=timezone.utc)
KEY_HEX = "11" * 32


def h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def evidence(eid: str) -> dict:
    return {
        "evidence_id": eid,
        "subject": f"Public safe subject {eid}",
        "performer": "Token Junkie Labs",
        "source_ref": f"https://example.test/evidence/{eid}",
        "source_sha256": h(f"source:{eid}"),
        "observed_result": f"Observed bounded result for {eid}",
        "limitations": ["No customer acceptance inferred", "No certification inferred"],
        "disclosure_summary": f"Bounded capability summary for {eid}",
    }


def packet(required_count: int = 1) -> dict:
    return {
        "schema_version": ra.SCHEMA_VERSION,
        "opportunity": {"opportunity_id": "opp-iowa", "title": "University assessment pursuit"},
        "requirements": [
            {
                "requirement_id": "refs-three",
                "opportunity_id": "opp-iowa",
                "label": "Comparable references",
                "required_count": required_count,
            }
        ],
        "evidence": [evidence(x) for x in ("client-one", "internal-tool", "oss-merge")],
    }


def registry_body(
    p: dict | None = None,
    *,
    sequence: int = 1,
    generation_id: str | None = None,
    issued_at: str = "2026-09-14T21:00:00Z",
) -> dict:
    p = p or packet()
    generation_id = generation_id or f"trust-gen-{sequence}"
    oppdig = ra.opportunity_digest(p["opportunity"])
    reqdig = ra.requirement_digest(p["requirements"][0])
    digs = {e["evidence_id"]: ra.evidence_digest(e) for e in p["evidence"]}
    kinds = {
        "client-one": ("eng-client-one", "CLIENT_ENGAGEMENT"),
        "internal-tool": ("eng-internal", "INTERNAL_ENGINEERING"),
        "oss-merge": ("eng-oss", "OPEN_SOURCE_CONTRIBUTION"),
    }
    classifications = []
    disclosures = []
    for eid, (engagement_id, kind) in kinds.items():
        if eid not in digs:
            continue
        classifications.append(
            {
                "classification_id": f"class-{eid}",
                "evidence_id": eid,
                "evidence_digest": digs[eid],
                "engagement_id": engagement_id,
                "engagement_kind": kind,
                "status": "CLASSIFIED",
                "observed_at": "2026-09-14T21:10:00Z",
                "expires_at": "2099-09-20T00:00:00Z",
                "authority_ref": f"opaque:classification-{eid}",
                "authority_sha256": h(f"class:{eid}"),
            }
        )
        disclosures.append(
            {
                "authority_id": f"disc-{eid}",
                "evidence_id": eid,
                "evidence_digest": digs[eid],
                "opportunity_id": "opp-iowa",
                "opportunity_digest": oppdig,
                "use_class": "PROPOSAL_CAPABILITY",
                "status": "AUTHORIZED",
                "observed_at": "2026-09-14T21:20:00Z",
                "expires_at": "2099-09-20T00:00:00Z",
                "authority_ref": f"opaque:disclosure-{eid}",
                "authority_sha256": h(f"disc:{eid}"),
            }
        )
    return {
        "schema_version": ra.TRUST_SCHEMA_VERSION,
        "key_id": ra.KEY_ID,
        "generation_id": generation_id,
        "generation_sequence": sequence,
        "issued_at": issued_at,
        "requirement_ids": ["refs-three"],
        "classifications": classifications,
        "disclosures": disclosures,
        "permissions": [
            {
                "permission_id": "perm-client-one",
                "evidence_id": "client-one",
                "evidence_digest": digs["client-one"],
                "opportunity_id": "opp-iowa",
                "opportunity_digest": oppdig,
                "requirement_id": "refs-three",
                "requirement_digest": reqdig,
                "status": "AUTHORIZED",
                "observed_at": "2026-09-14T21:30:00Z",
                "expires_at": "2099-09-20T00:00:00Z",
                "permission_ref": "opaque:permission-client-one",
                "permission_sha256": h("perm:client-one"),
            }
        ],
        "comparabilities": [
            {
                "assessment_id": "cmp-client-one",
                "evidence_id": "client-one",
                "evidence_digest": digs["client-one"],
                "opportunity_id": "opp-iowa",
                "opportunity_digest": oppdig,
                "requirement_id": "refs-three",
                "requirement_digest": reqdig,
                "status": "COMPARABLE",
                "assessed_at": "2026-09-14T21:40:00Z",
                "expires_at": "2099-09-20T00:00:00Z",
                "assessment_ref": "opaque:comparison-client-one",
                "assessment_sha256": h("cmp:client-one"),
            }
        ],
    }


def sign(body: dict) -> dict:
    return ra._sign_registry_for_tests(body, KEY_HEX)


def registry(p: dict | None = None, **kwargs) -> dict:
    return sign(registry_body(p, **kwargs))


def state(result: dict, eid: str, rid: str = "refs-three") -> dict:
    return next(
        x
        for x in result["reference_states"]
        if x["evidence_id"] == eid and x["requirement_id"] == rid
    )


class ReferenceAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.old_key = os.environ.get(ra.HOST_KEY_ENV)
        os.environ[ra.HOST_KEY_ENV] = KEY_HEX

    def tearDown(self) -> None:
        if self.old_key is None:
            os.environ.pop(ra.HOST_KEY_ENV, None)
        else:
            os.environ[ra.HOST_KEY_ENV] = self.old_key

    def compiled(self, p: dict | None = None, r: dict | None = None, now: datetime = NOW) -> dict:
        p = p or packet()
        return ra._compile_registry_at(p, r or registry(p), now)

    def test_complete_trusted_chain_ready_for_owner_review(self):
        result = self.compiled()
        self.assertEqual("REFERENCE_READY_FOR_OWNER_REVIEW", state(result, "client-one")["status"])
        self.assertEqual(1, result["requirements"][0]["eligible_count"])

    def test_non_client_kinds_never_satisfy_reference_count(self):
        result = self.compiled()
        for eid in ("internal-tool", "oss-merge"):
            self.assertEqual("HOLD", state(result, eid)["status"])
            self.assertIn("NOT_CLIENT_ENGAGEMENT", state(result, eid)["hold_reasons"])

    def test_capability_examples_can_include_non_client_work(self):
        result = self.compiled()
        ids = {x["evidence_id"] for x in result["capability_examples"]}
        self.assertTrue({"internal-tool", "oss-merge"} <= ids)

    def test_candidate_packet_cannot_carry_authority(self):
        p = packet(); p["permissions"] = []
        with self.assertRaisesRegex(ra.ReferenceAuthorityError, "unknown fields"):
            self.compiled(p, registry())

    def test_candidate_packet_cannot_select_engagement_kind(self):
        p = packet(); p["evidence"][0]["engagement_kind"] = "CLIENT_ENGAGEMENT"
        with self.assertRaisesRegex(ra.ReferenceAuthorityError, "unknown fields"):
            self.compiled(p, registry())

    def test_random_mac_is_rejected(self):
        forged = registry_body()
        forged["mac"] = {"algorithm": "HMAC-SHA256", "key_id": ra.KEY_ID, "sha256": "0" * 64}
        with self.assertRaisesRegex(ra.ReferenceAuthorityError, "MAC verification failed"):
            self.compiled(packet(), forged)

    def test_authenticated_registry_tamper_is_rejected(self):
        r = registry(); r["permissions"][0]["status"] = "REVOKED"
        with self.assertRaisesRegex(ra.ReferenceAuthorityError, "MAC verification failed"):
            self.compiled(packet(), r)

    def test_missing_host_key_fails_closed(self):
        os.environ.pop(ra.HOST_KEY_ENV, None)
        with self.assertRaisesRegex(ra.ReferenceAuthorityError, "host key unavailable"):
            self.compiled(packet(), registry())

    def test_missing_permission_holds(self):
        b = registry_body(); b["permissions"] = []
        self.assertIn("MISSING_REFERENCE_PERMISSION", state(self.compiled(r=sign(b)), "client-one")["hold_reasons"])

    def test_missing_comparability_holds(self):
        b = registry_body(); b["comparabilities"] = []
        self.assertIn("MISSING_COMPARABILITY_AUTHORITY", state(self.compiled(r=sign(b)), "client-one")["hold_reasons"])

    def test_capability_narrative_is_not_reference_permission(self):
        b = registry_body()
        next(x for x in b["disclosures"] if x["evidence_id"] == "client-one")["use_class"] = "CAPABILITY_NARRATIVE"
        result = self.compiled(r=sign(b))
        self.assertIn("DISCLOSURE_NOT_PROPOSAL_CAPABILITY", state(result, "client-one")["hold_reasons"])
        self.assertIn("client-one", {x["evidence_id"] for x in result["capability_examples"]})

    def test_permission_evidence_digest_mismatch_holds(self):
        b = registry_body(); b["permissions"][0]["evidence_digest"] = "0" * 64
        self.assertIn("REFERENCE_PERMISSION_EVIDENCE_DIGEST_MISMATCH", state(self.compiled(r=sign(b)), "client-one")["hold_reasons"])

    def test_expired_permission_holds(self):
        b = registry_body(); b["permissions"][0]["expires_at"] = "2026-09-14T22:00:00Z"
        self.assertIn("EXPIRED_REFERENCE_PERMISSION", state(self.compiled(r=sign(b)), "client-one")["hold_reasons"])

    def test_future_permission_holds(self):
        b = registry_body(); b["permissions"][0]["observed_at"] = "2026-09-15T01:00:00Z"
        self.assertIn("FUTURE_REFERENCE_PERMISSION", state(self.compiled(r=sign(b)), "client-one")["hold_reasons"])

    def test_revocation_overrides_older_permission(self):
        b = registry_body(); old = b["permissions"][0]
        b["permissions"].append({**old, "permission_id": "perm-revoke", "status": "REVOKED", "observed_at": "2026-09-14T22:30:00Z", "permission_sha256": h("revoke")})
        self.assertIn("REFERENCE_PERMISSION_REVOKED", state(self.compiled(r=sign(b)), "client-one")["hold_reasons"])

    def test_requirement_generation_change_holds_old_authority(self):
        p = packet(); p["requirements"][0]["label"] = "Different criterion under same id"
        reasons = state(self.compiled(p, registry()), "client-one")["hold_reasons"]
        self.assertIn("REFERENCE_PERMISSION_REQUIREMENT_DIGEST_MISMATCH", reasons)
        self.assertIn("COMPARABILITY_AUTHORITY_REQUIREMENT_DIGEST_MISMATCH", reasons)

    def test_opportunity_generation_change_holds_old_authority(self):
        p = packet(); p["opportunity"]["title"] = "Different opportunity under same id"
        reasons = state(self.compiled(p, registry()), "client-one")["hold_reasons"]
        self.assertIn("DISCLOSURE_AUTHORITY_OPPORTUNITY_DIGEST_MISMATCH", reasons)

    def test_untrusted_renamed_alias_does_not_count(self):
        p = packet(); clone = copy.deepcopy(p["evidence"][0]); clone["evidence_id"] = "client-one-clone"; p["evidence"].append(clone)
        result = self.compiled(p, registry())
        self.assertIn("MISSING_ENGAGEMENT_CLASSIFICATION", state(result, "client-one-clone")["hold_reasons"])

    def test_trusted_aliases_same_engagement_count_once(self):
        p = packet(required_count=2)
        clone = copy.deepcopy(p["evidence"][0]); clone["evidence_id"] = "client-one-clone"; p["evidence"].append(clone)
        b = registry_body(p)
        dig = ra.evidence_digest(clone); oppdig = ra.opportunity_digest(p["opportunity"]); reqdig = ra.requirement_digest(p["requirements"][0])
        b["classifications"].append({"classification_id":"class-clone","evidence_id":"client-one-clone","evidence_digest":dig,"engagement_id":"eng-client-one","engagement_kind":"CLIENT_ENGAGEMENT","status":"CLASSIFIED","observed_at":"2026-09-14T21:10:00Z","expires_at":"2099-09-20T00:00:00Z","authority_ref":"opaque:class-clone","authority_sha256":h("class-clone")})
        b["disclosures"].append({"authority_id":"disc-clone","evidence_id":"client-one-clone","evidence_digest":dig,"opportunity_id":"opp-iowa","opportunity_digest":oppdig,"use_class":"PROPOSAL_CAPABILITY","status":"AUTHORIZED","observed_at":"2026-09-14T21:20:00Z","expires_at":"2099-09-20T00:00:00Z","authority_ref":"opaque:disc-clone","authority_sha256":h("disc-clone")})
        b["permissions"].append({"permission_id":"perm-clone","evidence_id":"client-one-clone","evidence_digest":dig,"opportunity_id":"opp-iowa","opportunity_digest":oppdig,"requirement_id":"refs-three","requirement_digest":reqdig,"status":"AUTHORIZED","observed_at":"2026-09-14T21:30:00Z","expires_at":"2099-09-20T00:00:00Z","permission_ref":"opaque:perm-clone","permission_sha256":h("perm-clone")})
        b["comparabilities"].append({"assessment_id":"cmp-clone","evidence_id":"client-one-clone","evidence_digest":dig,"opportunity_id":"opp-iowa","opportunity_digest":oppdig,"requirement_id":"refs-three","requirement_digest":reqdig,"status":"COMPARABLE","assessed_at":"2026-09-14T21:40:00Z","expires_at":"2099-09-20T00:00:00Z","assessment_ref":"opaque:cmp-clone","assessment_sha256":h("cmp-clone")})
        result = self.compiled(p, sign(b))
        self.assertEqual(1, result["requirements"][0]["eligible_count"])
        self.assertEqual("HOLD_INSUFFICIENT_REFERENCES", result["requirements"][0]["status"])

    def test_engagement_id_conflicting_kind_is_rejected(self):
        b = registry_body(); row = copy.deepcopy(b["classifications"][1]); row["classification_id"] = "class-conflict"; row["engagement_id"] = "eng-client-one"; row["engagement_kind"] = "INTERNAL_ENGINEERING"; b["classifications"].append(row)
        with self.assertRaisesRegex(ra.ReferenceAuthorityError, "conflicting engagement kinds"):
            sign(b)

    def test_generation_sequence_bool_and_zero_rejected(self):
        for bad in (True, 0, -1):
            b = registry_body(); b["generation_sequence"] = bad
            with self.assertRaisesRegex(ra.ReferenceAuthorityError, "generation_sequence"):
                sign(b)

    def test_duplicate_json_keys_and_nonfinite_numbers_rejected(self):
        with self.assertRaisesRegex(ra.ReferenceAuthorityError, "duplicate JSON key"):
            ra.strict_json_loads('{"x":1,"x":2}')
        for raw in ('{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}'):
            with self.assertRaisesRegex(ra.ReferenceAuthorityError, "non-finite"):
                ra.strict_json_loads(raw)

    def test_public_fields_reject_contact_secret_and_path_shapes(self):
        for bad in ("person@example.com", "555-123-4567", "api_key=abcdefgh", "/home/user/private"):
            p = packet(); p["opportunity"]["title"] = bad
            with self.assertRaises(ra.ReferenceAuthorityError):
                ra.normalize_packet(p)

    def test_output_authority_is_all_false(self):
        result = self.compiled()
        self.assertTrue(result["authority"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_historical_verification_binds_exact_generation_and_sequence(self):
        p = packet(); r = registry(); result = self.compiled(p, r)
        checked = ra.verify_historical(p, r, result)
        self.assertEqual("VERIFIED_HISTORICAL_INTEGRITY_ONLY", checked["status"])
        self.assertEqual(1, checked["authority_registry_generation_sequence"])
        newer = registry(sequence=2, generation_id="trust-gen-2", issued_at="2026-09-14T22:00:00Z")
        with self.assertRaisesRegex(ra.ReferenceAuthorityError, "historical authority registry generation mismatch"):
            ra.verify_historical(p, newer, result)

    def test_private_current_helper_honors_new_revocation_generation(self):
        p = packet(); old = registry(); result = self.compiled(p, old)
        b = registry_body(sequence=2, generation_id="trust-gen-2", issued_at="2026-09-14T22:00:00Z")
        prior = b["permissions"][0]
        b["permissions"].append({**prior, "permission_id":"perm-revoke-2", "status":"REVOKED", "observed_at":"2026-09-14T23:30:00Z", "permission_sha256":h("revoke-2")})
        checked = ra._verify_current_at(p, old, sign(b), result, LATER)
        self.assertIn("REFERENCE_PERMISSION_REVOKED", state(checked["current"], "client-one")["hold_reasons"])

    def test_current_lineage_rejects_signed_rollback(self):
        p = packet(); hist = registry(sequence=2, generation_id="g2", issued_at="2026-09-14T22:00:00Z"); result = self.compiled(p, hist)
        old = registry(sequence=1, generation_id="g1", issued_at="2026-09-14T21:00:00Z")
        with self.assertRaisesRegex(ra.ReferenceAuthorityError, "rollback"):
            ra._verify_current_at(p, hist, old, result, LATER)

    def test_current_lineage_rejects_same_sequence_fork(self):
        p = packet(); hist = registry(); result = self.compiled(p, hist)
        b = registry_body(); b["permissions"][0]["permission_sha256"] = h("fork")
        with self.assertRaisesRegex(ra.ReferenceAuthorityError, "same-sequence fork"):
            ra._verify_current_at(p, hist, sign(b), result, LATER)

    def test_current_lineage_rejects_same_sequence_different_generation_id(self):
        p = packet(); hist = registry(); result = self.compiled(p, hist)
        other = registry(sequence=1, generation_id="other-gen")
        with self.assertRaisesRegex(ra.ReferenceAuthorityError, "same-sequence fork"):
            ra._verify_current_at(p, hist, other, result, LATER)

    def test_current_lineage_rejects_generation_id_reuse(self):
        p = packet(); hist = registry(); result = self.compiled(p, hist)
        newer = registry(sequence=2, generation_id="trust-gen-1", issued_at="2026-09-14T22:00:00Z")
        with self.assertRaisesRegex(ra.ReferenceAuthorityError, "reused generation_id"):
            ra._verify_current_at(p, hist, newer, result, LATER)

    def test_current_lineage_rejects_nonlater_issued_at(self):
        p = packet(); hist = registry(); result = self.compiled(p, hist)
        newer = registry(sequence=2, generation_id="trust-gen-2", issued_at="2026-09-14T21:00:00Z")
        with self.assertRaisesRegex(ra.ReferenceAuthorityError, "later issued_at"):
            ra._verify_current_at(p, hist, newer, result, LATER)

    def test_same_exact_current_generation_is_allowed(self):
        p = packet(); hist = registry(); result = self.compiled(p, hist)
        checked = ra._verify_current_at(p, hist, hist, result, LATER)
        self.assertEqual("VERIFIED_WITH_FRESH_HOST_TIME_REASSESSMENT", checked["status"])
        self.assertEqual(1, checked["current_registry"]["generation_sequence"])

    def test_public_verify_has_no_current_registry_or_clock_argument(self):
        p = packet(); hist = registry(); result = self.compiled(p, hist)
        with self.assertRaises(TypeError):
            ra.verify_current(p, hist, hist, result)
        with self.assertRaises(TypeError):
            ra.verify_current(p, hist, result, trusted_now=NOW)

    def test_host_current_store_reader_rejects_symlink_leaf(self):
        if os.name != "posix" or not hasattr(os, "O_NOFOLLOW"):
            self.skipTest("POSIX nofollow required")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); real = root / "real.json"; link = root / "link.json"
            real.write_text(json.dumps(registry()), encoding="utf-8"); link.symlink_to(real)
            with mock.patch.object(ra, "HOST_CURRENT_REGISTRY_PATH", link):
                with self.assertRaisesRegex(ra.ReferenceAuthorityError, "cannot open trusted current authority registry"):
                    ra._read_host_current_registry()

    def test_public_verify_uses_host_store_and_honors_revocation(self):
        if os.name != "posix" or not hasattr(os, "O_NOFOLLOW"):
            self.skipTest("POSIX retained store required")
        p = packet(); hist = registry(); result = self.compiled(p, hist)
        b = registry_body(sequence=2, generation_id="trust-gen-2", issued_at="2026-09-14T22:00:00Z")
        prior = b["permissions"][0]
        b["permissions"].append({**prior, "permission_id":"perm-revoke-2", "status":"REVOKED", "observed_at":"2026-09-14T22:30:00Z", "permission_sha256":h("revoke-2")})
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "current.json"; path.write_text(json.dumps(sign(b)), encoding="utf-8")
            with mock.patch.object(ra, "HOST_CURRENT_REGISTRY_PATH", path), mock.patch.object(ra, "_now", return_value=LATER):
                checked = ra.verify_current(p, hist, result)
        self.assertIn("REFERENCE_PERMISSION_REVOKED", state(checked["current"], "client-one")["hold_reasons"])

    def test_host_store_tamper_fails_mac(self):
        if os.name != "posix" or not hasattr(os, "O_NOFOLLOW"):
            self.skipTest("POSIX retained store required")
        r = registry(); r["permissions"][0]["status"] = "REVOKED"
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "current.json"; path.write_text(json.dumps(r), encoding="utf-8")
            with mock.patch.object(ra, "HOST_CURRENT_REGISTRY_PATH", path):
                loaded = ra._read_host_current_registry()
                with self.assertRaisesRegex(ra.ReferenceAuthorityError, "MAC verification failed"):
                    ra.normalize_authority_registry(loaded)

    def test_write_does_not_unlink_foreign_replacement_after_failure(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "out.json"
            class Exploder:
                def __init__(self, fd): self.fd = fd
                def __enter__(self): return self
                def write(self, data):
                    os.close(self.fd); path.unlink(); path.write_text("replacement", encoding="utf-8"); raise OSError("boom")
                def flush(self): pass
                def fileno(self): return self.fd
                def __exit__(self, *args): return False
            with mock.patch.object(ra.os, "fdopen", side_effect=lambda fd, mode: Exploder(fd)):
                with self.assertRaises(OSError): ra._write(path, b"ours")
            self.assertEqual("replacement", path.read_text(encoding="utf-8"))

    def test_render_markdown_keeps_authority_ceiling(self):
        md = ra.render_markdown(self.compiled())
        self.assertIn("Authority ceiling", md)
        self.assertIn("does not authorize disclosure", md)


if __name__ == "__main__":
    unittest.main()
