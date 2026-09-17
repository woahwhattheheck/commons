from __future__ import annotations

import copy
import hashlib
import unittest

from revenue.revenue_experiment_allocator.engine import (
    AllocationError,
    compile_bundle,
    compile_packet,
    verify_bundle,
)


def _sha(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def segment(
    sid: str,
    *,
    attempts: int = 10,
    delivered: int = 9,
    human_replies: int = 3,
    positive_replies: int = 2,
    proposals: int = 1,
    accepted: int = 0,
    paid: int = 0,
    cash: int = 0,
    available: int = 20,
    dnr: int = 0,
    collisions: int = 0,
    census: bool = True,
    route: bool = True,
    unresolved: bool = False,
    observed: str = "2026-09-17T07:00:00Z",
):
    return {
        "segment_id": sid,
        "offer_id": "offer-" + sid,
        "route_kind": "EMAIL",
        "audience_label": "Synthetic " + sid,
        "evidence_observed_at": observed,
        "evidence_ref": "fixture://" + sid,
        "evidence_sha256": _sha(sid),
        "available_candidates": available,
        "attempts": attempts,
        "delivered": delivered,
        "human_replies": human_replies,
        "positive_replies": positive_replies,
        "proposals": proposals,
        "accepted": accepted,
        "paid": paid,
        "retained_cash_cents": cash,
        "dnr_events": dnr,
        "collision_events": collisions,
        "fresh_census_complete": census,
        "route_available": route,
        "unresolved_collision": unresolved,
    }


def document(segments, *, batch=10, share=4000, exploration=2, max_age=168):
    return {
        "schema": "TJL_REVENUE_EXPERIMENT_ALLOCATOR_V1",
        "evaluation_at": "2026-09-17T08:00:00Z",
        "batch_size": batch,
        "max_segment_share_bps": share,
        "exploration_slots": exploration,
        "max_evidence_age_hours": max_age,
        "segments": segments,
    }


class RevenueExperimentAllocatorTests(unittest.TestCase):
    def test_paid_signal_ranked_first_without_headline_ticket(self):
        paid = segment("paid", accepted=1, paid=1, cash=250000)
        reply = segment("reply")
        packet = compile_packet(document([reply, paid], batch=2, share=5000, exploration=0))
        self.assertEqual([o["segment_id"] for o in packet["orders"]], ["paid", "reply"])
        self.assertFalse(packet["policy"]["rank_uses_headline_ticket_value"])
        self.assertFalse(packet["summary"]["provider_authenticated_outcomes_available"])

    def test_hard_share_cap_prevents_one_segment_consuming_batch(self):
        paid = segment("paid", human_replies=6, positive_replies=5, proposals=4, accepted=3, paid=2, cash=500000, available=100)
        other = segment("other", available=100)
        packet = compile_packet(document([paid, other], batch=10, share=3000, exploration=0))
        by_id = {r["segment_id"]: r for r in packet["segments"]}
        self.assertLessEqual(by_id["paid"]["allocated_slots"], 3)
        self.assertLessEqual(by_id["other"]["allocated_slots"], 3)
        self.assertEqual(packet["summary"]["unallocated_slot_count"], 4)

    def test_exploration_reserves_slot_for_nonpaid_signal(self):
        paid = segment("paid", human_replies=7, positive_replies=6, proposals=5, accepted=4, paid=3, cash=900000, available=50)
        explore = segment("explore", available=50)
        packet = compile_packet(document([paid, explore], batch=4, share=7500, exploration=1))
        by_id = {r["segment_id"]: r for r in packet["segments"]}
        self.assertGreaterEqual(by_id["explore"]["allocated_slots"], 1)
        self.assertIn("EXPLORATION", by_id["explore"]["allocation_role"])

    def test_unresolved_collision_holds_entire_segment(self):
        s = segment("collision", unresolved=True)
        row = compile_packet(document([s], batch=5, share=10_000, exploration=0))["segments"][0]
        self.assertEqual(row["state"], "HOLD_COLLISION")
        self.assertEqual(row["allocated_slots"], 0)

    def test_incomplete_census_holds(self):
        row = compile_packet(document([segment("census", census=False)], batch=1, share=10_000, exploration=0))["segments"][0]
        self.assertEqual(row["state"], "HOLD_CENSUS_INCOMPLETE")
        self.assertEqual(row["next_action"], "NONE")

    def test_stale_evidence_holds(self):
        row = compile_packet(
            document([segment("stale", observed="2026-09-01T08:00:00Z")], batch=1, share=10_000, exploration=0, max_age=24)
        )["segments"][0]
        self.assertEqual(row["state"], "HOLD_STALE_EVIDENCE")

    def test_route_unavailable_holds(self):
        row = compile_packet(document([segment("route", route=False)], batch=1, share=10_000, exploration=0))["segments"][0]
        self.assertEqual(row["state"], "HOLD_ROUTE_UNAVAILABLE")

    def test_every_order_stops_before_recipient_selection_and_send(self):
        packet = compile_packet(document([segment("a")], batch=1, share=10_000, exploration=0))
        order = packet["orders"][0]
        row = packet["segments"][0]
        self.assertIsNone(order["recipient_identifiers"])
        self.assertEqual(order["authority"], "PLANNING_ONLY_NOT_SEND_AUTHORITY")
        self.assertTrue(row["muse_required_before_any_external_contact"])
        self.assertTrue(row["fresh_recipient_census_required_before_any_external_contact"])
        self.assertFalse(row["external_send_authorized"])
        self.assertFalse(row["recipient_selection_authorized"])

    def test_monotone_funnel_required(self):
        bad = segment("bad")
        bad["positive_replies"] = bad["human_replies"] + 1
        with self.assertRaisesRegex(AllocationError, "monotone"):
            compile_packet(document([bad]))

    def test_cash_without_paid_signal_rejected(self):
        with self.assertRaisesRegex(AllocationError, "cash without"):
            compile_packet(document([segment("cash", cash=1)]))

    def test_paid_without_cash_rejected(self):
        with self.assertRaisesRegex(AllocationError, "positive retained cash"):
            compile_packet(document([segment("paid", accepted=1, paid=1, cash=0)]))

    def test_duplicate_evidence_binding_rejected(self):
        a = segment("a")
        b = segment("b")
        b["evidence_ref"] = a["evidence_ref"]
        b["evidence_sha256"] = a["evidence_sha256"]
        with self.assertRaisesRegex(AllocationError, "duplicate evidence"):
            compile_packet(document([a, b]))

    def test_future_evidence_rejected(self):
        with self.assertRaisesRegex(AllocationError, "future evidence"):
            compile_packet(document([segment("future", observed="2026-09-17T09:00:00Z")]))

    def test_bundle_tamper_fails_verification(self):
        bundle = compile_bundle(document([segment("a")], batch=1, share=10_000, exploration=0))
        self.assertTrue(verify_bundle(bundle))
        bad = copy.deepcopy(bundle)
        bad["packet"]["orders"][0]["allocated_slots"] = 99
        self.assertFalse(verify_bundle(bad))

    def test_zero_batch_is_valid_and_allocates_nothing(self):
        packet = compile_packet(document([segment("a")], batch=0, share=0, exploration=0))
        self.assertEqual(packet["orders"], [])
        self.assertEqual(packet["summary"]["allocated_slot_count"], 0)

    def test_integer_rates_are_deterministic(self):
        s = segment("rate", attempts=3, delivered=2, human_replies=1, positive_replies=1, proposals=0)
        row = compile_packet(document([s], batch=0, share=0, exploration=0))["segments"][0]
        self.assertEqual(row["retained_signal"]["delivery_rate_bps"], 6666)
        self.assertEqual(row["retained_signal"]["human_reply_rate_bps"], 5000)


    def test_unknown_route_kind_rejected(self):
        bad = segment("route-kind")
        bad["route_kind"] = "SMS"
        with self.assertRaisesRegex(AllocationError, "unsupported"):
            compile_packet(document([bad]))

    def test_bool_does_not_alias_integer(self):
        bad = segment("bool-int")
        bad["attempts"] = True
        with self.assertRaisesRegex(AllocationError, "integer"):
            compile_packet(document([bad]))

    def test_duplicate_segment_id_rejected(self):
        with self.assertRaisesRegex(AllocationError, "duplicate segment"):
            compile_packet(document([segment("dup"), segment("dup")]))

    def test_exploration_cannot_exceed_batch(self):
        with self.assertRaisesRegex(AllocationError, "exploration_slots"):
            compile_packet(document([segment("a")], batch=1, share=10_000, exploration=2))

    def test_paid_signal_with_incomplete_census_never_allocates(self):
        s = segment(
            "paid-held",
            human_replies=5,
            positive_replies=4,
            proposals=3,
            accepted=2,
            paid=1,
            cash=100_000,
            census=False,
            available=100,
        )
        row = compile_packet(
            document([s], batch=10, share=10_000, exploration=0)
        )["segments"][0]
        self.assertEqual(row["state"], "HOLD_CENSUS_INCOMPLETE")
        self.assertEqual(row["allocated_slots"], 0)

    def test_historical_dnr_and_collision_metrics_rank_but_do_not_authorize_or_hold(self):
        s = segment("history", dnr=2, collisions=1)
        packet = compile_packet(document([s], batch=1, share=10_000, exploration=0))
        row = packet["segments"][0]
        self.assertEqual(row["state"], "READY")
        self.assertEqual(row["allocated_slots"], 1)
        self.assertFalse(row["external_send_authorized"])
        self.assertTrue(row["fresh_recipient_census_required_before_any_external_contact"])

    def test_summary_authority_ceiling(self):
        packet = compile_packet(document([segment("a")], batch=1, share=10_000, exploration=0))
        self.assertEqual(
            packet["authority"],
            {
                "external_send": False,
                "recipient_selection": False,
                "muse_selection": False,
                "provider_mutation": False,
                "contact_creation": False,
                "payment_movement": False,
                "receivable_establishment": False,
                "accounting_assertion": False,
                "revenue_recognition": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
