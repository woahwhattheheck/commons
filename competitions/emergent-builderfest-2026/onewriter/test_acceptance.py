#!/usr/bin/env python3
import json
import unittest
from copy import deepcopy
from pathlib import Path

from acceptance import Replay, collision_key, replay_fixture, verify_receipts

HERE = Path(__file__).resolve().parent
LANE = {"organization":"Example Industrial","domain":"example.example","route":"ops@example.example","purpose":"paid evidence review","opportunity":"closed period"}


def ev(event_id, at, actor, action, **extra):
    return {"event_id":event_id,"at":at,"actor":actor,"action":action,"lane":deepcopy(LANE),**extra}


class OneWriterAcceptanceTests(unittest.TestCase):
    def test_demo_fixture_replays(self):
        fixture = json.loads((HERE / "demo_events.json").read_text(encoding="utf-8"))
        result = replay_fixture(fixture)
        self.assertTrue(result["ok"])
        self.assertEqual(13, result["events_replayed"])

    def test_collision_key_normalizes_equivalent_identity(self):
        variant = {"organization":"  EXAMPLE   INDUSTRIAL ","domain":"https://www.Example.Example/path","route":"OPS@EXAMPLE.EXAMPLE","purpose":"Paid   Evidence Review","opportunity":"CLOSED PERIOD"}
        self.assertEqual(collision_key(LANE), collision_key(variant))

    def test_concurrent_second_writer_is_denied(self):
        r = Replay(); r.apply(ev("p","2026-09-17T00:00:00Z","a","PROPOSE")); r.apply(ev("l1","2026-09-17T00:00:01Z","a","ACQUIRE_LEASE",lease_seconds=30))
        denied = r.apply(ev("l2","2026-09-17T00:00:02Z","b","ACQUIRE_LEASE",lease_seconds=30))
        self.assertFalse(denied["accepted"]); self.assertEqual("active_lease", denied["reason"]); self.assertEqual(1, r.metrics["collisions_prevented"])

    def test_non_holder_cannot_claim_provider_success(self):
        r = Replay(); r.apply(ev("p","2026-09-17T00:00:00Z","a","PROPOSE")); r.apply(ev("l","2026-09-17T00:00:01Z","a","ACQUIRE_LEASE",lease_seconds=30))
        denied = r.apply(ev("s","2026-09-17T00:00:02Z","b","PROVIDER_SENT",provider_receipt="x"))
        self.assertFalse(denied["accepted"]); self.assertEqual("not_lease_holder", denied["reason"])

    def test_provider_event_requires_receipt(self):
        r = Replay(); r.apply(ev("p","2026-09-17T00:00:00Z","a","PROPOSE")); r.apply(ev("l","2026-09-17T00:00:01Z","a","ACQUIRE_LEASE",lease_seconds=30))
        denied = r.apply(ev("s","2026-09-17T00:00:02Z","a","PROVIDER_SENT"))
        self.assertFalse(denied["accepted"]); self.assertEqual("missing_provider_receipt", denied["reason"])

    def test_early_expiry_is_denied_then_stale_recovery_succeeds(self):
        r = Replay(); r.apply(ev("p","2026-09-17T00:00:00Z","a","PROPOSE")); r.apply(ev("l","2026-09-17T00:00:01Z","a","ACQUIRE_LEASE",lease_seconds=30))
        early = r.apply(ev("x0","2026-09-17T00:00:20Z","system","EXPIRE_LEASE")); self.assertFalse(early["accepted"]); self.assertEqual("lease_not_expired", early["reason"])
        self.assertTrue(r.apply(ev("x1","2026-09-17T00:00:31Z","system","EXPIRE_LEASE"))["accepted"])
        self.assertTrue(r.apply(ev("l2","2026-09-17T00:00:32Z","b","ACQUIRE_LEASE",lease_seconds=30))["accepted"]); self.assertEqual(1, r.metrics["stale_leases_recovered"])

    def test_sent_dnr_fences_duplicate_until_human_event(self):
        r = Replay(); r.apply(ev("p","2026-09-17T00:00:00Z","a","PROPOSE")); r.apply(ev("l","2026-09-17T00:00:01Z","a","ACQUIRE_LEASE",lease_seconds=30))
        self.assertEqual("SENT_DNR", r.apply(ev("s","2026-09-17T00:00:02Z","a","PROVIDER_SENT",provider_receipt="sent-1"))["next_state"])
        self.assertFalse(r.apply(ev("l2","2026-09-17T00:00:03Z","b","ACQUIRE_LEASE",lease_seconds=30))["accepted"])
        self.assertTrue(r.apply(ev("h","2026-09-17T00:00:04Z","buyer","HUMAN_EVENT",human_event_ref="reply-1"))["accepted"])
        self.assertTrue(r.apply(ev("l3","2026-09-17T00:00:05Z","b","ACQUIRE_LEASE",lease_seconds=30))["accepted"])

    def test_bounce_is_dead_route_not_buyer_rejection(self):
        r = Replay(); r.apply(ev("p","2026-09-17T00:00:00Z","a","PROPOSE")); r.apply(ev("l","2026-09-17T00:00:01Z","a","ACQUIRE_LEASE",lease_seconds=30))
        bounced = r.apply(ev("b","2026-09-17T00:00:02Z","a","PROVIDER_BOUNCE",provider_receipt="dsn-550"))
        self.assertEqual("DEAD_ROUTE", bounced["next_state"]); self.assertEqual("provider_bounce", bounced["reason"])
        human = r.apply(ev("h","2026-09-17T00:00:03Z","buyer","HUMAN_EVENT",human_event_ref="unrelated")); self.assertFalse(human["accepted"]); self.assertEqual("human_event_not_reopenable", human["reason"])

    def test_receipt_chain_detects_tamper(self):
        r = Replay(); r.apply(ev("p","2026-09-17T00:00:00Z","a","PROPOSE")); r.apply(ev("l","2026-09-17T00:00:01Z","a","ACQUIRE_LEASE",lease_seconds=30)); verify_receipts(r.receipts)
        tampered = deepcopy(r.receipts); tampered[0]["reason"] = "forged"
        with self.assertRaisesRegex(ValueError, "digest mismatch"): verify_receipts(tampered)

    def test_invalid_lease_duration_is_fail_closed(self):
        r = Replay(); r.apply(ev("p","2026-09-17T00:00:00Z","a","PROPOSE"))
        for seconds in (0,-1,3601):
            denied = r.apply(ev(f"l{seconds}","2026-09-17T00:00:01Z","a","ACQUIRE_LEASE",lease_seconds=seconds)); self.assertFalse(denied["accepted"]); self.assertEqual("invalid_lease_seconds", denied["reason"])


if __name__ == "__main__":
    unittest.main()
