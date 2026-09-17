import copy
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import firewall as fw


SOURCE_BYTES = b'{"authority":"retained","opportunity":"DEMO-1","revision":"A"}\n'


def base_packet():
    return {
        "schema": fw.SCHEMA,
        "source": {
            "locator": "fixtures/source_authority.json",
            "sha256": hashlib.sha256(SOURCE_BYTES).hexdigest(),
        },
        "as_of_utc": "2026-09-17T19:00:00Z",
        "opportunity": {
            "id": "DEMO-1",
            "deadline_utc": "2026-09-20T19:00:00Z",
            "min_runway_hours": 48,
        },
        "submission": {
            "kind": "PORTAL",
            "locator": "https://buyer.example/submit",
            "route_state": "PROVEN",
            "registration_required": False,
            "registration_state": "NOT_REQUIRED",
        },
        "eligibility": {
            "gates": [
                {
                    "name": "prime eligibility",
                    "state": "PROVEN",
                    "evidence_refs": ["source#prime"],
                },
                {
                    "name": "partner onboarding",
                    "state": "NOT_REQUIRED",
                    "evidence_refs": [],
                },
            ]
        },
        "economics": {
            "basis": "FIXED_FEE",
            "amount": "5000.00",
            "currency": "USD",
            "bounded_scope": "one retained-export acceptance pilot",
            "payment_path_state": "PROVEN",
        },
        "target": {
            "organization": "Example Buyer",
            "contact": "opps@example.com",
            "relationship_state": "OPEN",
        },
        "action": {
            "kind": "EMAIL",
            "route": "OPPS@EXAMPLE.COM",
            "purpose": "bounded paid workshare inquiry",
            "content_sha256": "0" * 64,
        },
        "prior_actions": [],
    }


def evaluate(packet, *, writer="Z-Palisade-1445"):
    return fw.evaluate(
        packet,
        SOURCE_BYTES,
        now_utc="2026-09-17T19:00:00Z",
        writer=writer,
    )


def add_approval_and_lease(packet, first, *, writer="Z-Palisade-1445"):
    packet["owner_review"] = {
        "status": "APPROVED",
        "reviewer": "Bryce",
        "qualification_digest": first.qualification_digest,
        "reviewed_at_utc": "2026-09-17T19:00:00Z",
        "expires_at_utc": "2026-09-17T20:00:00Z",
    }
    packet["writer_lease"] = {
        "status": "SELECTED",
        "key": "DEMO-1-EMAIL-ZPAL1445",
        "selected_writer": writer,
        "action_digest": first.action_digest,
        "issued_at_utc": "2026-09-17T19:00:00Z",
        "expires_at_utc": "2026-09-17T20:00:00Z",
    }


