#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from coordination.revenue_lane_state.core import (
    ContractError,
    canonical_bytes,
    compile_from_json,
    compile_state,
    strict_json_loads,
    verify_artifact,
)
from coordination.revenue_lane_state import cli

EVAL = "2026-09-17T21:00:00Z"
IDENTITY = {
    "lane_id": "lane-1",
    "opportunity_id": "opp-1",
    "counterparty_id": "org-1",
    "purpose_id": "teaming-1",
}


def ev(
    event_id: str,
    generation: int,
    kind: str,
    source_class: str,
    when: str,
    *,
    route_id: str | None = None,
    supersedes: str | None = None,
):
    row = {
        "event_id": event_id,
        **IDENTITY,
        "generation": generation,
        "kind": kind,
        "source_class": source_class,
        "source_ref": f"ref:{event_id}",
        "occurred_at": when,
    }
    if route_id is not None:
        row["route_id"] = route_id
    if supersedes is not None:
        row["supersedes"] = supersedes
    return row


def packet(events, *, currentness_seconds=604800):
    return {
        "schema_version": 1,
        **IDENTITY,
        "currentness_seconds": currentness_seconds,
        "events": events,
    }


class RevenueLaneStateTest(unittest.TestCase):
    def compile(self, events, body="", *, eval_time=EVAL, currentness_seconds=604800):
        return compile_state(
            packet(events, currentness_seconds=currentness_seconds),
            body_text=body,
            evaluation_time=eval_time,
        )

    def test_raleigh_stale_not_sent_becomes_sent_dnr(self):
        result = self.compile(
            [
                ev("research", 1, "RESEARCHED", "coordination", "2026-09-16T10:00:00Z"),
                ev("sent", 2, "PROVIDER_SENT", "provider", "2026-09-16T13:11:36Z", route_id="route-a"),
            ],
            body="Truth: OUTBOUND NOT YET SENT / $0 booked",
        )
        self.assertEqual(result["state"], "SENT_DNR_PENDING_EVENT")
        self.assertEqual([f["code"] for f in result["stale_body_findings"]], ["NOT_SENT"])
        self.assertFalse(result["patch_plan"]["apply"])

    def test_e470_identity_receipt_is_distinct(self):
        a = self.compile([ev("sent-a", 1, "PROVIDER_SENT", "provider", "2026-09-17T04:35:47Z")])
        other = packet([ev("sent-a", 1, "PROVIDER_SENT", "provider", "2026-09-17T04:35:47Z")])
        other["lane_id"] = "lane-e470"
        other["events"][0]["lane_id"] = "lane-e470"
        b = compile_state(other, body_text="", evaluation_time=EVAL)
        self.assertEqual(a["state"], b["state"])
        self.assertNotEqual(a["semantic_receipt_sha256"], b["semantic_receipt_sha256"])

    def test_pi9_two_sends_same_generation_is_collision(self):
        result = self.compile(
            [
                ev("bounce1", 1, "BOUNCED", "provider", "2026-09-17T07:46:42Z", route_id="learn"),
                ev("select2", 2, "MUSE_SELECTED", "coordination", "2026-09-17T19:00:00Z", route_id="sales"),
                ev("sent2a", 2, "PROVIDER_SENT", "provider", "2026-09-17T19:08:17Z", route_id="sales"),
                ev("sent2b", 2, "PROVIDER_SENT", "provider", "2026-09-17T19:08:42Z", route_id="sales"),
            ],
            body="PARTNER ROUTE RECOVERY / MUSE-PENDING",
        )
        self.assertEqual(result["state"], "COLLISION_DUPLICATE_SEND_DNR")
        self.assertIn("MUSE_PENDING", [f["code"] for f in result["stale_body_findings"]])

    def test_packet_received_flags_packet_pending_without_minting_eligibility(self):
        result = self.compile(
            [
                ev("req", 1, "PACKET_REQUESTED", "procurement", "2026-09-13T12:00:00Z"),
                ev("recv", 2, "PACKET_RECEIVED", "provider", "2026-09-14T12:00:00Z"),
            ],
            body="packet recovery pending; direct prime eligibility unknown",
        )
        self.assertEqual(result["state"], "PACKET_RECEIVED")
        self.assertEqual([f["code"] for f in result["stale_body_findings"]], ["PACKET_PENDING"])
        self.assertNotIn("PARTNER_CONFIRMED", canonical_bytes(result).decode())

    def test_human_decline_is_current_dnr_and_flags_await_reply(self):
        result = self.compile(
            [
                ev("sent", 1, "PROVIDER_SENT", "provider", "2026-09-13T14:05:27Z"),
                ev("decline", 2, "HUMAN_DECLINE", "human", "2026-09-14T12:12:05Z"),
            ],
            body="awaiting reply from aligned training partner",
        )
        self.assertEqual(result["state"], "HUMAN_DECLINE_DNR")
        self.assertEqual([f["code"] for f in result["stale_body_findings"]], ["AWAIT_REPLY"])

    def test_kentucky_body_no_contact_is_flagged_after_send(self):
        result = self.compile(
            [ev("sent", 1, "PROVIDER_SENT", "provider", "2026-09-13T06:51:58Z")],
            body="No buyer or partner contact. Next authorized action: one inquiry.",
        )
        self.assertEqual(result["state"], "SENT_DNR_PENDING_EVENT")
        self.assertIn("NO_PARTNER_CONTACT", [f["code"] for f in result["stale_body_findings"]])

    def test_bounce_is_transport_truth_not_human_decline(self):
        result = self.compile(
            [
                ev("attempt", 1, "PROVIDER_SEND_ATTEMPTED", "provider", "2026-09-17T07:46:40Z"),
                ev("bounce", 1, "BOUNCED", "provider", "2026-09-17T07:46:42Z"),
            ]
        )
        self.assertEqual(result["state"], "BOUNCED_DEAD_ROUTE")
        self.assertNotEqual(result["state"], "HUMAN_DECLINE_DNR")

    def test_selection_alone_never_mints_provider_sent(self):
        result = self.compile([ev("select", 1, "MUSE_SELECTED", "coordination", "2026-09-17T20:00:00Z")])
        self.assertEqual(result["state"], "SELECTED_UNCONSUMED_NO_SEND_AUTHORITY")

    def test_human_reply_requires_human_source(self):
        with self.assertRaisesRegex(ContractError, "cannot be proven"):
            self.compile([ev("auto", 1, "HUMAN_REPLY", "auto", "2026-09-17T20:00:00Z")])

    def test_event_identity_transplant_fails(self):
        row = ev("x", 1, "RESEARCHED", "coordination", "2026-09-17T20:00:00Z")
        row["counterparty_id"] = "other-org"
        with self.assertRaisesRegex(ContractError, "transplant"):
            self.compile([row])

    def test_duplicate_event_id_fails_even_if_semantics_same(self):
        row = ev("dup", 1, "RESEARCHED", "coordination", "2026-09-17T20:00:00Z")
        with self.assertRaisesRegex(ContractError, "duplicate event_id"):
            self.compile([row, dict(row)])

    def test_generation_regression_fails(self):
        with self.assertRaisesRegex(ContractError, "generation chronology regressed"):
            self.compile([
                ev("g2", 2, "RESEARCHED", "coordination", "2026-09-17T19:00:00Z"),
                ev("g1", 1, "TAKE", "coordination", "2026-09-17T20:00:00Z"),
            ])

    def test_future_event_fails(self):
        with self.assertRaisesRegex(ContractError, "future event"):
            self.compile([ev("future", 1, "RESEARCHED", "coordination", "2026-09-18T00:00:00Z")])

    def test_historical_actionable_state_becomes_hold(self):
        result = self.compile(
            [ev("pending", 1, "MUSE_PENDING", "coordination", "2026-09-10T00:00:00Z")],
            currentness_seconds=3600,
        )
        self.assertEqual(result["state"], "HOLD_EVIDENCE")

    def test_strict_json_rejects_duplicate_keys_float_and_unsafe_int(self):
        for raw in (
            '{"a":1,"a":1}',
            '{"a":1.5}',
            '{"a":9007199254740992}',
            '{"a":NaN}',
        ):
            with self.subTest(raw=raw):
                with self.assertRaises(ContractError):
                    strict_json_loads(raw)

    def test_bool_as_generation_rejected(self):
        row = ev("b", 1, "RESEARCHED", "coordination", "2026-09-17T20:00:00Z")
        row["generation"] = True
        with self.assertRaisesRegex(ContractError, "generation"):
            self.compile([row])

    def test_lone_surrogate_and_control_shaped_id_rejected(self):
        with self.assertRaises(ContractError):
            strict_json_loads('{"x":"\\ud800"}')
        row = ev("bad\nid", 1, "RESEARCHED", "coordination", "2026-09-17T20:00:00Z")
        with self.assertRaisesRegex(ContractError, "event_id"):
            self.compile([row])

    def test_supersession_removes_stale_intent_but_preserves_new_truth(self):
        result = self.compile([
            ev("pending", 1, "MUSE_PENDING", "coordination", "2026-09-17T19:00:00Z"),
            ev("correction", 2, "EVIDENCE_HOLD", "coordination", "2026-09-17T19:30:00Z", supersedes="pending"),
        ])
        self.assertEqual(result["state"], "HOLD_EVIDENCE")

    def test_prior_provider_send_survives_later_coordination_generation(self):
        result = self.compile([
            ev("sent", 1, "PROVIDER_SENT", "provider", "2026-09-17T19:00:00Z"),
            ev("select", 2, "MUSE_SELECTED", "coordination", "2026-09-17T20:00:00Z"),
        ])
        self.assertEqual(result["state"], "SENT_DNR_PENDING_EVENT")
        self.assertFalse(result["input_authentication"]["verified_by_compiler"])

    def test_coordination_superseder_cannot_erase_provider_truth(self):
        with self.assertRaisesRegex(ContractError, "source authority mismatch"):
            self.compile([
                ev("sent", 1, "PROVIDER_SENT", "provider", "2026-09-17T19:00:00Z"),
                ev("hold", 2, "EVIDENCE_HOLD", "coordination", "2026-09-17T20:00:00Z", supersedes="sent"),
            ])

    def test_cross_generation_second_provider_send_is_collision(self):
        result = self.compile([
            ev("sent1", 1, "PROVIDER_SENT", "provider", "2026-09-17T18:00:00Z", route_id="route-a"),
            ev("select2", 2, "MUSE_SELECTED", "coordination", "2026-09-17T19:00:00Z", route_id="route-b"),
            ev("sent2", 2, "PROVIDER_SENT", "provider", "2026-09-17T19:05:00Z", route_id="route-b"),
        ])
        self.assertEqual(result["state"], "COLLISION_DUPLICATE_SEND_DNR")

    def test_provider_send_cannot_be_hidden_by_provider_correction(self):
        with self.assertRaisesRegex(ContractError, "provider send evidence cannot be superseded"):
            self.compile([
                ev("sent1", 1, "PROVIDER_SENT", "provider", "2026-09-17T18:00:00Z"),
                ev("sent2", 2, "PROVIDER_SENT", "provider", "2026-09-17T19:00:00Z", supersedes="sent1"),
            ])

    def test_same_source_human_correction_can_retire_stale_modeled_state(self):
        result = self.compile([
            ev("decline", 1, "HUMAN_DECLINE", "human", "2026-09-17T18:00:00Z"),
            ev("reply", 2, "HUMAN_REPLY", "human", "2026-09-17T19:00:00Z", supersedes="decline"),
        ])
        self.assertEqual(result["state"], "HUMAN_REPLY_ACTIONABLE")

    def test_same_source_provider_correction_can_retire_stale_modeled_state(self):
        result = self.compile([
            ev("bounce", 1, "BOUNCED", "provider", "2026-09-17T18:00:00Z"),
            ev("dead", 2, "DEAD_ROUTE", "provider", "2026-09-17T19:00:00Z", supersedes="bounce"),
        ])
        self.assertEqual(result["state"], "BOUNCED_DEAD_ROUTE")

    def test_fresh_coordination_does_not_refresh_stale_human_reply(self):
        result = self.compile(
            [
                ev("reply", 1, "HUMAN_REPLY", "human", "2026-09-17T18:00:00Z"),
                ev("take", 2, "TAKE", "coordination", "2026-09-17T20:30:00Z"),
            ],
            currentness_seconds=3600,
        )
        self.assertEqual(result["state"], "HOLD_EVIDENCE")

    def test_equal_time_mutual_supersession_cycle_fails_closed(self):
        with self.assertRaisesRegex(ContractError, "supersession chronology invalid"):
            self.compile([
                ev("a", 1, "PROVIDER_SENT", "provider", "2026-09-17T19:00:00Z", supersedes="b"),
                ev("b", 1, "PROVIDER_SENT", "provider", "2026-09-17T19:00:00Z", supersedes="a"),
            ])

    def test_strict_json_normalizes_large_integer_and_deep_nesting(self):
        cases = [
            '{"a":' + ("9" * 5000) + "}",
            ("[" * 1000) + "0" + ("]" * 1000),
        ]
        for raw in cases:
            with self.assertRaises(ContractError):
                strict_json_loads(raw)

    def test_packet_cannot_select_unbounded_currentness_horizon(self):
        with self.assertRaisesRegex(ContractError, "compiler maximum"):
            self.compile(
                [ev("reply", 1, "HUMAN_REPLY", "human", "2026-01-01T00:00:00Z")],
                currentness_seconds=9007199254740991,
            )

    def test_lease_consumed_without_provider_event_stays_hold(self):
        result = self.compile([
            ev("selected", 1, "MUSE_SELECTED", "coordination", "2026-09-17T20:00:00Z"),
            ev("lease", 1, "LEASE_CONSUMED", "coordination", "2026-09-17T20:01:00Z"),
        ])
        self.assertEqual(result["state"], "HOLD_EVIDENCE")

    def test_conflicting_terminal_procurement_truth_fails_closed(self):
        with self.assertRaisesRegex(ContractError, "conflicting terminal procurement"):
            self.compile([
                ev("lost", 1, "LOST", "procurement", "2026-09-17T19:00:00Z"),
                ev("awarded", 1, "AWARDED", "procurement", "2026-09-17T19:01:00Z"),
            ])

    def test_expired_and_submitted_truth_fails_closed(self):
        with self.assertRaisesRegex(ContractError, "expired and submitted"):
            self.compile([
                ev("submitted", 1, "SUBMITTED", "procurement", "2026-09-17T19:00:00Z"),
                ev("expired", 1, "EXPIRED", "procurement", "2026-09-17T19:01:00Z"),
            ])

    def test_human_decline_and_partner_acceptance_fails_closed(self):
        with self.assertRaisesRegex(ContractError, "human decline and partner acceptance"):
            self.compile([
                ev("decline", 1, "HUMAN_DECLINE", "human", "2026-09-17T19:00:00Z"),
                ev("accept", 1, "PARTNER_ACCEPTED", "human", "2026-09-17T19:01:00Z"),
            ])

    def test_superseded_history_remains_bound_into_event_digest(self):
        corrected = self.compile([
            ev("pending", 1, "MUSE_PENDING", "coordination", "2026-09-17T19:00:00Z"),
            ev("hold", 2, "EVIDENCE_HOLD", "coordination", "2026-09-17T19:30:00Z", supersedes="pending"),
        ])
        hold_only = self.compile([
            ev("hold", 2, "EVIDENCE_HOLD", "coordination", "2026-09-17T19:30:00Z"),
        ])
        self.assertEqual(corrected["state"], hold_only["state"])
        self.assertNotEqual(
            corrected["event_digest_sha256"],
            hold_only["event_digest_sha256"],
        )

    def test_patch_plan_refuses_malformed_existing_block(self):
        body = "<!-- REVENUE_LANE_CURRENT_STATE:BEGIN -->\nmissing end"
        with self.assertRaisesRegex(ContractError, "malformed"):
            self.compile([ev("r", 1, "RESEARCHED", "coordination", "2026-09-17T20:00:00Z")], body)

    def test_verifier_detects_changed_source_semantics(self):
        p = packet([ev("sent", 1, "PROVIDER_SENT", "provider", "2026-09-17T20:00:00Z")])
        pbytes = canonical_bytes(p)
        artifact = canonical_bytes(compile_state(p, body_text="", evaluation_time=EVAL))
        self.assertTrue(verify_artifact(pbytes, artifact, body_text="", evaluation_time=EVAL))
        changed = json.loads(pbytes)
        changed["events"][0]["source_ref"] = "ref:changed"
        with self.assertRaisesRegex(ContractError, "exactly replay"):
            verify_artifact(canonical_bytes(changed), artifact, body_text="", evaluation_time=EVAL)

    def test_cli_compile_verify_and_create_exclusive(self):
        p = packet([ev("r", 1, "RESEARCHED", "coordination", "2026-09-17T20:00:00Z")])
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            events = td / "events.json"
            body = td / "body.md"
            artifact = td / "artifact.json"
            events.write_bytes(canonical_bytes(p))
            body.write_text("fresh lane", encoding="utf-8")
            self.assertEqual(cli.main([
                "compile", "--events", str(events), "--body", str(body),
                "--evaluation-time", EVAL, "--output", str(artifact)
            ]), 0)
            self.assertEqual(cli.main([
                "verify", "--events", str(events), "--body", str(body),
                "--evaluation-time", EVAL, "--artifact", str(artifact)
            ]), 0)
            self.assertEqual(cli.main([
                "compile", "--events", str(events), "--body", str(body),
                "--evaluation-time", EVAL, "--output", str(artifact)
            ]), 2)


if __name__ == "__main__":
    unittest.main()
