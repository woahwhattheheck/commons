#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from acceptance import (
    Replay,
    _load_fixture,
    collision_key,
    replay_fixture,
    verify_receipts,
)

HERE = Path(__file__).resolve().parent
LANE = {
    "organization": "Example Industrial",
    "domain": "example.example",
    "route": "ops@example.example",
    "purpose": "paid evidence review",
    "opportunity": "closed period",
}

ROLE_FOR = {
    "PROPOSE": "WORKER",
    "ACQUIRE_LEASE": "WORKER",
    "RELEASE_LEASE": "WORKER",
    "PROVIDER_SENT": "WORKER",
    "PROVIDER_BOUNCE": "WORKER",
    "EXPIRE_LEASE": "SYSTEM",
    "HUMAN_EVENT": "HUMAN_SOURCE",
    "PLACE_HOLD": "OPERATOR",
}


def ev(event_id, at, actor, action, *, role=None, lane=None, **extra):
    return {
        "event_id": event_id,
        "at": at,
        "actor": actor,
        "role": role or ROLE_FOR[action],
        "action": action,
        "lane": deepcopy(lane or LANE),
        **extra,
    }


def leased_replay(*, seconds=30):
    replay = Replay()
    replay.apply(ev("p", "2026-09-17T00:00:00Z", "agent-a", "PROPOSE"))
    replay.apply(
        ev(
            "l",
            "2026-09-17T00:00:01Z",
            "agent-a",
            "ACQUIRE_LEASE",
            lease_seconds=seconds,
        )
    )
    return replay


def sent_replay():
    replay = leased_replay()
    receipt = replay.apply(
        ev(
            "s",
            "2026-09-17T00:00:02Z",
            "agent-a",
            "PROVIDER_SENT",
            provider_receipt="provider-sent-1",
        )
    )
    if not receipt["accepted"]:
        raise AssertionError(receipt)
    return replay


