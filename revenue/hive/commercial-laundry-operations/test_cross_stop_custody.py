from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from laundry_desk import InvoiceBlocked, LaundryDesk, StateConflict


class CrossStopCustodyCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "desk.sqlite3")
        self.desk = LaundryDesk(self.db)
        d = self.desk
        d.add_customer("seed.ca", "cust-a", "Customer A")
        d.add_customer("seed.cb", "cust-b", "Customer B")
        d.add_site("seed.sa", "site-a", "cust-a", "Site A")
        d.add_site("seed.sb", "site-b", "cust-b", "Site B")
        for site, suffix in (("site-a", "a"), ("site-b", "b")):
            d.add_agreement(f"seed.agr.{suffix}", f"agr-{suffix}", site, "sheet", 100, "2026-01-01")
        d.add_service_plan("seed.plan.a", "plan-a", "site-a", "route-one", 0, 10, "2026-01-01")
        d.add_service_plan("seed.plan.b", "plan-b", "site-b", "route-one", 0, 20, "2026-01-01")
        route = d.create_daily_route("seed.route", "2026-09-21", "route-one").value
        self.route_id = route["route_id"]
        self.stop_a, self.stop_b = [row["stop_id"] for row in route["stops"]]

    def tearDown(self):
        self.tmp.cleanup()

    def _process(self, desk: LaundryDesk, key: str, stop_id: str):
        return desk.process(key, stop_id, {"sheet": 1}, {"sheet": 0})

    def test_shared_container_sequential_pickup_rejected_and_restart_persists(self):
        self.desk.pickup("seq.a", self.stop_a, {"sheet": 1}, ["BIN-SHARED"])
        reopened = LaundryDesk(self.db)
        with self.assertRaises(StateConflict):
            reopened.pickup("seq.b", self.stop_b, {"sheet": 1}, ["BIN-SHARED"])
        snap = reopened.route_snapshot(self.route_id)
        self.assertEqual(snap["stops"][0]["state"], "PICKED_UP")
        self.assertEqual(snap["stops"][0]["pickup_containers"], ["BIN-SHARED"])
        self.assertEqual(snap["stops"][1]["state"], "MANIFESTED")
        self.assertEqual(snap["stops"][1]["pickup_containers"], [])

    def test_shared_container_concurrent_pickup_has_exactly_one_owner(self):
        barrier = threading.Barrier(2)
        results: list[tuple[str, str]] = []
        lock = threading.Lock()

        def worker(label: str, stop_id: str):
            local = LaundryDesk(self.db)
            barrier.wait()
            try:
                local.pickup(f"race.{label}", stop_id, {"sheet": 1}, ["BIN-RACE"])
                result = "ok"
            except StateConflict:
                result = "conflict"
            with lock:
                results.append((label, result))

        t1 = threading.Thread(target=worker, args=("a", self.stop_a))
        t2 = threading.Thread(target=worker, args=("b", self.stop_b))
        t1.start(); t2.start(); t1.join(); t2.join()
        self.assertCountEqual([result for _, result in results], ["ok", "conflict"])
        snap = self.desk.route_snapshot(self.route_id)
        owners = [s for s in snap["stops"] if s["pickup_containers"] == ["BIN-RACE"]]
        self.assertEqual(len(owners), 1)
        self.assertEqual(sum(s["state"] == "PICKED_UP" for s in snap["stops"]), 1)
        self.assertEqual(sum(s["state"] == "MANIFESTED" for s in snap["stops"]), 1)

    def test_clean_delivery_releases_container_for_next_stop(self):
        self.desk.pickup("reuse.a.pickup", self.stop_a, {"sheet": 1}, ["BIN-REUSE"])
        self._process(self.desk, "reuse.a.process", self.stop_a)
        self.desk.deliver("reuse.a.deliver", self.stop_a, {"sheet": 1}, ["BIN-REUSE"])
        result = self.desk.pickup("reuse.b.pickup", self.stop_b, {"sheet": 1}, ["BIN-REUSE"])
        self.assertEqual(result.value["state"], "PICKED_UP")

    def test_missing_container_stays_reserved_until_explicit_resolution(self):
        self.desk.pickup("missing.a.pickup", self.stop_a, {"sheet": 1}, ["BIN-HELD"])
        self._process(self.desk, "missing.a.process", self.stop_a)
        delivered = self.desk.deliver(
            "missing.a.deliver", self.stop_a, {"sheet": 1}, ["BIN-OTHER"]
        ).value
        snap = self.desk.route_snapshot(self.route_id)
        missing = [
            exc for exc in snap["stops"][0]["exceptions"]
            if exc["kind"] == "CUSTODY_MISSING" and exc["item_code"] == "BIN-HELD"
        ]
        self.assertEqual(len(missing), 1)
        self.assertIn(missing[0]["exception_id"], delivered["open_exception_ids"])
        with self.assertRaises(InvoiceBlocked):
            self.desk.draft_invoice("missing.a.invoice.blocked", self.stop_a)
        with self.assertRaises(StateConflict):
            self.desk.pickup("missing.b.blocked", self.stop_b, {"sheet": 1}, ["BIN-HELD"])
        self.desk.resolve_exception(
            "missing.a.release",
            missing[0]["exception_id"],
            "OWNER_TRANSFER_RECONCILED",
            "Owner explicitly released missing container custody",
        )
        result = self.desk.pickup("missing.b.pickup", self.stop_b, {"sheet": 1}, ["BIN-HELD"])
        self.assertEqual(result.value["state"], "PICKED_UP")

    def test_delivery_cannot_claim_container_active_on_other_stop(self):
        self.desk.pickup("delivery.a.pickup", self.stop_a, {"sheet": 1}, ["BIN-SHARED"])
        self.desk.pickup("delivery.b.pickup", self.stop_b, {"sheet": 1}, ["BIN-B"])
        self._process(self.desk, "delivery.a.process", self.stop_a)
        self._process(self.desk, "delivery.b.process", self.stop_b)
        with self.assertRaises(StateConflict):
            self.desk.deliver("delivery.b.bad", self.stop_b, {"sheet": 1}, ["BIN-SHARED"])
        snap = self.desk.route_snapshot(self.route_id)
        self.assertEqual(snap["stops"][1]["state"], "PROCESSED")
        self.assertEqual(snap["stops"][1]["delivery_containers"], [])
        self.desk.deliver("delivery.b.good", self.stop_b, {"sheet": 1}, ["BIN-B"])
        self.assertEqual(self.desk.route_snapshot(self.route_id)["stops"][1]["state"], "DELIVERED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
