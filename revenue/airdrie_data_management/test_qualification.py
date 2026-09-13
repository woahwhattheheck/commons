import copy
import unittest
from unittest.mock import patch

import qualification as q


NOTICE = {
    "solicitation_id": "AB-2026-06233",
    "buyer": "City of Airdrie",
    "title": "Data Management Consultant",
    "reported_deadline_local": "2026-10-06 20:00 (timezone unverified)",
    "discovery_sources": [
        {"uri": "https://example.invalid/a", "source_type": "procurement-index"},
        {"uri": "https://example.invalid/b", "source_type": "procurement-index"},
    ],
}


def packet():
    return {"notice": copy.deepcopy(NOTICE), "requirements": [], "evidence": []}


def source(sid="sol", sha="a" * 64, **kw):
    out = {
        "source_id": sid,
        "sha256": sha,
        "authority": q.TRUSTED_AUTHORITY,
        "current": True,
        "scope_complete": True,
        "deadline_utc": "2026-10-07T02:00:00Z",
        "kind": "SOLICITATION",
        "supersedes": [],
    }
    out.update(kw)
    return out


def evidence(eid="e1", status="PROVEN", **kw):
    out = {"evidence_id": eid, "status": status}
    if status == "PROVEN":
        out.update({"artifact_ref": "repo:path", "artifact_sha256": "b" * 64})
    out.update(kw)
    return out


def requirement(rid="r1", eid="e1", source_id="sol", source_sha="a" * 64, classification="MANDATORY"):
    return {
        "requirement_id": rid,
        "source_id": source_id,
        "source_sha256": source_sha,
        "classification": classification,
        "locator": "Section 1",
        "text": "Demonstrated requirement",
        "evidence_ids": [] if eid is None else [eid],
    }


class QualificationTests(unittest.TestCase):
    def future(self):
        return patch("qualification._utc_now", return_value=q.datetime(2026, 9, 13, tzinfo=q.timezone.utc))

    def expired(self):
        return patch("qualification._utc_now", return_value=q.datetime(2026, 10, 7, tzinfo=q.timezone.utc))

    def test_discovery_can_only_hold(self):
        with self.future():
            self.assertEqual("HOLD_CONTROLLING_PACK_REQUIRED", q.evaluate_discovery(packet())["status"])

    def test_discovery_stays_hold_even_after_reported_date(self):
        with self.expired():
            self.assertEqual("HOLD_CONTROLLING_PACK_REQUIRED", q.evaluate_discovery(packet())["status"])

    def test_trusted_deadline_reverify(self):
        s = source(deadline_utc="2026-10-06T20:00:00Z")
        with self.expired():
            self.assertEqual("HOLD_DEADLINE_REVERIFY", q.evaluate_with_trusted_sources(packet(), [s])["status"])

    def test_notice_identity_drift_is_invalid(self):
        p = packet(); p["notice"]["buyer"] = "Someone Else"
        with self.future():
            self.assertEqual("INVALID", q.evaluate_discovery(p)["status"])

    def test_duplicate_discovery_source_invalid(self):
        p = packet(); p["notice"]["discovery_sources"][1]["uri"] = p["notice"]["discovery_sources"][0]["uri"]
        with self.future():
            self.assertEqual("INVALID", q.evaluate_discovery(p)["status"])

    def test_trusted_pack_without_extraction_holds(self):
        with self.future():
            self.assertEqual(
                "HOLD_REQUIREMENT_EXTRACTION_REQUIRED",
                q.evaluate_with_trusted_sources(packet(), [source()])["status"],
            )

    def test_untrusted_authority_invalid(self):
        with self.future():
            self.assertEqual(
                "INVALID",
                q.evaluate_with_trusted_sources(packet(), [source(authority="CALLER")])["status"],
            )

    def test_source_hash_shape_invalid(self):
        with self.future():
            self.assertEqual("INVALID", q.evaluate_with_trusted_sources(packet(), [source(sha="AA")])["status"])

    def test_two_current_complete_solicitations_invalid(self):
        with self.future():
            self.assertEqual(
                "INVALID",
                q.evaluate_with_trusted_sources(packet(), [source("s1"), source("s2", sha="c" * 64)])["status"],
            )

    def test_supersession_requires_old_noncurrent(self):
        old = source("old", scope_complete=False)
        new = source("new", sha="c" * 64, supersedes=["old"])
        with self.future():
            self.assertEqual("INVALID", q.evaluate_with_trusted_sources(packet(), [old, new])["status"])

    def test_requirement_cannot_bind_superseded_source(self):
        old = source("old", current=False, scope_complete=False)
        new = source("sol", supersedes=["old"])
        p = packet(); p["evidence"] = [evidence()]; p["requirements"] = [requirement(source_id="old")]
        with self.future():
            self.assertEqual("INVALID", q.evaluate_with_trusted_sources(p, [old, new])["status"])

    def test_requirement_source_sha_must_match(self):
        p = packet(); p["evidence"] = [evidence()]; p["requirements"] = [requirement(source_sha="f" * 64)]
        with self.future():
            self.assertEqual("INVALID", q.evaluate_with_trusted_sources(p, [source()])["status"])

    def test_missing_mandatory_evidence_holds(self):
        p = packet(); p["requirements"] = [requirement(eid=None)]
        with self.future():
            receipt = q.evaluate_with_trusted_sources(p, [source()])
        self.assertEqual("HOLD_MANDATORY_GAPS", receipt["status"])
        self.assertFalse(receipt.get("submission_authorized", False))

    def test_unknown_mandatory_evidence_holds(self):
        p = packet(); p["evidence"] = [evidence(status="UNKNOWN")]; p["requirements"] = [requirement()]
        with self.future():
            self.assertEqual("HOLD_MANDATORY_GAPS", q.evaluate_with_trusted_sources(p, [source()])["status"])

    def test_all_mandatory_proven_only_ready_for_owner_review(self):
        p = packet(); p["evidence"] = [evidence()]; p["requirements"] = [requirement()]
        with self.future():
            receipt = q.evaluate_with_trusted_sources(p, [source()])
        self.assertEqual("READY_FOR_OWNER_REVIEW", receipt["status"])
        self.assertIs(receipt["submission_authorized"], False)
        self.assertIn("no buyer contact", receipt["authority"])

    def test_duplicate_requirement_invalid(self):
        p = packet(); p["evidence"] = [evidence()]; p["requirements"] = [requirement(), requirement()]
        with self.future():
            self.assertEqual("INVALID", q.evaluate_with_trusted_sources(p, [source()])["status"])

    def test_duplicate_evidence_invalid(self):
        p = packet(); p["evidence"] = [evidence(), evidence()]; p["requirements"] = [requirement()]
        with self.future():
            self.assertEqual("INVALID", q.evaluate_with_trusted_sources(p, [source()])["status"])

    def test_bool_not_accepted_as_current(self):
        s = source(); s["current"] = 1
        with self.future():
            self.assertEqual("INVALID", q.evaluate_with_trusted_sources(packet(), [s])["status"])

    def test_cli_surface_has_no_trusted_source_argument(self):
        p = packet()
        p["trusted_sources"] = [source()]
        with self.future():
            self.assertEqual("HOLD_CONTROLLING_PACK_REQUIRED", q.evaluate_discovery(p)["status"])


if __name__ == "__main__":
    unittest.main()
