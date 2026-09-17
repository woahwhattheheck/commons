from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.relationship_contact_guard.guard import (
    AUTHORITY,
    GuardError,
    compile_guard,
    load_json,
    verify_guard,
)


NOW = "2026-09-17T19:00:00Z"


def candidate(**overrides):
    row = {
        "counterparty_id": "example.com",
        "opportunity_id": "example-rfp-1",
        "route": "sales@example.com",
        "purpose": "paid-qa-workshare",
        "now": NOW,
    }
    row.update(overrides)
    return row


def sent(event_id="s1", at="2026-09-17T18:00:00Z", route="ops@example.com", purpose="other-purpose", opportunity="example-rfp-1", message="m1"):
    return {
        "event_id": event_id,
        "kind": "PROVIDER_SENT",
        "occurred_at": at,
        "counterparty_id": "example.com",
        "opportunity_id": opportunity,
        "route": route,
        "purpose": purpose,
        "provider_message_id": message,
    }


def bounce(event_id="b1", at="2026-09-17T18:05:00Z", route="ops@example.com", purpose="other-purpose", opportunity="example-rfp-1", message="m1"):
    return {
        "event_id": event_id,
        "kind": "PROVIDER_BOUNCE",
        "occurred_at": at,
        "counterparty_id": "example.com",
        "opportunity_id": opportunity,
        "route": route,
        "purpose": purpose,
        "in_reply_to_message_id": message,
    }


def reply(event_id="r1", at="2026-09-17T18:05:00Z", route="ops@example.com", purpose="other-purpose", opportunity="example-rfp-1", message="m1"):
    return {
        "event_id": event_id,
        "kind": "HUMAN_REPLY",
        "occurred_at": at,
        "counterparty_id": "example.com",
        "opportunity_id": opportunity,
        "route": route,
        "purpose": purpose,
        "in_reply_to_message_id": message,
    }


def negative(scope, event_id="n1", at="2026-09-17T18:05:00Z", route="sales@example.com", purpose="paid-qa-workshare", opportunity="example-rfp-1", message="m1"):
    return {
        "event_id": event_id,
        "kind": "HUMAN_NEGATIVE",
        "occurred_at": at,
        "counterparty_id": "example.com",
        "opportunity_id": opportunity,
        "route": route,
        "purpose": purpose,
        "scope": scope,
        "in_reply_to_message_id": message,
    }


def reopen(event_id="o1", at="2026-09-17T18:10:00Z"):
    return {
        "event_id": event_id,
        "kind": "HUMAN_REOPEN",
        "occurred_at": at,
        "counterparty_id": "example.com",
        "opportunity_id": "example-rfp-1",
        "route": "sales@example.com",
        "purpose": "paid-qa-workshare",
    }


