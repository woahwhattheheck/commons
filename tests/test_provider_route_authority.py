from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest
from revenue.provider_route_authority.core import AuthorityError, INPUT_SCHEMA, compile_authority, strict_json_loads, verify_authority


def event(event_id, kind, source, at, route="sales@example.com", route_type="EMAIL",
          org="example.com", purpose="paid-workshare"):
    return {"event_id": event_id, "kind": kind, "source": source, "at": at,
            "org": org, "purpose": purpose, "route_type": route_type, "route": route,
            "evidence_ref": f"evidence:{event_id}"}


def packet(events):
    return {"schema": INPUT_SCHEMA, "subject": {"org": "example.com", "route_type": "EMAIL",
            "route": "sales@example.com", "purpose": "paid-workshare"}, "events": events}


class ProviderRouteAuthorityTests(unittest.TestCase):
    def allow_events(self):
        return [event("take", "SLACK_TAKE", "SLACK", "2026-09-17T02:00:00-04:00"),
                event("route", "ROUTE_VERIFIED", "PUBLIC_EVIDENCE", "2026-09-17T02:01:00-04:00"),
                event("muse", "MUSE_CLEAR", "MUSE", "2026-09-17T02:02:00-04:00")]

    def test_correctly_labeled_caller_asserted_gates_are_candidate_only(self):
        out = compile_authority(packet(self.allow_events()))
        self.assertEqual(out["decision"], "CANDIDATE_ONE_SEND")
        self.assertEqual(out["evidence_trust"], "CALLER_ASSERTED_UNAUTHENTICATED")
        self.assertFalse(out["authority"]["external_send_authorized"])
        self.assertFalse(out["authority"]["muse_request_authorized"])
        self.assertIn("LIVE_SLACK_MUSE_PROVIDER_RECENSUS_REQUIRED", out["reasons"])

    def test_provider_sent_hard_dnr_even_after_new_muse(self):
        events = self.allow_events() + [event("sent", "PROVIDER_SENT", "PROVIDER", "2026-09-17T02:03:00-04:00"),
                                        event("muse2", "MUSE_CLEAR", "MUSE", "2026-09-17T02:04:00-04:00")]
        self.assertEqual(compile_authority(packet(events))["decision"], "HARD_DNR")

    def test_hard_bounce_makes_route_dead_even_for_other_purpose(self):
        events = self.allow_events() + [event("dsn", "HARD_BOUNCE", "PROVIDER", "2026-09-17T02:03:05-04:00",
                                            purpose="older-campaign")]
        out = compile_authority(packet(events))
        self.assertEqual(out["decision"], "DEAD_ROUTE")
        self.assertIn("BOUNCE_IS_NOT_PERMISSION_TO_ROUTE_AROUND", out["reasons"])

    def test_human_reply_is_org_level_inbound_only(self):
        events = self.allow_events() + [event("reply", "HUMAN_REPLY", "MAILBOX", "2026-09-17T02:03:00-04:00",
                                            route="ceo@example.com", purpose="different-opportunity")]
        self.assertEqual(compile_authority(packet(events))["decision"], "INBOUND_ONLY")

    def test_human_rejection_is_inbound_only(self):
        events = self.allow_events() + [event("reject", "HUMAN_REJECTION", "MAILBOX", "2026-09-17T02:03:00-04:00")]
        self.assertEqual(compile_authority(packet(events))["decision"], "INBOUND_ONLY")

    def test_two_distinct_hard_failed_routes_hold_org(self):
        events = self.allow_events() + [event("d1", "HARD_BOUNCE", "PROVIDER", "2026-09-17T01:00:00-04:00", "first@example.com"),
                                        event("d2", "HARD_BOUNCE", "PROVIDER", "2026-09-17T01:05:00-04:00", "second@example.com")]
        out = compile_authority(packet(events))
        self.assertEqual(out["decision"], "HOLD_UNKNOWN")
        self.assertIn("ROUTE_SPRAY_GUARD", out["reasons"])

    def test_one_other_route_hard_bounce_does_not_block_clean_exact_route(self):
        events = self.allow_events() + [event("d1", "HARD_BOUNCE", "PROVIDER", "2026-09-17T01:00:00-04:00", "old@example.com")]
        self.assertEqual(compile_authority(packet(events))["decision"], "CANDIDATE_ONE_SEND")

    def test_soft_bounce_holds_retry(self):
        events = self.allow_events() + [event("sent", "PROVIDER_SENT", "PROVIDER", "2026-09-17T02:03:00-04:00"),
                                        event("soft", "SOFT_BOUNCE", "PROVIDER", "2026-09-17T02:04:00-04:00")]
        self.assertEqual(compile_authority(packet(events))["decision"], "HOLD_UNKNOWN")

    def test_timeout_holds(self):
        events = self.allow_events() + [event("timeout", "PROVIDER_TIMEOUT", "PROVIDER", "2026-09-17T02:04:00-04:00")]
        self.assertEqual(compile_authority(packet(events))["decision"], "HOLD_UNKNOWN")

    def test_stale_muse_before_take_is_not_authority(self):
        events = [event("muse", "MUSE_CLEAR", "MUSE", "2026-09-17T01:59:00-04:00"),
                  event("take", "SLACK_TAKE", "SLACK", "2026-09-17T02:00:00-04:00"),
                  event("route", "ROUTE_VERIFIED", "PUBLIC_EVIDENCE", "2026-09-17T02:01:00-04:00")]
        out = compile_authority(packet(events))
        self.assertEqual(out["decision"], "HOLD_UNKNOWN")
        self.assertIn("NO_POST_TAKE_MUSE_CLEAR", out["reasons"])

    def test_stale_route_verification_before_take_is_not_authority(self):
        events = [event("route", "ROUTE_VERIFIED", "PUBLIC_EVIDENCE", "2026-09-17T01:59:00-04:00"),
                  event("take", "SLACK_TAKE", "SLACK", "2026-09-17T02:00:00-04:00"),
                  event("muse", "MUSE_CLEAR", "MUSE", "2026-09-17T02:01:00-04:00")]
        out = compile_authority(packet(events))
        self.assertEqual(out["decision"], "HOLD_UNKNOWN")
        self.assertIn("NO_POST_TAKE_ROUTE_VERIFICATION", out["reasons"])

    def test_same_route_other_purpose_send_blocks_duplicate_route(self):
        events = self.allow_events() + [event("sent", "PROVIDER_SENT", "PROVIDER", "2026-09-17T01:30:00-04:00",
                                            purpose="other-opportunity")]
        out = compile_authority(packet(events))
        self.assertEqual(out["decision"], "HOLD_UNKNOWN")
        self.assertIn("ROUTE_ALREADY_CONTACTED_OTHER_PURPOSE", out["reasons"])

    def test_other_route_same_org_send_blocks_route_fanout(self):
        events = self.allow_events() + [event("sent", "PROVIDER_SENT", "PROVIDER", "2026-09-17T01:30:00-04:00",
                                            route="ceo@example.com", purpose="other-opportunity")]
        out = compile_authority(packet(events))
        self.assertEqual(out["decision"], "HOLD_UNKNOWN")
        self.assertIn("NO_ROUTE_FANOUT_AUTHORITY", out["reasons"])

    def test_other_org_provider_event_does_not_poison_subject(self):
        events = self.allow_events() + [event("sent", "PROVIDER_SENT", "PROVIDER", "2026-09-17T01:30:00-04:00",
                                            org="other.example", route="sales@other.example")]
        self.assertEqual(compile_authority(packet(events))["decision"], "CANDIDATE_ONE_SEND")

    def test_source_binding_rejects_forged_provider_event(self):
        bad = packet(self.allow_events() + [event("sent", "PROVIDER_SENT", "SLACK", "2026-09-17T02:03:00-04:00")])
        with self.assertRaises(AuthorityError):
            compile_authority(bad)

    def test_duplicate_event_id_rejected(self):
        events = self.allow_events(); events.append(copy.deepcopy(events[0]))
        with self.assertRaises(AuthorityError):
            compile_authority(packet(events))

    def test_email_route_normalizes_case(self):
        p = packet(self.allow_events()); p["subject"]["route"] = "Sales@Example.COM"
        for e in p["events"]:
            e["route"] = "SALES@example.com"
        self.assertEqual(compile_authority(p)["decision"], "CANDIDATE_ONE_SEND")

    def test_org_normalizes_case(self):
        p = packet(self.allow_events()); p["subject"]["org"] = "Example.COM"
        for e in p["events"]:
            e["org"] = "EXAMPLE.com"
        self.assertEqual(compile_authority(p)["decision"], "CANDIDATE_ONE_SEND")

    def test_naive_timestamp_rejected(self):
        p = packet(self.allow_events()); p["events"][0]["at"] = "2026-09-17T02:00:00"
        with self.assertRaises(AuthorityError):
            compile_authority(p)

    def test_equivalent_timestamp_offsets_canonicalize_to_same_receipt(self):
        left = packet(self.allow_events())
        right = copy.deepcopy(left)
        right["events"][0]["at"] = "2026-09-17T06:00:00Z"
        right["events"][1]["at"] = "2026-09-17T06:01:00Z"
        right["events"][2]["at"] = "2026-09-17T06:02:00Z"
        self.assertEqual(compile_authority(left), compile_authority(right))

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(AuthorityError):
            strict_json_loads('{"a":1,"a":2}')

    def test_receipt_verifier_is_exact(self):
        p = packet(self.allow_events()); receipt = compile_authority(p); verify_authority(p, receipt)
        bad = copy.deepcopy(receipt); bad["decision"] = "HARD_DNR"
        with self.assertRaises(AuthorityError):
            verify_authority(p, bad)

    def test_event_order_does_not_change_digest_or_result(self):
        self.assertEqual(compile_authority(packet(self.allow_events())),
                         compile_authority(packet(list(reversed(self.allow_events())))))

    def test_fixture_round_trip(self):
        root = Path(__file__).resolve().parents[1]
        fixture = root / "revenue/provider_route_authority/fixtures/two-hard-bounces.json"
        receipt = root / "revenue/provider_route_authority/fixtures/two-hard-bounces.receipt.json"
        raw = strict_json_loads(fixture.read_text(encoding="utf-8"))
        expected = strict_json_loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(compile_authority(raw), expected)
        verify_authority(raw, expected)

    def test_empty_packet_holds(self):
        self.assertEqual(compile_authority(packet([]))["decision"], "HOLD_UNKNOWN")


if __name__ == "__main__":
    unittest.main()
