from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("smart_outreach_tested", ROOT / "host" / "smart_outreach.py")
assert SPEC and SPEC.loader
smart = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smart)


def prospect(pid="one", email="Owner@Example.Test"):
    return {
        "prospect_id": pid,
        "organization": "Qualified Example",
        "recipient_email": email,
        "evidence": {
            "source_url": "https://example.test/production",
            "observed_at": "2026-09-13T00:00:00Z",
            "exact_quote": "A production timeout needs idempotent recovery, replay, and an exact audit trace.",
        },
        "owner_role": "agent platform owner",
        "route": {"kind": "EMAIL", "value": email, "state": "VERIFIED"},
        "proof_hypothesis": "Can one timeout recover idempotently and leave an exact replay receipt?",
        "occupied_by": None,
        "do_not_contact": False,
        "disqualifiers": [],
    }


def data(*rows):
    return {
        "schema_version": smart.SCHEMA_VERSION,
        "kind": "SMART_OUTREACH_CANDIDATES",
        "generated_at": "2026-09-13T23:35:00-04:00",
        "offer": {
            "sku_id": "proof-2500-v1",
            "name": "Proof",
            "price_usd": 2500,
            "proof_url": "https://example.test/proof",
            "intake_url": "https://example.test/intake",
        },
        "prospects": list(rows),
    }


class LeaseIntegrationTests(unittest.TestCase):
    def test_ready_draft_is_bound_to_canonical_remote_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = smart.build_plan(data(prospect()), Path(directory))
        item = plan["items"][0]
        self.assertEqual(item["decision"], "READY_TO_DRAFT")
        lease = item["outbound_lease"]
        self.assertTrue(lease["claim_required"])
        self.assertEqual(lease["remote_authority"], "git-main")
        self.assertTrue(lease["path"].startswith("coordination/outbound/leases/"))
        self.assertTrue(lease["path"].endswith(".json"))
        self.assertEqual(len(lease["key"]), 64)
        self.assertNotIn("Owner@Example.Test", str(lease))
        self.assertIn(lease["path"], item["next_action"])
        self.assertEqual(plan["truth"]["lease_claims_required"], 1)
        self.assertEqual(plan["truth"]["contacts_claimed"], 0)
        self.assertEqual(plan["truth"]["transport_actions"], 0)

    def test_case_variation_has_same_lease_identity(self):
        a = smart.outbound_lease_identity(prospect(email="Owner@Example.Test"), data(prospect())["offer"])
        b = smart.outbound_lease_identity(prospect(email=" owner@example.test "), data(prospect())["offer"])
        self.assertEqual(a["key"], b["key"])
        self.assertEqual(a["path"], b["path"])

    def test_two_rows_same_offer_and_recipient_fail_before_drafting(self):
        a = prospect("aaa", "same@example.test")
        b = prospect("bbb", "SAME@example.test")
        with self.assertRaisesRegex(smart.OutreachError, "duplicate outbound lead identity"):
            smart.validate_input(data(a, b))

    def test_dnr_still_dominates_and_creates_no_draft(self):
        row = prospect()
        row["do_not_contact"] = True
        with tempfile.TemporaryDirectory() as directory:
            plan = smart.build_plan(data(row), Path(directory))
        item = plan["items"][0]
        self.assertEqual(item["decision"], "HOLD_DO_NOT_CONTACT")
        self.assertIsNone(item["draft"])
        self.assertEqual(plan["truth"]["lease_claims_required"], 0)

    def test_receipt_collision_still_dominates(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "sent.json").write_text(
                '{"organization":"Else","recipient_email":"owner@example.test","dedupe":{"do_not_resend":true}}',
                encoding="utf-8",
            )
            plan = smart.build_plan(data(prospect(email="owner@example.test")), Path(directory))
        self.assertEqual(plan["items"][0]["decision"], "HOLD_DO_NOT_RESEND")
        self.assertIsNone(plan["items"][0]["draft"])

    def test_missing_recipient_cannot_be_ready_to_draft(self):
        row = prospect()
        row["recipient_email"] = None
        with tempfile.TemporaryDirectory() as directory:
            plan = smart.build_plan(data(row), Path(directory))
        self.assertEqual(plan["items"][0]["decision"], "RESEARCH_REQUIRED")
        self.assertIsNone(plan["items"][0]["draft"])
        self.assertIsNone(plan["items"][0]["outbound_lease"])


if __name__ == "__main__":
    unittest.main()
