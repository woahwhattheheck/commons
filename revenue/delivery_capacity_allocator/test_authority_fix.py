from __future__ import annotations

import unittest

from revenue.delivery_capacity_allocator.engine import (
    canonical_json,
    compile_bytes,
    compile_current_bytes,
    sha256_hex,
    verify_current_receipt_bytes,
)
from revenue.delivery_capacity_allocator.test_engine import (
    NOW,
    active,
    deal,
    demands,
    j,
    policy,
    reservations,
)


class CapacityAuthorityFixTests(unittest.TestCase):
    def test_production_current_fails_closed_without_retained_root_authority(self):
        pb = j(policy())
        db = j(demands([deal("a")]))
        rb = j(reservations())
        out = compile_current_bytes(pb, db, rb)
        self.assertEqual(out["current_state"], "HOLD_RETAINED_ROOT_AUTHORITY")
        self.assertIn("RETAINED_ROOT_AUTHORITY_UNAVAILABLE", out["global_blockers"])
        by = {row["deal_id"]: row for row in out["decisions"]}
        self.assertEqual(by["a"]["decision"], "CAPACITY_HOLD")

    def test_future_acceptance_is_global_hold(self):
        out = compile_bytes(
            j(policy()),
            j(demands([deal("a", accepted="2026-09-14T01:30:00Z")])),
            j(reservations()),
            expected_policy_sha256=sha256_hex(j(policy())),
            expected_demand_sha256=sha256_hex(j(demands([deal("a", accepted="2026-09-14T01:30:00Z")]))),
            expected_reservations_sha256=sha256_hex(j(reservations())),
            now=NOW,
        )
        self.assertIn("DEAL_ACCEPTED_AT_FUTURE", out["global_blockers"])
        self.assertEqual(out["decisions"][0]["decision"], "CAPACITY_HOLD")

    def test_ended_slot_cannot_receive_new_allocation(self):
        p = policy()
        p["slots"] = [{
            "slot_id": "slot-a",
            "service_class": "evidence-pilot",
            "starts_at": "2026-09-14T00:30:00Z",
            "ends_at": "2026-09-14T01:00:00Z",
            "capacity_units": 2,
        }]
        d = demands([deal("a", deadline="2026-09-14T03:00:00Z")])
        r = reservations()
        pb, db, rb = j(p), j(d), j(r)
        out = compile_bytes(
            pb,
            db,
            rb,
            expected_policy_sha256=sha256_hex(pb),
            expected_demand_sha256=sha256_hex(db),
            expected_reservations_sha256=sha256_hex(rb),
            now=NOW,
        )
        self.assertEqual(out["decisions"][0]["decision"], "CAPACITY_HOLD")
        self.assertEqual(out["decisions"][0]["reasons"], ["NO_SLOT_WITHIN_DEAL_WINDOW"])

    def test_orphan_active_reservation_holds_and_still_consumes_capacity(self):
        p = policy(cap=2)
        d = demands([deal("new")])
        r = reservations([active("ghost")])
        pb, db, rb = j(p), j(d), j(r)
        out = compile_bytes(
            pb,
            db,
            rb,
            expected_policy_sha256=sha256_hex(pb),
            expected_demand_sha256=sha256_hex(db),
            expected_reservations_sha256=sha256_hex(rb),
            now=NOW,
        )
        self.assertIn("ACTIVE_RESERVATION_ORPHAN_DEAL", out["global_blockers"])
        slot_a = {row["slot_id"]: row for row in out["slot_balances"]}["slot-a"]
        self.assertEqual(slot_a["remaining_units"], 1)
        self.assertEqual(out["decisions"][0]["decision"], "CAPACITY_HOLD")

    def test_active_reservation_on_ended_slot_holds(self):
        p = policy()
        p["slots"][0]["starts_at"] = "2026-09-14T00:30:00Z"
        p["slots"][0]["ends_at"] = "2026-09-14T01:00:00Z"
        d = demands([deal("old")])
        r = reservations([active("old")])
        pb, db, rb = j(p), j(d), j(r)
        out = compile_bytes(
            pb,
            db,
            rb,
            expected_policy_sha256=sha256_hex(pb),
            expected_demand_sha256=sha256_hex(db),
            expected_reservations_sha256=sha256_hex(rb),
            now=NOW,
        )
        self.assertIn("ACTIVE_RESERVATION_SLOT_ENDED", out["global_blockers"])
        self.assertEqual(out["decisions"][0]["decision"], "CAPACITY_HOLD")
        self.assertTrue(out["decisions"][0]["existing_reservation"])

    def test_self_minted_historical_receipt_never_passes_production_verifier(self):
        p, d, r = policy(), demands([deal("a")]), reservations()
        pb, db, rb = j(p), j(d), j(r)
        receipt = compile_bytes(
            pb,
            db,
            rb,
            expected_policy_sha256=sha256_hex(pb),
            expected_demand_sha256=sha256_hex(db),
            expected_reservations_sha256=sha256_hex(rb),
            now=NOW,
        )
        self.assertEqual(receipt["current_state"], "CURRENT")
        self.assertFalse(
            verify_current_receipt_bytes(pb, db, rb, canonical_json(receipt))
        )


if __name__ == "__main__":
    unittest.main()