class FirewallTests(unittest.TestCase):
    def test_fully_evidenced_packet_reaches_owner_review_but_cannot_send(self):
        decision = evaluate(base_packet())
        self.assertTrue(decision.qualified_for_owner_review)
        self.assertFalse(decision.authorized_to_send)
        self.assertEqual(decision.blockers, ())
        self.assertIn("OWNER_REVIEW_REQUIRED", decision.warnings)
        self.assertIn("WRITER_LEASE_REQUIRED", decision.warnings)

    def test_exact_owner_review_and_writer_lease_authorize_one_action(self):
        packet = base_packet()
        first = evaluate(packet)
        add_approval_and_lease(packet, first)
        decision = evaluate(packet)
        self.assertTrue(decision.qualified_for_owner_review)
        self.assertTrue(decision.authorized_to_send)
        self.assertEqual(decision.blockers, ())

    def test_action_mutation_invalidates_bound_lease_and_review(self):
        packet = base_packet()
        first = evaluate(packet)
        add_approval_and_lease(packet, first)
        packet["action"]["content_sha256"] = "1" * 64
        decision = evaluate(packet)
        self.assertFalse(decision.authorized_to_send)
        self.assertIn("OWNER_REVIEW_STALE_OR_FOREIGN", decision.blockers)
        self.assertIn("WRITER_LEASE_STALE_OR_FOREIGN_ACTION", decision.blockers)

    def test_mutable_clock_replay_is_rejected(self):
        packet = base_packet()
        with self.assertRaisesRegex(fw.PacketError, "mutable-clock replay"):
            fw.evaluate(
                packet,
                SOURCE_BYTES,
                now_utc="2026-09-17T18:59:59Z",
                writer="Z-Palisade-1445",
            )

    def test_short_runway_is_held(self):
        packet = base_packet()
        packet["opportunity"]["deadline_utc"] = "2026-09-18T18:59:59Z"
        decision = evaluate(packet)
        self.assertFalse(decision.qualified_for_owner_review)
        self.assertIn("RUNWAY_BELOW_MINIMUM", decision.blockers)

    def test_exact_runway_boundary_is_qualified_and_warned(self):
        packet = base_packet()
        packet["opportunity"]["deadline_utc"] = "2026-09-19T19:00:00Z"
        decision = evaluate(packet)
        self.assertTrue(decision.qualified_for_owner_review)
        self.assertIn("RUNWAY_EXACTLY_AT_MINIMUM", decision.warnings)

    def test_deadline_passed_has_explicit_blocker(self):
        packet = base_packet()
        packet["opportunity"]["deadline_utc"] = "2026-09-17T18:59:59Z"
        packet["opportunity"]["min_runway_hours"] = 0
        decision = evaluate(packet)
        self.assertIn("DEADLINE_PASSED", decision.blockers)

    def test_unknown_eligibility_never_becomes_qualified(self):
        packet = base_packet()
        packet["eligibility"]["gates"][0]["state"] = "UNKNOWN"
        packet["eligibility"]["gates"][0]["evidence_refs"] = []
        decision = evaluate(packet)
        self.assertFalse(decision.qualified_for_owner_review)
        self.assertIn("ELIGIBILITY_UNKNOWN:prime eligibility", decision.blockers)

    def test_proven_eligibility_requires_evidence_reference(self):
        packet = base_packet()
        packet["eligibility"]["gates"][0]["evidence_refs"] = []
        with self.assertRaisesRegex(fw.PacketError, "needs evidence_refs"):
            evaluate(packet)

    def test_unknown_route_and_required_registration_block(self):
        packet = base_packet()
        packet["submission"]["route_state"] = "UNKNOWN"
        packet["submission"]["registration_required"] = True
        packet["submission"]["registration_state"] = "UNKNOWN"
        decision = evaluate(packet)
        self.assertIn("SUBMISSION_ROUTE_NOT_PROVEN", decision.blockers)
        self.assertIn("REGISTRATION_NOT_PROVEN", decision.blockers)

    def test_dnr_and_bounce_relationships_block(self):
        for state in ("DNR", "BOUNCE", "BLOCKED", "CLOSED"):
            packet = base_packet()
            packet["target"]["relationship_state"] = state
            with self.subTest(state=state):
                self.assertIn(f"RELATIONSHIP_{state}", evaluate(packet).blockers)

    def test_non_positive_or_non_finite_economics_fail_structurally(self):
        for amount in ("0", "-1", "NaN", "Infinity"):
            packet = base_packet()
            packet["economics"]["amount"] = amount
            with self.subTest(amount=amount):
                with self.assertRaisesRegex(fw.PacketError, "finite and > 0|positive decimal"):
                    evaluate(packet)

    def test_unproven_payment_path_blocks(self):
        packet = base_packet()
        packet["economics"]["payment_path_state"] = "UNKNOWN"
        self.assertIn("PAYMENT_PATH_NOT_PROVEN", evaluate(packet).blockers)

    def test_retained_source_byte_tamper_fails_before_decision(self):
        packet = base_packet()
        with self.assertRaisesRegex(fw.PacketError, "retained source digest mismatch"):
            fw.evaluate(
                packet,
                SOURCE_BYTES + b"tamper",
                now_utc=packet["as_of_utc"],
                writer="Z-Palisade-1445",
            )

    def test_email_alias_case_and_mailto_normalize_to_same_dedupe_key(self):
        a = base_packet()
        b = base_packet()
        a["action"]["route"] = " OPPS@EXAMPLE.COM "
        b["action"]["route"] = "mailto:opps@example.com"
        self.assertEqual(evaluate(a).dedupe_key, evaluate(b).dedupe_key)

    def test_duplicate_material_action_blocks_even_with_case_alias(self):
        packet = base_packet()
        key = evaluate(packet).dedupe_key
        packet["action"]["route"] = "mailto:opps@example.com"
        packet["prior_actions"] = [{"dedupe_key": key, "state": "SENT"}]
        decision = evaluate(packet)
        self.assertIn("DUPLICATE_PRIOR_ACTION:SENT", decision.blockers)

    def test_failed_or_void_prior_action_does_not_permanently_block(self):
        for state in ("FAILED", "VOID"):
            packet = base_packet()
            key = evaluate(packet).dedupe_key
            packet["prior_actions"] = [{"dedupe_key": key, "state": state}]
            with self.subTest(state=state):
                self.assertTrue(evaluate(packet).qualified_for_owner_review)

    def test_foreign_writer_lease_is_rejected(self):
        packet = base_packet()
        first = evaluate(packet)
        add_approval_and_lease(packet, first, writer="Z-Other")
        decision = evaluate(packet, writer="Z-Palisade-1445")
        self.assertIn("WRITER_LEASE_FOREIGN_WRITER", decision.blockers)
        self.assertFalse(decision.authorized_to_send)

    def test_expired_lease_is_rejected(self):
        packet = base_packet()
        first = evaluate(packet)
        add_approval_and_lease(packet, first)
        packet["writer_lease"]["expires_at_utc"] = "2026-09-17T18:59:59Z"
        decision = evaluate(packet)
        self.assertIn("WRITER_LEASE_TIME_INVALID", decision.blockers)

    def test_rejected_owner_review_cannot_send(self):
        packet = base_packet()
        first = evaluate(packet)
        add_approval_and_lease(packet, first)
        packet["owner_review"]["status"] = "REJECTED"
        decision = evaluate(packet)
        self.assertIn("OWNER_REVIEW_REJECTED", decision.blockers)
        self.assertFalse(decision.authorized_to_send)

    def test_owner_approval_cannot_override_qualification_blocker(self):
        packet = base_packet()
        first = evaluate(packet)
        add_approval_and_lease(packet, first)
        packet["target"]["relationship_state"] = "DNR"
        decision = evaluate(packet)
        self.assertIn("RELATIONSHIP_DNR", decision.blockers)
        self.assertIn("OWNER_REVIEW_STALE_OR_FOREIGN", decision.blockers)
        self.assertFalse(decision.qualified_for_owner_review)

    def test_bad_email_transport_is_rejected_structurally(self):
        packet = base_packet()
        packet["action"]["route"] = "not-an-email"
        with self.assertRaisesRegex(fw.PacketError, "valid email"):
            evaluate(packet)

    def test_contact_and_transport_must_match_for_email(self):
        packet = base_packet()
        packet["target"]["contact"] = "other@example.com"
        decision = evaluate(packet)
        self.assertIn("ACTION_ROUTE_CONTACT_MISMATCH", decision.blockers)

    def test_cli_is_nonzero_when_only_owner_review_qualified(self):
        packet = base_packet()
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            packet_path = root / "packet.json"
            source_path = root / "source.json"
            packet_path.write_text(json.dumps(packet), encoding="utf-8")
            source_path.write_bytes(SOURCE_BYTES)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(HERE / "firewall.py"),
                    str(packet_path),
                    "--source", str(source_path),
                    "--now", packet["as_of_utc"],
                    "--writer", "Z-Palisade-1445",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(proc.returncode, 2)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["qualified_for_owner_review"])
        self.assertFalse(payload["authorized_to_send"])


if __name__ == "__main__":
    unittest.main()
