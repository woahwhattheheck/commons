from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOST_HANDOFF = ROOT / "host" / "lm_gtm_relationship_handoff.py"
SPEC = importlib.util.spec_from_file_location("lm_gtm_relationship_handoff", HOST_HANDOFF)
assert SPEC and SPEC.loader
handoff_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handoff_mod)

idx = handoff_mod.idx
EMAIL_RE = idx.EMAIL_AT_RE
PHONE_RE = idx.PHONE_RE
BILLINGS = "city-of-billings-bid-1421"
BILLINGS_OWNER_HOLD = "lm-gtm-billings-owner-hold-status-20260831-02"
BILLINGS_POINTER = "lm-gtm-billings-material-reply-20260831-01"


class RelationshipHandoffTests(unittest.TestCase):
    def test_billings_handoff_is_evidence_bound(self) -> None:
        packet = handoff_mod.relationship_handoff(BILLINGS)
        self.assertEqual(packet["kind"], "LM_GTM_RELATIONSHIP_HANDOFF")
        self.assertEqual(packet["subject_id"], BILLINGS)
        self.assertEqual(packet["decision"], "OWNER_HOLD")
        self.assertEqual(packet["route_ref"], "airtable:rec2mCS4ETa8FOvqN")
        self.assertEqual(
            packet["canonical_crm"],
            "JOJO Revenue Recovery CRM / Revenue Pipeline",
        )
        self.assertEqual(packet["cash_usd"], 0)
        self.assertEqual(packet["transport"], "NONE")
        self.assertTrue(packet["invent_guard"]["no_second_crm"])
        self.assertTrue(packet["invent_guard"]["no_customer_contact"])

        fields = packet["fields"]
        successor = fields["successor_next_action"]
        self.assertEqual(successor["status"], "SOURCED")
        nxt = successor["value"].casefold()
        self.assertIn("owner_hold", nxt)
        self.assertIn("do not contact cheri", nxt)
        self.assertIn("no bid submission by agents", nxt)
        self.assertNotIn("submit the bid now", nxt)

        due = fields["next_time_sensitive"]
        self.assertEqual(due["status"], "SOURCED")
        self.assertEqual(due["value"], "2026-09-04")

        chain_ids = [item["id"] for item in packet["evidence_chain"]]
        self.assertIn(BILLINGS_OWNER_HOLD, chain_ids)
        self.assertIn(BILLINGS_POINTER, chain_ids)

        promised = fields["promised"]
        if promised["status"] == "SOURCED":
            text = promised["value"].casefold()
            self.assertNotIn("bid submitted", text)
            self.assertNotIn("proposal delivered to city", text)

        blob = json.dumps(packet, sort_keys=True, ensure_ascii=False)
        self.assertIsNone(EMAIL_RE.search(blob))
        self.assertIsNone(PHONE_RE.search(blob))
        for token in ("armstrongc@", "cheri@", "@billingsmt.gov", "6803283352"):
            self.assertNotIn(token, blob)

    def test_successor_reads_next_action_from_packet_only(self) -> None:
        packet = handoff_mod.relationship_handoff(BILLINGS)
        value = handoff_mod.successor_reads_next_action(packet)
        self.assertIsNotNone(value)
        assert value is not None
        self.assertEqual(value, packet["fields"]["successor_next_action"]["value"])
        self.assertIn("OWNER_HOLD", value)
        # Prove no re-read of ledgers is required: strip to packet fields only
        slim = {
            "fields": {
                "successor_next_action": packet["fields"]["successor_next_action"]
            }
        }
        self.assertEqual(handoff_mod.successor_reads_next_action(slim), value)

    def test_unknown_subject_fails_closed(self) -> None:
        with self.assertRaises(idx.IndexError_):
            handoff_mod.relationship_handoff("brand-new-buyer-mint-refuse")

    def test_composio_hot_handoff_surfaces_ready_to_draft(self) -> None:
        packet = handoff_mod.relationship_handoff("composio")
        self.assertEqual(packet["decision"], "READY_TO_DRAFT")
        self.assertEqual(packet["lane"], "ready_to_draft")
        self.assertEqual(packet["fields"]["successor_next_action"]["status"], "SOURCED")

    def test_cli_billings_and_send_exit(self) -> None:
        ok = subprocess.run(
            [sys.executable, str(HOST_HANDOFF), BILLINGS],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        packet = json.loads(ok.stdout)
        self.assertEqual(packet["subject_id"], BILLINGS)
        self.assertEqual(packet["decision"], "OWNER_HOLD")
        self.assertIsNone(EMAIL_RE.search(ok.stdout))
        self.assertIsNone(PHONE_RE.search(ok.stdout))

        refused = subprocess.run(
            [sys.executable, str(HOST_HANDOFF), BILLINGS, "--send"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(refused.returncode, 3)
        self.assertIn("never transports mail", refused.stderr.casefold())

    def test_no_second_crm_roots(self) -> None:
        for name in ("crm", "people", "contacts", "sales"):
            self.assertFalse((ROOT / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
