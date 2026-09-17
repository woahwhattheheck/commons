from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import tools.relationship_contact_guard.guard as guard
from tools.relationship_contact_guard.guard import (
    GuardError,
    compile_guard,
    load_json,
    verify_guard,
)


def stamp(*, seconds_ago: int = 0, seconds_ahead: int = 0) -> str:
    dt = datetime.now(timezone.utc).replace(microsecond=0)
    dt = dt - timedelta(seconds=seconds_ago) + timedelta(seconds=seconds_ahead)
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def candidate(**overrides):
    row = {
        "counterparty_id": "example.com",
        "opportunity_id": "example-rfp-1",
        "route": "sales@example.com",
        "purpose": "paid-qa-workshare",
    }
    row.update(overrides)
    return row


def sent(
    event_id="s1",
    *,
    seconds_ago=3600,
    route="ops@example.com",
    purpose="other-purpose",
    opportunity="example-rfp-1",
    message="m1",
    thread=None,
):
    row = {
        "event_id": event_id,
        "kind": "PROVIDER_SENT",
        "occurred_at": stamp(seconds_ago=seconds_ago),
        "counterparty_id": "example.com",
        "opportunity_id": opportunity,
        "route": route,
        "purpose": purpose,
        "provider_message_id": message,
    }
    if thread is not None:
        row["provider_thread_id"] = thread
    return row


def response(
    kind,
    event_id,
    *,
    seconds_ago=3500,
    route="ops@example.com",
    purpose="other-purpose",
    opportunity="example-rfp-1",
    message="m1",
    thread=None,
    scope=None,
    reopens_event_id=None,
):
    row = {
        "event_id": event_id,
        "kind": kind,
        "occurred_at": stamp(seconds_ago=seconds_ago),
        "counterparty_id": "example.com",
        "opportunity_id": opportunity,
        "route": route,
        "purpose": purpose,
        "in_reply_to_message_id": message,
    }
    if thread is not None:
        row["provider_thread_id"] = thread
    if scope is not None:
        row["scope"] = scope
    if reopens_event_id is not None:
        row["reopens_event_id"] = reopens_event_id
    return row


def bounce(**kwargs):
    return response("PROVIDER_BOUNCE", "b1", **kwargs)


def reply(**kwargs):
    return response("HUMAN_REPLY", "r1", **kwargs)


def negative(
    scope,
    event_id="n1",
    *,
    seconds_ago=3500,
    route="sales@example.com",
    purpose="paid-qa-workshare",
    opportunity="example-rfp-1",
    message="m1",
    thread=None,
):
    return response(
        "HUMAN_NEGATIVE",
        event_id,
        seconds_ago=seconds_ago,
        route=route,
        purpose=purpose,
        opportunity=opportunity,
        message=message,
        thread=thread,
        scope=scope,
    )


def reopen(
    blocker="n1",
    scope="COUNTERPARTY",
    event_id="o1",
    *,
    seconds_ago=3400,
    route="sales@example.com",
    purpose="paid-qa-workshare",
    opportunity="example-rfp-1",
    message="m1",
    thread=None,
):
    return response(
        "HUMAN_REOPEN",
        event_id,
        seconds_ago=seconds_ago,
        route=route,
        purpose=purpose,
        opportunity=opportunity,
        message=message,
        thread=thread,
        scope=scope,
        reopens_event_id=blocker,
    )


