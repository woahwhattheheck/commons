from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from laundry_desk import (
    AUTHORITY,
    IdempotencyConflict,
    InvoiceBlocked,
    LaundryDesk,
    StateConflict,
    ValidationError,
)


class DeskCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "desk.sqlite3")
        self.desk = LaundryDesk(self.db)
        self._seed()

    def tearDown(self):
        self.tmp.cleanup()

    def _seed(self):
        d = self.desk
        d.add_customer("op.ca", "cust-a", "Customer A")
        d.add_customer("op.cb", "cust-b", "Customer B")
        d.add_site("op.sa", "site-a", "cust-a", "Site A")
        d.add_site("op.sb", "site-b", "cust-b", "Site B")
        for site, letter in (("site-a", "a"), ("site-b", "b")):
            d.add_agreement(f"op.agr.{letter}.sheet", f"agr-{letter}-sheet", site, "sheet", 125, "2026-01-01")
            d.add_agreement(f"op.agr.{letter}.towel", f"agr-{letter}-towel", site, "towel", 75, "2026-01-01")
        d.add_service_plan("op.plan.a", "plan-a", "site-a", "route-one", 0, 10, "2026-01-01")
        d.add_service_plan("op.plan.b", "plan-b", "site-b", "route-one", 0, 20, "2026-01-01")

    def _route(self):
        return self.desk.create_daily_route("op.route", "2026-09-21", "route-one").value

    def _good_stop(self, stop_id, prefix="x"):
        self.desk.pickup(f"{prefix}.pickup", stop_id, {"sheet": 10, "towel": 20}, [f"{prefix}-c1"])
        self.desk.process(f"{prefix}.process", stop_id, {"sheet": 10, "towel": 20}, {"sheet": 0, "towel": 0})
        self.desk.deliver(f"{prefix}.deliver", stop_id, {"sheet": 10, "towel": 20}, [f"{prefix}-c1"])

    def test_two_account_manifest_is_deterministic(self):
        route = self._route()
        self.assertEqual([s["site_id"] for s in route["stops"]], ["site-a", "site-b"])
        self.assertEqual([s["sequence"] for s in route["stops"]], [10, 20])
        self.assertEqual(route["route_id"], "route:2026-09-21:route-one")

    def test_exact_retry_is_noop_changed_content_fails(self):
        first = self.desk.add_customer("op.retry", "cust-c", "Customer C")
        second = self.desk.add_customer("op.retry", "cust-c", "Customer C")
        self.assertFalse(first.replayed)
        self.assertTrue(second.replayed)
        before = len(self.desk.event_history())
        with self.assertRaises(IdempotencyConflict):
            self.desk.add_customer("op.retry", "cust-c", "Changed")
        self.assertEqual(len(self.desk.event_history()), before)

    def test_processing_shortage_blocks_invoice_until_resolved(self):
        stop = self._route()["stops"][0]["stop_id"]
        self.desk.pickup("s.pickup", stop, {"sheet": 10}, ["bin-1"])
        result = self.desk.process("s.process", stop, {"sheet": 9}, {"sheet": 0}).value
        self.assertEqual(len(result["open_exception_ids"]), 1)
        self.desk.deliver("s.deliver", stop, {"sheet": 9}, ["bin-1"])
        with self.assertRaises(InvoiceBlocked):
            self.desk.draft_invoice("s.invoice.blocked", stop)
        self.desk.resolve_exception("s.resolve", result["open_exception_ids"][0], "COUNT_ACCEPTED", "Owner accepted shortage")
        inv = self.desk.draft_invoice("s.invoice", stop).value
        self.assertEqual(inv["state"], "DRAFT")
        self.assertEqual(inv["total_cents"], 9 * 125)

    def test_damage_is_explicit_and_blocks(self):
        stop = self._route()["stops"][0]["stop_id"]
        self.desk.pickup("d.pickup", stop, {"towel": 5}, ["bin-1"])
        result = self.desk.process("d.process", stop, {"towel": 4}, {"towel": 1}).value
        self.assertEqual(len(result["open_exception_ids"]), 1)
        snap = self.desk.route_snapshot("route:2026-09-21:route-one")
        kinds = [e["kind"] for e in snap["stops"][0]["exceptions"]]
        self.assertEqual(kinds, ["DAMAGE"])

    def test_delivery_mismatch_blocks(self):
        stop = self._route()["stops"][0]["stop_id"]
        self.desk.pickup("m.pickup", stop, {"sheet": 10}, ["bin-1"])
        self.desk.process("m.process", stop, {"sheet": 10}, {"sheet": 0})
        result = self.desk.deliver("m.deliver", stop, {"sheet": 8}, ["bin-1"]).value
        self.assertEqual(len(result["open_exception_ids"]), 1)
        with self.assertRaises(InvoiceBlocked):
            self.desk.draft_invoice("m.invoice", stop)

    def test_integer_cents_only(self):
        with self.assertRaises(ValidationError):
            self.desk.add_agreement("bad.float", "bad-float", "site-a", "napkin", 1.25, "2026-01-01")
        with self.assertRaises(ValidationError):
            self.desk.add_agreement("bad.bool", "bad-bool", "site-a", "napkin", True, "2026-01-01")

    def test_overlapping_price_authority_rejected(self):
        with self.assertRaises(StateConflict):
            self.desk.add_agreement("overlap", "overlap", "site-a", "sheet", 150, "2026-06-01")

    def test_restart_preserves_state_and_exports(self):
        stop = self._route()["stops"][0]["stop_id"]
        self._good_stop(stop, "r")
        invoice = self.desk.draft_invoice("r.invoice", stop).value
        reopened = LaundryDesk(self.db)
        snap = reopened.route_snapshot("route:2026-09-21:route-one")
        self.assertEqual(snap["stops"][0]["invoice"]["total_cents"], invoice["total_cents"])
        e1 = reopened.render_route_exports(snap["route_id"])
        e2 = reopened.render_route_exports(snap["route_id"])
        self.assertEqual(e1, e2)
        self.assertIn("invoice_total_cents", e1["csv"])
        self.assertIn("# Route", e1["markdown"])

    def test_customer_exports_cover_agreements(self):
        exports = self.desk.render_customer_exports("cust-a")
        self.assertIn("agr-a-sheet", exports["json"])
        self.assertIn("unit_price_cents", exports["csv"])
        self.assertIn("# Customer cust-a", exports["markdown"])

    def test_authority_flags_remain_false(self):
        stop = self._route()["stops"][0]["stop_id"]
        self._good_stop(stop, "a")
        invoice = self.desk.draft_invoice("a.invoice", stop).value
        self.assertTrue(AUTHORITY)
        self.assertTrue(all(value is False for value in invoice["authority"].values()))
        snap = self.desk.route_snapshot("route:2026-09-21:route-one")
        self.assertTrue(all(value is False for value in snap["authority"].values()))

    def test_events_are_immutable_in_storage(self):
        self._route()
        con = sqlite3.connect(self.db)
        try:
            with self.assertRaises(sqlite3.DatabaseError):
                con.execute("UPDATE events SET event_type='X' WHERE seq=1")
            with self.assertRaises(sqlite3.DatabaseError):
                con.execute("DELETE FROM events WHERE seq=1")
        finally:
            con.close()

    def test_integrity_reconciles_operations_and_events(self):
        self._route()
        result = self.desk.verify_integrity()
        self.assertEqual(result["integrity"], "PASS")
        self.assertEqual(result["operations"], result["events"])

    def test_competing_deliveries_cannot_double_apply(self):
        stop = self._route()["stops"][0]["stop_id"]
        self.desk.pickup("c.pickup", stop, {"sheet": 10}, ["bin-1"])
        self.desk.process("c.process", stop, {"sheet": 10}, {"sheet": 0})
        barrier = threading.Barrier(2)
        results = []
        lock = threading.Lock()

        def worker(key, container):
            local = LaundryDesk(self.db)
            barrier.wait()
            try:
                local.deliver(key, stop, {"sheet": 10}, ["bin-1"])
                value = "ok"
            except StateConflict:
                value = "conflict"
            with lock:
                results.append(value)

        t1 = threading.Thread(target=worker, args=("c.deliver.1", "out-1"))
        t2 = threading.Thread(target=worker, args=("c.deliver.2", "out-2"))
        t1.start(); t2.start(); t1.join(); t2.join()
        self.assertCountEqual(results, ["ok", "conflict"])
        snap = self.desk.route_snapshot("route:2026-09-21:route-one")
        self.assertEqual(len(snap["stops"][0]["delivery_containers"]), 1)

    def test_competing_exception_resolutions_cannot_double_apply(self):
        stop = self._route()["stops"][0]["stop_id"]
        self.desk.pickup("e.pickup", stop, {"sheet": 3}, ["bin-1"])
        exc = self.desk.process("e.process", stop, {"sheet": 2}, {"sheet": 0}).value["open_exception_ids"][0]
        self.desk.resolve_exception("e.resolve.1", exc, "COUNT_ACCEPTED", "First terminal decision")
        with self.assertRaises(StateConflict):
            self.desk.resolve_exception("e.resolve.2", exc, "OTHER", "Second terminal decision")

    def test_invoice_second_terminal_action_rejected(self):
        stop = self._route()["stops"][0]["stop_id"]
        self._good_stop(stop, "i")
        self.desk.draft_invoice("i.invoice.1", stop)
        with self.assertRaises(StateConflict):
            self.desk.draft_invoice("i.invoice.2", stop)

    def test_max_bound_identifiers_survive_full_lifecycle(self):
        customer_id = "c" * 255
        site_id = "s" * 255
        route_code = "r" * 255
        item_code = "i" * 255
        self.desk.add_customer("max.customer", customer_id, "Max Customer")
        self.desk.add_site("max.site", site_id, customer_id, "Max Site")
        self.desk.add_agreement("max.agreement", "g" * 255, site_id, item_code, 321, "2026-01-01")
        self.desk.add_service_plan("max.plan", "p" * 255, site_id, route_code, 0, 30, "2026-01-01")
        route = self.desk.create_daily_route("max.route", "2026-09-21", route_code).value
        stop_id = route["stops"][0]["stop_id"]
        self.assertLessEqual(len(route["route_id"]), 255)
        self.assertLessEqual(len(stop_id), 255)
        self.assertEqual(self.desk.route_snapshot(route["route_id"])["stops"][0]["stop_id"], stop_id)
        self.desk.pickup("max.pickup", stop_id, {item_code: 3}, ["max-bin-in"])
        processed = self.desk.process("max.process", stop_id, {item_code: 2}, {item_code: 1}).value
        self.assertEqual(len(processed["open_exception_ids"]), 1)
        exception_id = processed["open_exception_ids"][0]
        self.assertLessEqual(len(exception_id), 255)
        self.desk.resolve_exception("max.resolve", exception_id, "DAMAGE_ACCEPTED", "Owner accepted recorded damage")
        self.desk.deliver("max.deliver", stop_id, {item_code: 2}, ["max-bin-in"])
        invoice = self.desk.draft_invoice("max.invoice", stop_id).value
        self.assertLessEqual(len(invoice["invoice_id"]), 255)
        self.assertEqual(invoice["total_cents"], 642)

    def test_near_limit_stop_exception_id_remains_resolvable(self):
        route_code = "r" * 110
        site_id = "s" * 118
        item_code = "linen"
        self.desk.add_customer("near.customer", "near-customer", "Near Bound Customer")
        self.desk.add_site("near.site", site_id, "near-customer", "Near Bound Site")
        self.desk.add_agreement("near.agreement", "near-agreement", site_id, item_code, 200, "2026-01-01")
        self.desk.add_service_plan("near.plan", "near-plan", site_id, route_code, 0, 40, "2026-01-01")
        route = self.desk.create_daily_route("near.route", "2026-09-21", route_code).value
        stop_id = route["stops"][0]["stop_id"]
        self.assertGreater(len(stop_id), 240)
        self.assertLessEqual(len(stop_id), 255)
        self.desk.pickup("near.pickup", stop_id, {item_code: 5}, ["near-in"])
        processed = self.desk.process("near.process", stop_id, {item_code: 4}, {item_code: 1}).value
        exception_id = processed["open_exception_ids"][0]
        self.assertLessEqual(len(exception_id), 255)
        self.desk.resolve_exception("near.resolve", exception_id, "DAMAGE_ACCEPTED", "Near-bound exception resolved")
        self.desk.deliver("near.deliver", stop_id, {item_code: 4}, ["near-in"])
        invoice = self.desk.draft_invoice("near.invoice", stop_id).value
        self.assertEqual(invoice["total_cents"], 800)

    def test_custody_discontinuity_blocks_until_explicit_resolution_and_survives_restart(self):
        stop = self._route()["stops"][0]["stop_id"]
        self.desk.pickup("custody.pickup", stop, {"sheet": 10}, ["PICKUP-001"])
        self.desk.process("custody.process", stop, {"sheet": 10}, {"sheet": 0})
        delivered = self.desk.deliver(
            "custody.deliver", stop, {"sheet": 10}, ["DELIVERY-999"]
        )
        self.assertFalse(delivered.replayed)
        self.assertEqual(len(delivered.value["open_exception_ids"]), 2)
        replay = self.desk.deliver(
            "custody.deliver", stop, {"sheet": 10}, ["DELIVERY-999"]
        )
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.value["open_exception_ids"], delivered.value["open_exception_ids"])
        with self.assertRaises(IdempotencyConflict):
            self.desk.deliver("custody.deliver", stop, {"sheet": 10}, ["PICKUP-001"])

        reopened = LaundryDesk(self.db)
        snap = reopened.route_snapshot("route:2026-09-21:route-one")
        open_exceptions = [e for e in snap["stops"][0]["exceptions"] if e["status"] == "OPEN"]
        self.assertEqual(
            sorted(e["kind"] for e in open_exceptions),
            ["CUSTODY_MISSING", "CUSTODY_UNEXPECTED"],
        )
        with self.assertRaises(InvoiceBlocked):
            reopened.draft_invoice("custody.invoice.blocked", stop)
        for idx, exception_id in enumerate(delivered.value["open_exception_ids"], 1):
            reopened.resolve_exception(
                f"custody.resolve.{idx}",
                exception_id,
                "OWNER_REPACK_ACCEPTED",
                "Owner explicitly reconciled the container transfer",
            )
        invoice = reopened.draft_invoice("custody.invoice", stop).value
        self.assertEqual(invoice["state"], "DRAFT")
        self.assertEqual(invoice["total_cents"], 1250)

    def test_customer_csv_formula_neutralization_is_projection_only(self):
        import csv
        import io

        for idx, sigil in enumerate(("=", "+", "-", "@"), 1):
            customer_id = f"formula-customer-{idx}"
            site_id = f"formula-site-{idx}"
            customer_name = f"{sigil}1+1"
            site_name = f"{sigil}SUM(A1:A2)"
            self.desk.add_customer(f"formula.customer.{idx}", customer_id, customer_name)
            self.desk.add_site(f"formula.site.{idx}", site_id, customer_id, site_name)
            self.desk.add_agreement(
                f"formula.agreement.{idx}",
                f"formula-agreement-{idx}",
                site_id,
                "sheet",
                100,
                "2026-01-01",
            )
            before = self.desk.customer_snapshot(customer_id)
            exports = self.desk.render_customer_exports(customer_id)
            after = self.desk.customer_snapshot(customer_id)
            self.assertEqual(before, after)
            self.assertEqual(before["name"], customer_name)
            self.assertEqual(before["sites"][0]["name"], site_name)
            rows = list(csv.DictReader(io.StringIO(exports["csv"])))
            self.assertEqual(rows[0]["customer_name"], "'" + customer_name)
            self.assertEqual(rows[0]["site_name"], "'" + site_name)
            self.assertIn(customer_name, exports["json"])

    def test_customer_markdown_free_text_is_literal_and_deterministic(self):
        customer_name = "Pipe | `tick` *bold* [link] #heading"
        site_name = "Site | `code` ![image]"
        self.desk.add_customer("md.customer", "md-customer", customer_name)
        self.desk.add_site("md.site", "md-site", "md-customer", site_name)
        self.desk.add_agreement(
            "md.agreement", "md-agreement", "md-site", "sheet", 100, "2026-01-01"
        )
        first = self.desk.render_customer_exports("md-customer")
        second = self.desk.render_customer_exports("md-customer")
        self.assertEqual(first, second)
        md = first["markdown"]
        self.assertNotIn("Pipe | `tick`", md)
        self.assertNotIn("Site | `code`", md)
        self.assertIn("Pipe &#124; &#96;tick&#96; &#42;bold&#42; &#91;link&#93; &#35;heading", md)
        self.assertIn("Site &#124; &#96;code&#96; &#33;&#91;image&#93;", md)
        snapshot = self.desk.customer_snapshot("md-customer")
        self.assertEqual(snapshot["name"], customer_name)
        self.assertEqual(snapshot["sites"][0]["name"], site_name)

    def test_cli_export_is_create_exclusive(self):
        stop = self._route()["stops"][0]["stop_id"]
        self._good_stop(stop, "x")
        self.desk.draft_invoice("x.invoice", stop)
        out = Path(self.tmp.name) / "exports"
        cmd = [sys.executable, str(Path(__file__).with_name("cli.py")), self.db, "export-route", "route:2026-09-21:route-one", str(out)]
        first = subprocess.run(cmd, cwd=Path(__file__).parent, text=True, capture_output=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        second = subprocess.run(cmd, cwd=Path(__file__).parent, text=True, capture_output=True)
        self.assertNotEqual(second.returncode, 0)

    def test_demo_runs_and_exercises_block_then_resolution(self):
        cmd = [sys.executable, str(Path(__file__).with_name("demo.py"))]
        run = subprocess.run(cmd, cwd=Path(__file__).parent, text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        payload = json.loads(run.stdout)
        self.assertTrue(payload["invoice_blocked_before_resolution"])
        self.assertEqual(payload["integrity"]["integrity"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
