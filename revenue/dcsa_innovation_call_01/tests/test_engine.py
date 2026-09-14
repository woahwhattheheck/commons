from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import sys
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import engine  # noqa: E402

FIXED_NOW = datetime(2026, 9, 14, 5, 0, tzinfo=timezone.utc)
DEADLINE = "2026-09-18T13:00:00Z"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.files = {}
        for name in ["call", "sol", "template", "fcl", "cit", "secret", "t5"]:
            p = self.root / f"{name}.txt"
            p.write_text(f"fixture-{name}\n", encoding="utf-8")
            self.files[name] = p

    def tearDown(self):
        self.tmp.cleanup()

    def source(self, kind: str, key: str):
        p = self.files[key]
        return {"kind": kind, "url": f"https://example.test/{key}", "captured_at": "2026-09-14T04:00:00Z", "path": str(p), "sha256": digest(p)}

    def evidence(self, eid: str, etype: str, key: str):
        p = self.files[key]
        return {"id": eid, "type": etype, "subject": "candidate", "status": "evidenced", "observed_at": "2026-09-14T04:00:00Z", "expires_at": "2027-01-01T00:00:00Z", "issuer_or_source": "fixture", "path": str(p), "sha256": digest(p)}

    def packet(self):
        return {
            "opportunity": "DCSAInnovationCall01",
            "concept_paper_deadline": DEADLINE,
            "source_max_age_hours": 72,
            "sources": [
                self.source("innovation_call", "call"),
                self.source("general_solicitation", "sol"),
                self.source("concept_paper_template", "template"),
            ],
            "architecture_domains": sorted(engine.REQUIRED_ARCHITECTURE_DOMAINS),
            "privileged_users_in_scope": True,
            "eligibility_evidence": [],
            "teaming_targets": [{"name": "iWorks", "signals": ["current_dcsa_nb_is_work", "identity_application_modernization", "small_business", "public_partner_route"]}],
        }

    def evaluate(self, packet):
        with patch.object(engine, "_utc_now", return_value=FIXED_NOW):
            return engine.evaluate(packet)

    def test_missing_direct_evidence_is_teaming_required(self):
        r = self.evaluate(self.packet())
        self.assertEqual(r["state"], "TEAMING_REQUIRED")
        self.assertTrue(any(x.startswith("DIRECT_EVIDENCE_MISSING:") for x in r["holds"]))

    def test_all_direct_evidence_ready(self):
        p = self.packet()
        p["eligibility_evidence"] = [
            self.evidence("f", "facility_clearance_top_secret", "fcl"),
            self.evidence("c", "personnel_us_citizenship", "cit"),
            self.evidence("s", "personnel_interim_secret_or_higher", "secret"),
            self.evidence("t", "privileged_user_t5_or_allowed_interim", "t5"),
        ]
        r = self.evaluate(p)
        self.assertEqual(r["state"], "DIRECT_READY")
        self.assertFalse(r["authority_ceiling"]["clearance_truth_certified"])
        self.assertFalse(r["authority_ceiling"]["government_submission_authorized"])

    def test_stale_source_holds(self):
        p = self.packet()
        p["sources"][0]["captured_at"] = "2026-08-01T00:00:00Z"
        r = self.evaluate(p)
        self.assertEqual(r["state"], "HOLD")
        self.assertIn("SOURCE_STALE:innovation_call", r["holds"])

    def test_missing_architecture_holds(self):
        p = self.packet()
        p["architecture_domains"] = ["unified_access_shell"]
        r = self.evaluate(p)
        self.assertEqual(r["state"], "HOLD")
        self.assertIn("ARCHITECTURE_DOMAIN_MISSING:api_event_integration", r["holds"])

    def test_deadline_passed_holds_without_trusting_packet_clock(self):
        p = self.packet()
        p["concept_paper_deadline"] = "2026-09-13T00:00:00Z"
        p["trusted_now"] = "2020-01-01T00:00:00Z"  # ignored by design
        r = self.evaluate(p)
        self.assertEqual(r["state"], "HOLD")
        self.assertEqual(r["holds"], ["DEADLINE_PASSED"])

    def test_hash_mismatch_fails_closed(self):
        p = self.packet()
        p["sources"][0]["sha256"] = "0" * 64
        with self.assertRaises(engine.PacketError):
            self.evaluate(p)

    def test_symlink_fails_closed_when_nofollow_available(self):
        if not hasattr(os, "O_NOFOLLOW"):
            self.skipTest("O_NOFOLLOW unavailable")
        link = self.root / "link.txt"
        link.symlink_to(self.files["call"])
        p = self.packet()
        p["sources"][0]["path"] = str(link)
        with self.assertRaises(OSError):
            self.evaluate(p)

    def test_expired_evidence_holds_not_teaming_green(self):
        p = self.packet()
        row = self.evidence("f", "facility_clearance_top_secret", "fcl")
        row["expires_at"] = "2026-09-14T04:59:59Z"
        p["eligibility_evidence"] = [row]
        r = self.evaluate(p)
        self.assertEqual(r["state"], "HOLD")
        self.assertIn("EVIDENCE_EXPIRED:f", r["holds"])

    def test_current_addendum_generation_must_be_bound(self):
        p = self.packet()
        p["current_addendum_generation"] = "2"
        r = self.evaluate(p)
        self.assertEqual(r["state"], "HOLD")
        self.assertIn("CURRENT_ADDENDUM_NOT_BOUND:2", r["holds"])

    def test_receipt_is_deterministic_under_fixed_clock(self):
        p = self.packet()
        a = self.evaluate(p)
        b = self.evaluate(json.loads(json.dumps(p)))
        self.assertEqual(a["receipt_sha256"], b["receipt_sha256"])
        self.assertEqual(a, b)

    def test_incumbent_overlap_risk_penalizes_commercial_fit(self):
        p = self.packet()
        p["teaming_targets"] = [
            {"name": "Specialist", "signals": ["current_dcsa_nb_is_work", "identity_application_modernization", "small_business", "public_partner_route"]},
            {"name": "Incumbent", "signals": ["current_dcsa_nb_is_work", "govcloud_devsecops", "identity_application_modernization", "public_partner_route", "incumbent_overlap_risk"]},
        ]
        r = self.evaluate(p)
        self.assertEqual(r["teaming_targets"][0]["name"], "Specialist")

    def test_teaming_rank_does_not_treat_clearance_as_signal(self):
        p = self.packet()
        p["teaming_targets"] = [
            {"name": "A", "signals": ["claimed_facility_clearance", "public_partner_route"]},
            {"name": "B", "signals": ["current_dcsa_nb_is_work", "public_partner_route"]},
        ]
        r = self.evaluate(p)
        self.assertEqual(r["teaming_targets"][0]["name"], "B")
        self.assertEqual(r["teaming_targets"][1]["facility_clearance"], "OWNER_VERIFY")

    def test_concept_scaffold_preserves_no_authority_claim(self):
        p = self.packet()
        r = self.evaluate(p)
        md = engine.compile_concept_markdown(p, r)
        self.assertIn("does not assert facility clearance", md)
        self.assertIn("TEAMING_REQUIRED", md)
        self.assertIn("cleared-prime teaming path", md)


if __name__ == "__main__":
    unittest.main()
