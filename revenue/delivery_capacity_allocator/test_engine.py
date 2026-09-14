from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from revenue.delivery_capacity_allocator.cli import main as cli_main
from revenue.delivery_capacity_allocator.engine import (
    CapacityError,
    canonical_json,
    compile_bytes,
    sha256_hex,
    strict_json_loads,
    verify_current_bytes,
    verify_historical_bytes,
    write_exclusive,
)

NOW = datetime(2026, 9, 14, 1, 20, 0, tzinfo=timezone.utc)
HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


def j(obj):
    return canonical_json(obj)


def policy(*, cap=1, age=3600, snapshot="2026-09-14T01:15:00Z"):
    return {
        "schema": "tjlabs.delivery-capacity-policy/v1",
        "policy_id": "tjlabs-main",
        "generation": 7,
        "snapshot_at": snapshot,
        "max_age_seconds": age,
        "slots": [
            {"slot_id": "slot-a", "service_class": "evidence-pilot", "starts_at": "2026-09-14T02:00:00Z", "ends_at": "2026-09-14T04:00:00Z", "capacity_units": cap},
            {"slot_id": "slot-b", "service_class": "evidence-pilot", "starts_at": "2026-09-14T05:00:00Z", "ends_at": "2026-09-14T07:00:00Z", "capacity_units": 1},
        ],
    }


def deal(deal_id, *, stage="BUYER_ACCEPTED", units=1, deadline="2026-09-14T04:30:00Z", service="evidence-pilot", accepted="2026-09-14T01:00:00Z"):
    return {
        "deal_id": deal_id,
        "buyer_id": f"buyer-{deal_id}",
        "opportunity_id": f"opp-{deal_id}",
        "service_class": service,
        "requested_units": units,
        "stage": stage,
        "accepted_at": accepted if stage in {"BUYER_ACCEPTED", "FUNDED_TO_START", "FULFILLMENT_READY", "CLOSED_SETTLED"} else None,
        "not_before": "2026-09-14T01:30:00Z",
        "deadline": deadline,
        "source_receipt_sha256": HEX_A,
    }


def demands(rows, snapshot="2026-09-14T01:16:00Z"):
    return {"schema": "tjlabs.delivery-capacity-demand/v1", "policy_id": "tjlabs-main", "generation": 4, "snapshot_at": snapshot, "deals": rows}


def reservations(rows=(), snapshot="2026-09-14T01:17:00Z"):
    return {"schema": "tjlabs.delivery-capacity-reservations/v1", "policy_id": "tjlabs-main", "generation": 9, "snapshot_at": snapshot, "reservations": list(rows)}


def active(deal_id, slot="slot-a", units=1, *, buyer=None, opp=None, service="evidence-pilot"):
    return {
        "reservation_id": f"r-{deal_id}",
        "deal_id": deal_id,
        "buyer_id": buyer or f"buyer-{deal_id}",
        "opportunity_id": opp or f"opp-{deal_id}",
        "slot_id": slot,
        "service_class": service,
        "units": units,
        "state": "ACTIVE",
        "source_receipt_sha256": HEX_A,
    }


def compile_obj(p, d, r, now=NOW):
    pb, db, rb = j(p), j(d), j(r)
    return compile_bytes(pb, db, rb, expected_policy_sha256=sha256_hex(pb), expected_demand_sha256=sha256_hex(db), expected_reservations_sha256=sha256_hex(rb), now=now)