class RelationshipGuardTests(unittest.TestCase):
    def compile(self, events=(), **candidate_overrides):
        return compile_guard({"candidate": candidate(**candidate_overrides), "events": list(events)})

    def test_01_empty_packet_is_diagnostic_only(self):
        out = self.compile()
        self.assertEqual(out["decision"]["status"], "NO_CONFLICT_FOUND")
        self.assertEqual(out["decision"]["authority"], AUTHORITY)
        self.assertFalse(out["decision"]["truth"]["no_conflict_is_send_permission"])
        self.assertFalse(any(out["decision"]["authority"].values()))

    def test_02_same_counterparty_different_route_holds(self):
        out = self.compile([sent()])
        self.assertEqual(out["decision"]["status"], "HOLD_RECENT_COUNTERPARTY_CONTACT")
        self.assertEqual(out["decision"]["blocker_event_ids"], ["s1"])

    def test_03_same_opportunity_purpose_cross_key_holds_after_six_hours(self):
        row = sent(at="2026-09-17T10:00:00Z", route="other@example.com", purpose="paid-qa-workshare")
        out = self.compile([row])
        self.assertEqual(out["decision"]["status"], "HOLD_RECENT_PURSUIT_CONTACT")

    def test_04_exact_unanswered_send_is_dnr(self):
        row = sent(route="sales@example.com", purpose="paid-qa-workshare")
        out = self.compile([row])
        self.assertEqual(out["decision"]["status"], "HOLD_EXACT_DNR")

    def test_05_bounce_is_route_scoped_not_org_rejection(self):
        out = self.compile([sent(), bounce()])
        self.assertEqual(out["decision"]["status"], "NO_CONFLICT_FOUND")
        self.assertFalse(out["decision"]["authority"]["send_authorized"])

    def test_06_bounced_candidate_route_is_dead_route(self):
        s = sent(route="sales@example.com", purpose="paid-qa-workshare")
        b = bounce(route="sales@example.com", purpose="paid-qa-workshare")
        out = self.compile([s, b])
        self.assertEqual(out["decision"]["status"], "HOLD_DEAD_ROUTE")

    def test_07_counterparty_negative_blocks_other_route(self):
        s = sent(route="old@example.com")
        n = negative("COUNTERPARTY", route="old@example.com", purpose="other-purpose")
        out = self.compile([s, n])
        self.assertEqual(out["decision"]["status"], "HOLD_COUNTERPARTY_OPT_OUT")

    def test_08_route_negative_does_not_poison_other_route(self):
        s = sent(route="old@example.com", at="2026-09-10T18:00:00Z")
        n = negative("ROUTE_PURPOSE", route="old@example.com", purpose="other-purpose", at="2026-09-10T18:05:00Z")
        out = self.compile([s, n])
        self.assertEqual(out["decision"]["status"], "NO_CONFLICT_FOUND")

    def test_09_reopen_clears_scoped_negative_but_not_send_authority(self):
        s = sent(route="sales@example.com", purpose="paid-qa-workshare", at="2026-09-10T18:00:00Z")
        n = negative("COUNTERPARTY", route="sales@example.com", purpose="paid-qa-workshare", at="2026-09-10T18:05:00Z")
        o = reopen(at="2026-09-17T17:00:00Z")
        out = self.compile([s, n, o])
        self.assertEqual(out["decision"]["status"], "NO_CONFLICT_FOUND")
        self.assertFalse(out["decision"]["authority"]["send_authorized"])

    def test_10_human_reply_moves_to_inbound_review(self):
        s = sent(at="2026-09-10T18:00:00Z")
        r = reply(at="2026-09-10T18:05:00Z")
        out = self.compile([s, r])
        self.assertEqual(out["decision"]["status"], "HOLD_INBOUND_REVIEW")

    def test_11_future_event_rejected(self):
        with self.assertRaises(GuardError):
            self.compile([sent(at="2026-09-18T00:00:00Z")])

    def test_12_reordered_events_rejected(self):
        with self.assertRaises(GuardError):
            self.compile([sent(at="2026-09-17T18:10:00Z"), bounce(at="2026-09-17T18:05:00Z")])

    def test_13_duplicate_event_id_rejected(self):
        a = sent(event_id="dup", message="m1")
        b = sent(event_id="dup", message="m2", at="2026-09-17T18:01:00Z")
        with self.assertRaises(GuardError):
            self.compile([a, b])

    def test_14_duplicate_provider_message_id_rejected(self):
        a = sent(event_id="s1", message="same")
        b = sent(event_id="s2", message="same", at="2026-09-17T18:01:00Z")
        with self.assertRaises(GuardError):
            self.compile([a, b])

    def test_15_orphan_response_rejected(self):
        with self.assertRaises(GuardError):
            self.compile([reply(message="missing")])

    def test_16_cross_counterparty_transplant_rejected(self):
        row = sent()
        row["counterparty_id"] = "attacker.example"
        with self.assertRaises(GuardError):
            self.compile([row])

    def test_17_noncanonical_unicode_identifier_rejected(self):
        with self.assertRaises(GuardError):
            self.compile([], route="sáles@example.com")

    def test_18_cooldown_floors_cannot_be_weakened(self):
        with self.assertRaises(GuardError):
            self.compile([], relationship_cooldown_seconds=1)
        with self.assertRaises(GuardError):
            self.compile([], pursuit_cooldown_seconds=1)

    def test_19_receipt_and_exact_recompile_reject_mutation(self):
        packet = {"candidate": candidate(), "events": [sent()]}
        artifact = compile_guard(packet)
        self.assertTrue(verify_guard(packet, artifact))
        changed = copy.deepcopy(artifact)
        changed["decision"]["authority"]["send_authorized"] = True
        with self.assertRaises(GuardError):
            verify_guard(packet, changed)
        transplant = {"candidate": candidate(opportunity_id="other-rfp"), "events": []}
        with self.assertRaises(GuardError):
            verify_guard(transplant, artifact)

    def test_20_strict_json_duplicate_key_rejected(self):
        text = '{"candidate":{"counterparty_id":"example.com","counterparty_id":"evil.com","opportunity_id":"x","route":"a@example.com","purpose":"p","now":"2026-09-17T19:00:00Z"},"events":[]}'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "packet.json"
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(GuardError):
                load_json(path)

    def test_21_authority_ceiling_exact_false(self):
        out = self.compile()
        self.assertEqual(set(out["decision"]["authority"]), set(AUTHORITY))
        self.assertFalse(any(out["decision"]["authority"].values()))
        self.assertFalse(out["decision"]["truth"]["retained_packet_complete"])
        self.assertFalse(out["decision"]["truth"]["provider_authentication_established_here"])


if __name__ == "__main__":
    unittest.main()