class OneWriterAcceptanceTests(unittest.TestCase):
    def test_demo_fixture_replays(self):
        fixture = json.loads(
            (HERE / "demo_events.json").read_text(encoding="utf-8")
        )
        result = replay_fixture(fixture)
        self.assertTrue(result["ok"])
        self.assertEqual(13, result["events_replayed"])
        self.assertEqual("LEASED", result["final_states"]["acme fabrication"])

    def test_collision_key_normalizes_equivalent_identity(self):
        variant = {
            "organization": "  ＥＸＡＭＰＬＥ   INDUSTRIAL ",
            "domain": "https://www.Example.Example/path",
            "route": "OPS@EXAMPLE.EXAMPLE",
            "purpose": "Paid   Evidence Review",
            "opportunity": "CLOSED PERIOD",
        }
        self.assertEqual(collision_key(LANE), collision_key(variant))

    def test_collision_key_rejects_invisible_and_extra_identity_fields(self):
        invisible = deepcopy(LANE)
        invisible["organization"] = "Example\u200b Industrial"
        with self.assertRaisesRegex(ValueError, "control, format"):
            collision_key(invisible)
        extra = {**LANE, "campaign": "not part of canonical identity"}
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            collision_key(extra)

    def test_concurrent_second_writer_is_denied(self):
        replay = leased_replay()
        denied = replay.apply(
            ev(
                "l2",
                "2026-09-17T00:00:02Z",
                "agent-b",
                "ACQUIRE_LEASE",
                lease_seconds=30,
            )
        )
        self.assertFalse(denied["accepted"])
        self.assertEqual("active_lease", denied["reason"])
        self.assertEqual(1, replay.metrics["collisions_prevented"])

    def test_expired_lease_requires_system_recovery_before_reacquisition(self):
        replay = leased_replay(seconds=5)
        denied = replay.apply(
            ev(
                "l2",
                "2026-09-17T00:00:06Z",
                "agent-b",
                "ACQUIRE_LEASE",
                lease_seconds=30,
            )
        )
        self.assertFalse(denied["accepted"])
        self.assertEqual(
            "expired_lease_requires_system_recovery", denied["reason"]
        )
        expired = replay.apply(
            ev("x", "2026-09-17T00:00:07Z", "system", "EXPIRE_LEASE")
        )
        self.assertTrue(expired["accepted"])
        acquired = replay.apply(
            ev(
                "l3",
                "2026-09-17T00:00:08Z",
                "agent-b",
                "ACQUIRE_LEASE",
                lease_seconds=30,
            )
        )
        self.assertTrue(acquired["accepted"])
        self.assertEqual(1, replay.metrics["stale_leases_recovered"])

    def test_worker_cannot_forge_future_expiry(self):
        replay = leased_replay(seconds=30)
        denied = replay.apply(
            ev(
                "x0",
                "2026-09-17T00:00:31Z",
                "agent-b",
                "EXPIRE_LEASE",
                role="WORKER",
            )
        )
        self.assertFalse(denied["accepted"])
        self.assertEqual("role_requires_system", denied["reason"])
        self.assertEqual("LEASED", denied["next_state"])
        expired = replay.apply(
            ev("x1", "2026-09-17T00:00:32Z", "system", "EXPIRE_LEASE")
        )
        self.assertTrue(expired["accepted"])

    def test_system_role_requires_canonical_system_actor(self):
        replay = leased_replay(seconds=5)
        with self.assertRaisesRegex(ValueError, "canonical system actor"):
            replay.apply(
                ev(
                    "x",
                    "2026-09-17T00:00:06Z",
                    "agent-a",
                    "EXPIRE_LEASE",
                    role="SYSTEM",
                )
            )

    def test_expired_holder_cannot_release_or_publish_provider_outcome(self):
        cases = (
            ("RELEASE_LEASE", {}),
            ("PROVIDER_SENT", {"provider_receipt": "sent-1"}),
            ("PROVIDER_BOUNCE", {"provider_receipt": "bounce-1"}),
        )
        for index, (action, extra) in enumerate(cases):
            with self.subTest(action=action):
                replay = leased_replay(seconds=5)
                denied = replay.apply(
                    ev(
                        f"late-{index}",
                        "2026-09-17T00:00:06Z",
                        "agent-a",
                        action,
                        **extra,
                    )
                )
                self.assertFalse(denied["accepted"])
                self.assertEqual("lease_expired", denied["reason"])
                self.assertEqual("LEASED", denied["next_state"])

    def test_non_holder_cannot_claim_provider_success(self):
        replay = leased_replay()
        denied = replay.apply(
            ev(
                "s",
                "2026-09-17T00:00:02Z",
                "agent-b",
                "PROVIDER_SENT",
                provider_receipt="x",
            )
        )
        self.assertFalse(denied["accepted"])
        self.assertEqual("not_lease_holder", denied["reason"])

    def test_provider_event_requires_receipt_and_worker_role(self):
        replay = leased_replay()
        missing = replay.apply(
            ev("s0", "2026-09-17T00:00:02Z", "agent-a", "PROVIDER_SENT")
        )
        self.assertFalse(missing["accepted"])
        self.assertEqual("missing_provider_receipt", missing["reason"])
        wrong_role = replay.apply(
            ev(
                "s1",
                "2026-09-17T00:00:03Z",
                "agent-a",
                "PROVIDER_SENT",
                role="OPERATOR",
                provider_receipt="x",
            )
        )
        self.assertFalse(wrong_role["accepted"])
        self.assertEqual("role_requires_worker", wrong_role["reason"])

    def test_early_expiry_is_denied_then_stale_recovery_succeeds(self):
        replay = leased_replay()
        early = replay.apply(
            ev("x0", "2026-09-17T00:00:20Z", "system", "EXPIRE_LEASE")
        )
        self.assertFalse(early["accepted"])
        self.assertEqual("lease_not_expired", early["reason"])
        self.assertTrue(
            replay.apply(
                ev("x1", "2026-09-17T00:00:31Z", "system", "EXPIRE_LEASE")
            )["accepted"]
        )
        self.assertTrue(
            replay.apply(
                ev(
                    "l2",
                    "2026-09-17T00:00:32Z",
                    "agent-b",
                    "ACQUIRE_LEASE",
                    lease_seconds=30,
                )
            )["accepted"]
        )
        self.assertEqual(1, replay.metrics["stale_leases_recovered"])

    def test_sent_dnr_fences_duplicate_until_human_event(self):
        replay = sent_replay()
        denied = replay.apply(
            ev(
                "l2",
                "2026-09-17T00:00:03Z",
                "agent-b",
                "ACQUIRE_LEASE",
                lease_seconds=30,
            )
        )
        self.assertFalse(denied["accepted"])
        opened = replay.apply(
            ev(
                "h",
                "2026-09-17T00:00:04Z",
                "buyer-human",
                "HUMAN_EVENT",
                human_event_ref="reply-1",
            )
        )
        self.assertTrue(opened["accepted"])
        self.assertTrue(
            replay.apply(
                ev(
                    "l3",
                    "2026-09-17T00:00:05Z",
                    "agent-b",
                    "ACQUIRE_LEASE",
                    lease_seconds=30,
                )
            )["accepted"]
        )

    def test_human_reopen_requires_human_source_role_and_evidence(self):
        replay = sent_replay()
        wrong_role = replay.apply(
            ev(
                "h0",
                "2026-09-17T00:00:03Z",
                "buyer-human",
                "HUMAN_EVENT",
                role="WORKER",
                human_event_ref="reply-1",
            )
        )
        self.assertFalse(wrong_role["accepted"])
        self.assertEqual("role_requires_human_source", wrong_role["reason"])
        missing = replay.apply(
            ev("h1", "2026-09-17T00:00:04Z", "buyer-human", "HUMAN_EVENT")
        )
        self.assertFalse(missing["accepted"])
        self.assertEqual("missing_human_event_ref", missing["reason"])

    def test_reopened_lane_does_not_fall_back_to_clear_on_release_or_expiry(self):
        replay = sent_replay()
        replay.apply(
            ev(
                "h",
                "2026-09-17T00:00:03Z",
                "buyer-human",
                "HUMAN_EVENT",
                human_event_ref="reply-1",
            )
        )
        replay.apply(
            ev(
                "l2",
                "2026-09-17T00:00:04Z",
                "agent-b",
                "ACQUIRE_LEASE",
                lease_seconds=5,
            )
        )
        released = replay.apply(
            ev("r", "2026-09-17T00:00:05Z", "agent-b", "RELEASE_LEASE")
        )
        self.assertTrue(released["accepted"])
        self.assertEqual("HUMAN_EVENT_REOPEN", released["next_state"])

        replay.apply(
            ev(
                "l3",
                "2026-09-17T00:00:06Z",
                "agent-b",
                "ACQUIRE_LEASE",
                lease_seconds=5,
            )
        )
        expired = replay.apply(
            ev("x", "2026-09-17T00:00:11Z", "system", "EXPIRE_LEASE")
        )
        self.assertTrue(expired["accepted"])
        self.assertEqual("HUMAN_EVENT_REOPEN", expired["next_state"])
        self.assertTrue(
            replay.apply(
                ev(
                    "l4",
                    "2026-09-17T00:00:12Z",
                    "agent-a",
                    "ACQUIRE_LEASE",
                    lease_seconds=5,
                )
            )["accepted"]
        )

    def test_bounce_is_dead_route_not_buyer_rejection(self):
        replay = leased_replay()
        bounced = replay.apply(
            ev(
                "b",
                "2026-09-17T00:00:02Z",
                "agent-a",
                "PROVIDER_BOUNCE",
                provider_receipt="dsn-550",
            )
        )
        self.assertEqual("DEAD_ROUTE", bounced["next_state"])
        self.assertEqual("provider_bounce", bounced["reason"])
        human = replay.apply(
            ev(
                "h",
                "2026-09-17T00:00:03Z",
                "buyer-human",
                "HUMAN_EVENT",
                human_event_ref="unrelated",
            )
        )
        self.assertFalse(human["accepted"])
        self.assertEqual("human_event_not_reopenable", human["reason"])

    def test_operator_role_is_required_for_hold(self):
        replay = Replay()
        replay.apply(ev("p", "2026-09-17T00:00:00Z", "agent-a", "PROPOSE"))
        denied = replay.apply(
            ev(
                "o0",
                "2026-09-17T00:00:01Z",
                "agent-a",
                "PLACE_HOLD",
                role="WORKER",
            )
        )
        self.assertFalse(denied["accepted"])
        self.assertEqual("role_requires_operator", denied["reason"])
        placed = replay.apply(
            ev("o1", "2026-09-17T00:00:02Z", "reviewer", "PLACE_HOLD")
        )
        self.assertTrue(placed["accepted"])
        self.assertEqual("HOLD", placed["next_state"])

    def test_receipt_binds_full_decision_input_and_detects_tamper(self):
        replay = leased_replay()
        sent = replay.apply(
            ev(
                "s",
                "2026-09-17T00:00:02Z",
                "agent-a",
                "PROVIDER_SENT",
                provider_receipt="provider-sent-1",
            )
        )
        decision = sent["decision_input"]
        self.assertEqual("provider-sent-1", decision["provider_receipt"])
        self.assertEqual(LANE["domain"], decision["normalized_lane"]["domain"])
        self.assertEqual(
            30, replay.receipts[1]["decision_input"]["lease_seconds"]
        )
        verify_receipts(replay.receipts)

        tampered = deepcopy(replay.receipts)
        tampered[-1]["decision_input"]["provider_receipt"] = "forged"
        with self.assertRaisesRegex(ValueError, "event digest mismatch"):
            verify_receipts(tampered)

    def test_receipt_chain_detects_payload_tamper(self):
        replay = leased_replay()
        verify_receipts(replay.receipts)
        tampered = deepcopy(replay.receipts)
        tampered[0]["reason"] = "forged"
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            verify_receipts(tampered)

    def test_duplicate_event_id_is_rejected_by_direct_engine(self):
        replay = Replay()
        first = ev("same", "2026-09-17T00:00:00Z", "agent-a", "PROPOSE")
        replay.apply(first)
        duplicate = ev(
            "same",
            "2026-09-17T00:00:01Z",
            "agent-a",
            "ACQUIRE_LEASE",
            lease_seconds=30,
        )
        with self.assertRaisesRegex(ValueError, "duplicate event_id"):
            replay.apply(duplicate)
        self.assertEqual(1, len(replay.receipts))

    def test_event_time_cannot_move_backward(self):
        replay = Replay()
        replay.apply(ev("p", "2026-09-17T00:00:02Z", "agent-a", "PROPOSE"))
        with self.assertRaisesRegex(ValueError, "moved backward"):
            replay.apply(
                ev(
                    "l",
                    "2026-09-17T00:00:01Z",
                    "agent-a",
                    "ACQUIRE_LEASE",
                    lease_seconds=30,
                )
            )

    def test_invalid_lease_duration_is_fail_closed(self):
        for index, seconds in enumerate((None, 0, -1, 3601)):
            with self.subTest(seconds=seconds):
                replay = Replay()
                replay.apply(
                    ev(
                        f"p{index}",
                        "2026-09-17T00:00:00Z",
                        "agent-a",
                        "PROPOSE",
                    )
                )
                extra = {} if seconds is None else {"lease_seconds": seconds}
                denied = replay.apply(
                    ev(
                        f"l{index}",
                        "2026-09-17T00:00:01Z",
                        "agent-a",
                        "ACQUIRE_LEASE",
                        **extra,
                    )
                )
                self.assertFalse(denied["accepted"])
                self.assertEqual("invalid_lease_seconds", denied["reason"])
        replay = Replay()
        replay.apply(ev("p", "2026-09-17T00:00:00Z", "agent-a", "PROPOSE"))
        with self.assertRaisesRegex(ValueError, "must be an integer"):
            replay.apply(
                ev(
                    "l",
                    "2026-09-17T00:00:01Z",
                    "agent-a",
                    "ACQUIRE_LEASE",
                    lease_seconds=True,
                )
            )

    def test_unknown_event_fields_are_rejected_not_dropped_from_receipt(self):
        replay = Replay()
        event = ev("p", "2026-09-17T00:00:00Z", "agent-a", "PROPOSE")
        event["unsealed_hint"] = "ignored would be unsafe"
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            replay.apply(event)

    def test_strict_fixture_loader_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixture.json"
            path.write_text('{"events":[],"events":[]}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                _load_fixture(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