class CapacityTests(unittest.TestCase):
    def test_two_accepted_one_slot_only_one_allocates(self):
        out = compile_obj(policy(), demands([deal("a"), deal("b")]), reservations())
        by = {x["deal_id"]: x for x in out["decisions"]}
        self.assertEqual(by["a"]["decision"], "ALLOCATED_FOR_OWNER_REVIEW")
        self.assertEqual(by["b"]["decision"], "CAPACITY_HOLD")

    def test_funded_beats_accepted(self):
        out = compile_obj(policy(), demands([deal("a", stage="BUYER_ACCEPTED", accepted="2026-09-14T00:00:00Z"), deal("b", stage="FUNDED_TO_START", accepted="2026-09-14T01:10:00Z")]), reservations())
        by = {x["deal_id"]: x for x in out["decisions"]}
        self.assertEqual(by["b"]["decision"], "ALLOCATED_FOR_OWNER_REVIEW")
        self.assertEqual(by["a"]["decision"], "CAPACITY_HOLD")

    def test_earlier_deadline_breaks_same_stage(self):
        p = policy()
        p["slots"] = [p["slots"][0]]
        out = compile_obj(p, demands([deal("late", deadline="2026-09-14T06:00:00Z"), deal("early", deadline="2026-09-14T04:00:00Z")]), reservations())
        by = {x["deal_id"]: x for x in out["decisions"]}
        self.assertEqual(by["early"]["decision"], "ALLOCATED_FOR_OWNER_REVIEW")
        self.assertEqual(by["late"]["decision"], "CAPACITY_HOLD")

    def test_active_reservation_consumes_capacity(self):
        out = compile_obj(policy(), demands([deal("old"), deal("new")]), reservations([active("old")]))
        by = {x["deal_id"]: x for x in out["decisions"]}
        self.assertTrue(by["old"]["existing_reservation"])
        self.assertEqual(by["new"]["decision"], "CAPACITY_HOLD")

    def test_active_reservation_overdraw_holds_globally(self):
        out = compile_obj(policy(), demands([deal("old")]), reservations([active("old", units=2)]))
        self.assertIn("ACTIVE_RESERVATION_OVERDRAW", out["global_blockers"])
        self.assertEqual(out["decisions"][0]["decision"], "CAPACITY_HOLD")

    def test_reservation_rebinding_holds_globally(self):
        out = compile_obj(policy(), demands([deal("old")]), reservations([active("old", buyer="buyer-evil")]))
        self.assertIn("ACTIVE_RESERVATION_DEAL_REBINDING", out["global_blockers"])

    def test_duplicate_active_reservations_for_one_deal_hold(self):
        r1 = active("old")
        r2 = active("old", slot="slot-b")
        r2["reservation_id"] = "r-old-2"
        out = compile_obj(policy(), demands([deal("old", deadline="2026-09-14T08:00:00Z")]), reservations([r1, r2]))
        self.assertIn("DEAL_RESERVATION_COLLISION", out["global_blockers"])

    def test_changed_reserved_units_are_rebinding(self):
        r = active("a", units=1)
        out = compile_obj(policy(cap=4), demands([deal("a", units=2)]), reservations([r]))
        self.assertIn("ACTIVE_RESERVATION_DEAL_REBINDING", out["global_blockers"])

    def test_changed_reserved_source_receipt_is_rebinding(self):
        r = active("a")
        r["source_receipt_sha256"] = HEX_B
        out = compile_obj(policy(), demands([deal("a")]), reservations([r]))
        self.assertIn("ACTIVE_RESERVATION_DEAL_REBINDING", out["global_blockers"])

    def test_naive_trusted_time_rejects(self):
        pb, db, rb = j(policy()), j(demands([deal("a")])), j(reservations())
        with self.assertRaises(CapacityError):
            compile_bytes(
                pb, db, rb,
                expected_policy_sha256=sha256_hex(pb),
                expected_demand_sha256=sha256_hex(db),
                expected_reservations_sha256=sha256_hex(rb),
                now=datetime(2026, 9, 14, 1, 20, 0),
            )

    def test_wrong_service_holds_deal(self):
        out = compile_obj(policy(), demands([deal("a", service="security-review")]), reservations())
        self.assertEqual(out["decisions"][0]["reasons"], ["NO_SERVICE_CLASS_SLOT"])

    def test_window_mismatch_holds_deal(self):
        out = compile_obj(policy(), demands([deal("a", deadline="2026-09-14T03:00:00Z")]), reservations())
        self.assertEqual(out["decisions"][0]["reasons"], ["NO_SLOT_WITHIN_DEAL_WINDOW"])

    def test_no_partial_allocation(self):
        out = compile_obj(policy(cap=2), demands([deal("a", units=3, deadline="2026-09-14T08:00:00Z")]), reservations())
        self.assertEqual(out["decisions"][0]["decision"], "CAPACITY_HOLD")
        self.assertEqual(out["decisions"][0]["units"], 0)

    def test_nonaccepted_is_ineligible(self):
        out = compile_obj(policy(), demands([deal("a", stage="BUYER_INTEREST")]), reservations())
        self.assertEqual(out["decisions"][0]["decision"], "INELIGIBLE")

    def test_permutation_invariant(self):
        d1 = demands([deal("b"), deal("a")])
        d2 = demands([deal("a"), deal("b")])
        o1 = compile_obj(policy(), d1, reservations())
        o2 = compile_obj(policy(), d2, reservations())
        self.assertEqual(o1["allocation_sha256"], o2["allocation_sha256"])
        self.assertEqual(o1["decisions"], o2["decisions"])
        self.assertNotEqual(o1["receipt_sha256"], o2["receipt_sha256"])

    def test_stale_snapshot_holds_currentness(self):
        out = compile_obj(policy(age=30, snapshot="2026-09-14T01:00:00Z"), demands([deal("a")], snapshot="2026-09-14T01:00:00Z"), reservations(snapshot="2026-09-14T01:00:00Z"))
        self.assertNotEqual(out["current_state"], "CURRENT")
        self.assertEqual(out["decisions"][0]["decision"], "CAPACITY_HOLD")

    def test_future_snapshot_holds(self):
        out = compile_obj(policy(snapshot="2026-09-14T01:30:00Z"), demands([deal("a")]), reservations())
        self.assertIn("POLICY_SNAPSHOT_FUTURE", out["global_blockers"])

    def test_expected_digest_mismatch_rejects(self):
        pb, db, rb = j(policy()), j(demands([deal("a")])), j(reservations())
        with self.assertRaises(CapacityError):
            compile_bytes(pb, db, rb, expected_policy_sha256=HEX_C, expected_demand_sha256=sha256_hex(db), expected_reservations_sha256=sha256_hex(rb), now=NOW)

    def test_bool_is_not_integer(self):
        p = policy()
        p["slots"][0]["capacity_units"] = True
        with self.assertRaises(CapacityError):
            compile_obj(p, demands([deal("a")]), reservations())

    def test_duplicate_json_key_rejects(self):
        with self.assertRaises(CapacityError):
            strict_json_loads(b'{"schema":"x","schema":"y"}')

    def test_nonfinite_json_rejects(self):
        with self.assertRaises(CapacityError):
            strict_json_loads(b'{"x": NaN}')

    def test_duplicate_deal_id_rejects(self):
        with self.assertRaises(CapacityError):
            compile_obj(policy(), demands([deal("a"), deal("a")]), reservations())

    def test_duplicate_reservation_id_rejects(self):
        a = active("a")
        b = dict(a)
        with self.assertRaises(CapacityError):
            compile_obj(policy(), demands([deal("a")]), reservations([a, b]))

    def test_historical_verifies_same_allocation_but_never_current(self):
        p, d, r = policy(), demands([deal("a")]), reservations()
        pb, db, rb = j(p), j(d), j(r)
        kws = dict(expected_policy_sha256=sha256_hex(pb), expected_demand_sha256=sha256_hex(db), expected_reservations_sha256=sha256_hex(rb))
        receipt = compile_bytes(pb, db, rb, now=NOW, **kws)
        self.assertEqual(receipt["current_state"], "HISTORICAL_INTEGRITY_ONLY")
        self.assertTrue(verify_historical_bytes(pb, db, rb, canonical_json(receipt), **kws))
        self.assertFalse(verify_current_bytes(pb, db, rb, canonical_json(receipt), now=NOW + timedelta(minutes=5), **kws))

    def test_verify_current_rejects_when_snapshot_ages_out(self):
        p, d, r = policy(age=600), demands([deal("a")]), reservations()
        pb, db, rb = j(p), j(d), j(r)
        kws = dict(expected_policy_sha256=sha256_hex(pb), expected_demand_sha256=sha256_hex(db), expected_reservations_sha256=sha256_hex(rb))
        receipt = compile_bytes(pb, db, rb, now=NOW, **kws)
        self.assertFalse(verify_current_bytes(pb, db, rb, canonical_json(receipt), now=NOW + timedelta(hours=2), **kws))

    def test_verify_current_bad_current_time_fails_closed(self):
        p, d, r = policy(), demands([deal("a")]), reservations()
        pb, db, rb = j(p), j(d), j(r)
        kws = dict(expected_policy_sha256=sha256_hex(pb), expected_demand_sha256=sha256_hex(db), expected_reservations_sha256=sha256_hex(rb))
        receipt = compile_bytes(pb, db, rb, now=NOW, **kws)
        self.assertFalse(verify_current_bytes(pb, db, rb, canonical_json(receipt), now=datetime(2026, 9, 14, 1, 25, 0), **kws))

    def test_receipt_tamper_rejects(self):
        p, d, r = policy(), demands([deal("a")]), reservations()
        pb, db, rb = j(p), j(d), j(r)
        kws = dict(expected_policy_sha256=sha256_hex(pb), expected_demand_sha256=sha256_hex(db), expected_reservations_sha256=sha256_hex(rb))
        receipt = compile_bytes(pb, db, rb, now=NOW, **kws)
        receipt["decisions"][0]["decision"] = "ALLOCATED_FOR_OWNER_REVIEW" if receipt["decisions"][0]["decision"] != "ALLOCATED_FOR_OWNER_REVIEW" else "CAPACITY_HOLD"
        self.assertFalse(verify_historical_bytes(pb, db, rb, canonical_json(receipt), **kws))

    def test_all_external_authority_false(self):
        out = compile_obj(policy(), demands([deal("a")]), reservations())
        self.assertTrue(out["authority"])
        self.assertFalse(any(out["authority"].values()))

    def test_write_exclusive_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "out.json")
            write_exclusive(path, b"one")
            with self.assertRaises(CapacityError):
                write_exclusive(path, b"two")
            with open(path, "rb") as fh:
                self.assertEqual(fh.read(), b"one")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_write_exclusive_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            target = os.path.join(td, "target")
            link = os.path.join(td, "link")
            with open(target, "wb") as fh:
                fh.write(b"safe")
            os.symlink(target, link)
            with self.assertRaises(CapacityError):
                write_exclusive(link, b"evil")
            with open(target, "rb") as fh:
                self.assertEqual(fh.read(), b"safe")

    def test_cli_compile_then_verify(self):
        with tempfile.TemporaryDirectory() as td:
            p, d, r = j(policy()), j(demands([deal("a")])), j(reservations())
            paths = {}
            for name, data in (("p", p), ("d", d), ("r", r)):
                path = os.path.join(td, name + ".json")
                with open(path, "wb") as fh:
                    fh.write(data)
                paths[name] = path
            out = os.path.join(td, "receipt.json")
            rc = cli_main(["compile", "--policy", paths["p"], "--demands", paths["d"], "--reservations", paths["r"], "--policy-sha", sha256_hex(p), "--demand-sha", sha256_hex(d), "--reservations-sha", sha256_hex(r), "--out", out])
            self.assertEqual(rc, 3)
            self.assertTrue(os.path.exists(out))
            verify_rc = cli_main(["verify", "--policy", paths["p"], "--demands", paths["d"], "--reservations", paths["r"], "--policy-sha", sha256_hex(p), "--demand-sha", sha256_hex(d), "--reservations-sha", sha256_hex(r), "--receipt", out])
            self.assertEqual(verify_rc, 3)


if __name__ == "__main__":
    unittest.main()