class RelationshipGuardTests(unittest.TestCase):
    def compile(self, events=(), **candidate_overrides):
        return compile_guard({"candidate": candidate(**candidate_overrides), "events": list(events)})

    def test_01_empty_packet_is_diagnostic_only_and_process_timed(self):
        out = self.compile()
        self.assertEqual(out["decision"]["status"], "NO_CONFLICT_FOUND")
        self.assertEqual(out["decision"]["evaluation_mode"], "CURRENT")
        self.assertTrue(out["decision"]["truth"]["evaluation_time_is_process_owned"])
        self.assertFalse(out["decision"]["truth"]["verify_replay_establishes_currentness"])
        self.assertFalse(out["decision"]["truth"]["no_conflict_is_send_permission"])
        self.assertFalse(any(out["decision"]["authority"].values()))

    def test_02_candidate_now_is_rejected(self):
        with self.assertRaises(GuardError):
            self.compile(now=stamp(seconds_ago=10_000_000))

    def test_03_same_counterparty_different_route_holds(self):
        out = self.compile([sent()])
        self.assertEqual(out["decision"]["status"], "HOLD_RECENT_COUNTERPARTY_CONTACT")
        self.assertEqual(out["decision"]["blocker_event_ids"], ["s1"])

    def test_04_same_opportunity_purpose_cross_key_holds_after_six_hours(self):
        row = sent(seconds_ago=7 * 3600, route="other@example.com", purpose="paid-qa-workshare")
        out = self.compile([row])
        self.assertEqual(out["decision"]["status"], "HOLD_RECENT_PURSUIT_CONTACT")

    def test_05_exact_unanswered_send_is_dnr(self):
        row = sent(route="sales@example.com", purpose="paid-qa-workshare")
        out = self.compile([row])
        self.assertEqual(out["decision"]["status"], "HOLD_EXACT_DNR")

    def test_06_bounce_is_route_scoped_not_org_rejection(self):
        s = sent()
        b = bounce()
        out = self.compile([s, b])
        self.assertEqual(out["decision"]["status"], "NO_CONFLICT_FOUND")
        self.assertFalse(out["decision"]["authority"]["send_authorized"])

    def test_07_bounced_candidate_route_is_dead_route(self):
        s = sent(route="sales@example.com", purpose="paid-qa-workshare")
        b = bounce(route="sales@example.com", purpose="paid-qa-workshare")
        out = self.compile([s, b])
        self.assertEqual(out["decision"]["status"], "HOLD_DEAD_ROUTE")

    def test_08_counterparty_negative_blocks_other_route(self):
        s = sent(route="sales@example.com", purpose="paid-qa-workshare")
        n = negative("COUNTERPARTY")
        out = self.compile([s, n])
        self.assertEqual(out["decision"]["status"], "HOLD_COUNTERPARTY_OPT_OUT")

    def test_09_route_negative_does_not_poison_other_route_after_old_contact(self):
        s = sent(
            seconds_ago=4 * 24 * 3600,
            route="old@example.com",
            purpose="other-purpose",
            message="old1",
        )
        n = negative(
            "ROUTE_PURPOSE",
            seconds_ago=4 * 24 * 3600 - 60,
            route="old@example.com",
            purpose="other-purpose",
            message="old1",
        )
        out = self.compile([s, n])
        self.assertEqual(out["decision"]["status"], "NO_CONFLICT_FOUND")

    def test_10_exact_reopen_clears_counterparty_negative_only(self):
        s = sent(
            seconds_ago=4 * 24 * 3600,
            route="sales@example.com",
            purpose="paid-qa-workshare",
        )
        n = negative(
            "COUNTERPARTY",
            seconds_ago=4 * 24 * 3600 - 60,
        )
        o = reopen(seconds_ago=24 * 3600)
        out = self.compile([s, n, o])
        self.assertEqual(out["decision"]["status"], "NO_CONFLICT_FOUND")
        self.assertFalse(out["decision"]["authority"]["send_authorized"])

    def test_11_reopen_must_reference_existing_negative(self):
        s = sent(route="sales@example.com", purpose="paid-qa-workshare")
        o = reopen(blocker="missing")
        with self.assertRaises(GuardError):
            self.compile([s, o])

    def test_12_reopen_scope_must_match_blocker(self):
        s = sent(route="sales@example.com", purpose="paid-qa-workshare")
        n = negative("COUNTERPARTY")
        o = reopen(scope="ROUTE_PURPOSE")
        with self.assertRaises(GuardError):
            self.compile([s, n, o])

    def test_13_reopen_identity_must_match_blocker(self):
        s = sent(route="sales@example.com", purpose="paid-qa-workshare")
        n = negative("COUNTERPARTY")
        o = reopen(opportunity="different-rfp")
        with self.assertRaises(GuardError):
            self.compile([s, n, o])

    def test_14_human_reply_moves_to_inbound_review(self):
        s = sent(seconds_ago=4 * 24 * 3600)
        r = reply(seconds_ago=4 * 24 * 3600 - 60)
        out = self.compile([s, r])
        self.assertEqual(out["decision"]["status"], "HOLD_INBOUND_REVIEW")

    def test_15_response_opportunity_transplant_rejected(self):
        s = sent()
        r = reply(opportunity="different-rfp")
        with self.assertRaisesRegex(GuardError, "transplant"):
            self.compile([s, r])

    def test_16_response_route_transplant_rejected(self):
        s = sent()
        r = reply(route="sales@example.com")
        with self.assertRaisesRegex(GuardError, "transplant"):
            self.compile([s, r])

    def test_17_response_purpose_transplant_rejected(self):
        s = sent()
        r = reply(purpose="paid-qa-workshare")
        with self.assertRaisesRegex(GuardError, "transplant"):
            self.compile([s, r])

    def test_18_response_thread_omission_rejected(self):
        s = sent(thread="t1")
        r = reply()
        with self.assertRaisesRegex(GuardError, "thread"):
            self.compile([s, r])

    def test_19_response_thread_swap_rejected(self):
        s = sent(thread="t1")
        r = reply(thread="t2")
        with self.assertRaisesRegex(GuardError, "thread"):
            self.compile([s, r])

    def test_20_future_event_rejected(self):
        row = sent()
        row["occurred_at"] = stamp(seconds_ahead=3600)
        with self.assertRaises(GuardError):
            self.compile([row])

    def test_21_reordered_events_rejected(self):
        s = sent(seconds_ago=3000)
        b = bounce(seconds_ago=4000)
        with self.assertRaises(GuardError):
            self.compile([s, b])

    def test_22_duplicate_event_id_rejected(self):
        a = sent(event_id="dup", message="m1", seconds_ago=4000)
        b = sent(event_id="dup", message="m2", seconds_ago=3000)
        with self.assertRaises(GuardError):
            self.compile([a, b])

    def test_23_duplicate_provider_message_id_rejected(self):
        a = sent(event_id="s1", message="same", seconds_ago=4000)
        b = sent(event_id="s2", message="same", seconds_ago=3000)
        with self.assertRaises(GuardError):
            self.compile([a, b])

    def test_24_orphan_response_rejected(self):
        with self.assertRaises(GuardError):
            self.compile([reply(message="missing")])

    def test_25_cross_counterparty_transplant_rejected(self):
        row = sent()
        row["counterparty_id"] = "attacker.example"
        with self.assertRaises(GuardError):
            self.compile([row])

    def test_26_noncanonical_unicode_identifier_rejected(self):
        with self.assertRaises(GuardError):
            self.compile([], route="sáles@example.com")

    def test_27_cooldown_floors_cannot_be_weakened(self):
        with self.assertRaises(GuardError):
            self.compile([], relationship_cooldown_seconds=1)
        with self.assertRaises(GuardError):
            self.compile([], pursuit_cooldown_seconds=1)

    def test_28_receipt_and_retained_time_recompile_reject_mutation(self):
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

    def test_29_strict_json_duplicate_key_rejected(self):
        text = '{"candidate":{"counterparty_id":"example.com","counterparty_id":"evil.com","opportunity_id":"x","route":"a@example.com","purpose":"p"},"events":[]}'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "packet.json"
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(GuardError):
                load_json(path)

    def test_30_large_integer_parser_valueerror_normalized(self):
        text = '{"candidate":{"counterparty_id":"example.com","opportunity_id":"x","route":"a@example.com","purpose":"p","relationship_cooldown_seconds":' + ("9" * 5000) + '},"events":[]}'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "packet.json"
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(GuardError):
                load_json(path)

    def test_31_exported_authority_mutation_cannot_widen_compile_or_verify(self):
        original = guard.AUTHORITY
        try:
            guard.AUTHORITY = {key: True for key in original}
            packet = {"candidate": candidate(), "events": []}
            artifact = compile_guard(packet)
            self.assertFalse(any(artifact["decision"]["authority"].values()))
            self.assertTrue(verify_guard(packet, artifact))
        finally:
            guard.AUTHORITY = original

    def test_32_artifact_evaluation_mode_cannot_be_relabelled(self):
        packet = {"candidate": candidate(), "events": []}
        artifact = compile_guard(packet)
        artifact["decision"]["evaluation_mode"] = "HISTORICAL"
        with self.assertRaises(GuardError):
            verify_guard(packet, artifact)

    def test_33_authority_ceiling_exact_false(self):
        out = self.compile()
        self.assertEqual(set(out["decision"]["authority"]), set(guard.AUTHORITY))
        self.assertFalse(any(out["decision"]["authority"].values()))
        self.assertFalse(out["decision"]["truth"]["retained_packet_complete"])
        self.assertFalse(out["decision"]["truth"]["provider_authentication_established_here"])


if __name__ == "__main__":
    unittest.main()
