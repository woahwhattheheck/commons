#!/usr/bin/env python3
import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from desk import (
    BillingBlocked,
    OperationConflict,
    StateConflict,
    ValidationError,
    WasteRouteDesk,
)


MANIFEST = {
    "customers": [
        {
            "id": "ACME",
            "name": "Acme Coffee Group",
            "currency": "USD",
            "sites": [
                {
                    "id": "ACME-DOWNTOWN",
                    "name": "Downtown Cafe",
                    "containers": [
                        {
                            "id": "ACME-DOWNTOWN-8YD",
                            "label": "Rear 8yd",
                            "container_type": "front-load 8yd",
                            "plans": [
                                {
                                    "id": "PLAN-ACME-DOWNTOWN",
                                    "weekday": 0,
                                    "service_code": "RECURRENT_PICKUP",
                                    "price_minor": 12900,
                                }
                            ],
                        }
                    ],
                },
                {
                    "id": "ACME-MARKET",
                    "name": "Market Cafe",
                    "containers": [
                        {
                            "id": "ACME-MARKET-4YD",
                            "label": "Dock 4yd",
                            "container_type": "front-load 4yd",
                            "plans": [
                                {
                                    "id": "PLAN-ACME-MARKET",
                                    "weekday": 0,
                                    "service_code": "RECURRENT_PICKUP",
                                    "price_minor": 9900,
                                }
                            ],
                        }
                    ],
                },
            ],
        },
        {
            "id": "BETA",
            "name": "Beta Office Partners",
            "currency": "USD",
            "sites": [
                {
                    "id": "BETA-HQ",
                    "name": "Beta HQ",
                    "containers": [
                        {
                            "id": "BETA-HQ-6YD",
                            "label": "East lot 6yd",
                            "container_type": "front-load 6yd",
                            "plans": [
                                {
                                    "id": "PLAN-BETA-HQ",
                                    "weekday": 0,
                                    "service_code": "RECURRENT_PICKUP",
                                    "price_minor": 14900,
                                }
                            ],
                        }
                    ],
                }
            ],
        },
    ]
}


class WasteRouteDeskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "desk.sqlite3")
        self.desk = WasteRouteDesk(self.db)
        self.desk.import_manifest(MANIFEST, "manifest-v1")

    def tearDown(self):
        self.desk.close()
        self.tmp.cleanup()

    def _monday_route(self, day="2026-09-14", op="route-1"):
        return self.desk.generate_route(day, op)

    def test_manifest_route_order_and_exports_are_deterministic(self):
        first = self.desk.import_manifest(MANIFEST, "manifest-v1")
        self.assertEqual(first["counts"], {"customers": 2, "sites": 3, "containers": 3, "plans": 3})
        route = self._monday_route()
        self.assertEqual(route["stop_count"], 3)
        self.assertEqual(
            [s["plan_id"] for s in route["stops"]],
            ["PLAN-ACME-DOWNTOWN", "PLAN-ACME-MARKET", "PLAN-BETA-HQ"],
        )
        snap = self.desk.route_snapshot("2026-09-14")
        self.assertEqual(snap["external_provider_calls"], 0)
        self.assertFalse(snap["autonomous_dispatch"])
        csv_a = self.desk.route_csv("2026-09-14")
        csv_b = self.desk.route_csv("2026-09-14")
        self.assertEqual(csv_a, csv_b)
        self.assertIn("PLAN-BETA-HQ", csv_a)
        md = self.desk.route_markdown("2026-09-14")
        self.assertIn("| 1 | Acme Coffee Group | Downtown Cafe | Rear 8yd |", md)

    def test_distinct_manifest_operation_does_not_reinitialize_workspace(self):
        with self.assertRaises(StateConflict):
            self.desk.import_manifest(MANIFEST, "manifest-second-key")

    def test_operation_key_exact_retry_and_changed_input_conflict(self):
        route = self._monday_route()
        stop = route["stops"][0]["id"]
        result = self.desk.record_stop(stop, "SERVICED", "outcome-1")
        replay = self.desk.record_stop(stop, "SERVICED", "outcome-1")
        self.assertEqual(result, replay)
        with self.assertRaises(OperationConflict):
            self.desk.record_stop(stop, "SKIPPED", "outcome-1", exception_code="BLOCKED_ACCESS")

    def test_unresolved_or_pending_service_blocks_invoice(self):
        route = self._monday_route()
        acme_stops = [s for s in route["stops"] if s["customer_id"] == "ACME"]
        self.desk.record_stop(acme_stops[0]["id"], "SERVICED", "acme-service")
        self.desk.record_stop(
            acme_stops[1]["id"], "SKIPPED", "acme-skip", exception_code="BLOCKED_ACCESS"
        )
        with self.assertRaises(BillingBlocked):
            self.desk.draft_invoice("ACME", "2026-09-14", "2026-09-14", "inv-acme")
        self.desk.resolve_exception(
            acme_stops[1]["id"], "NO_SERVICE_NO_CHARGE", "acme-resolve"
        )
        invoice = self.desk.draft_invoice(
            "ACME", "2026-09-14", "2026-09-14", "inv-acme"
        )
        self.assertEqual(invoice["total_minor"], 12900)
        self.assertFalse(invoice["payment_mutation"])
        self.assertEqual(len(invoice["lines"]), 2)
        self.assertEqual(
            {line["status"] for line in invoice["lines"]},
            {"SERVICE_CONFIRMED", "RESOLVED_NO_CHARGE"},
        )

    def test_customer_invoice_isolation_and_billable_makeup(self):
        route = self._monday_route()
        acme = [s for s in route["stops"] if s["customer_id"] == "ACME"]
        beta = [s for s in route["stops"] if s["customer_id"] == "BETA"][0]
        self.desk.record_stop(acme[0]["id"], "SERVICED", "a1")
        self.desk.record_stop(acme[1]["id"], "SKIPPED", "a2", exception_code="LOCKED_GATE")
        self.desk.resolve_exception(acme[1]["id"], "MAKEUP_COMPLETED_BILLABLE", "a3")
        self.desk.record_stop(beta["id"], "SERVICED", "b1")
        beta_invoice = self.desk.draft_invoice(
            "BETA", "2026-09-14", "2026-09-14", "binv"
        )
        self.assertEqual(beta_invoice["total_minor"], 14900)
        self.assertEqual({line["customer_id"] for line in beta_invoice["lines"]}, {"BETA"})
        acme_invoice = self.desk.draft_invoice(
            "ACME", "2026-09-14", "2026-09-14", "ainv"
        )
        self.assertEqual(acme_invoice["total_minor"], 22800)

    def test_restart_preserves_state_and_event_history(self):
        route = self._monday_route()
        self.desk.record_stop(route["stops"][0]["id"], "SERVICED", "persist-outcome")
        before = self.desk.event_log()
        self.desk.close()
        self.desk = WasteRouteDesk(self.db)
        snap = self.desk.route_snapshot("2026-09-14")
        self.assertEqual(snap["stops"][0]["status"], "SERVICE_CONFIRMED")
        after = self.desk.event_log()
        self.assertEqual(before, after)

    def test_events_are_sqlite_immutable(self):
        self._monday_route()
        with self.assertRaises(sqlite3.DatabaseError):
            self.desk.conn.execute("UPDATE events SET event_type='FORGED' WHERE id=1")
        with self.assertRaises(sqlite3.DatabaseError):
            self.desk.conn.execute("DELETE FROM events WHERE id=1")

    def test_concurrent_terminal_race_has_one_winner(self):
        route = self._monday_route("2026-09-21", "route-race")
        stop_id = route["stops"][0]["id"]
        barrier = threading.Barrier(2)

        def worker(kind):
            with WasteRouteDesk(self.db) as desk:
                barrier.wait()
                try:
                    if kind == "service":
                        result = desk.record_stop(stop_id, "SERVICED", "race-service")
                    else:
                        result = desk.record_stop(
                            stop_id,
                            "SKIPPED",
                            "race-skip",
                            exception_code="BLOCKED_ACCESS",
                        )
                    return ("ok", result["status"])
                except StateConflict as exc:
                    return ("conflict", str(exc))

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, ["service", "skip"]))
        self.assertEqual(sorted(r[0] for r in results), ["conflict", "ok"])
        final = self.desk.route_snapshot("2026-09-21")
        self.assertIn(
            final["stops"][0]["status"],
            {"SERVICE_CONFIRMED", "EXCEPTION_OPEN"},
        )

    def test_invoice_blocks_if_a_later_due_route_was_never_generated(self):
        route = self._monday_route()
        acme = [s for s in route["stops"] if s["customer_id"] == "ACME"]
        self.desk.record_stop(acme[0]["id"], "SERVICED", "week1-a")
        self.desk.record_stop(acme[1]["id"], "SERVICED", "week1-b")
        with self.assertRaises(BillingBlocked):
            self.desk.draft_invoice("ACME", "2026-09-14", "2026-09-21", "two-week-too-early")

        route2 = self.desk.generate_route("2026-09-21", "week2-route")
        acme2 = [s for s in route2["stops"] if s["customer_id"] == "ACME"]
        self.desk.record_stop(acme2[0]["id"], "SERVICED", "week2-a")
        self.desk.record_stop(acme2[1]["id"], "SERVICED", "week2-b")
        invoice = self.desk.draft_invoice(
            "ACME", "2026-09-14", "2026-09-21", "two-week-ready"
        )
        self.assertEqual(invoice["total_minor"], 45600)
        self.assertEqual(len(invoice["lines"]), 4)

    def test_invoice_stays_blocked_if_other_stop_is_pending(self):
        route = self._monday_route()
        first_acme = [s for s in route["stops"] if s["customer_id"] == "ACME"][0]
        self.desk.record_stop(first_acme["id"], "SERVICED", "only-one")
        with self.assertRaises(BillingBlocked):
            self.desk.draft_invoice("ACME", "2026-09-14", "2026-09-14", "too-early")

    def test_manifest_rejects_float_money_and_boolean_weekday(self):
        bad = json.loads(json.dumps(MANIFEST))
        bad["customers"][0]["sites"][0]["containers"][0]["plans"][0]["price_minor"] = 12.5
        with self.assertRaises(ValidationError):
            WasteRouteDesk._normalize_manifest(bad)
        bad = json.loads(json.dumps(MANIFEST))
        bad["customers"][0]["sites"][0]["containers"][0]["plans"][0]["weekday"] = True
        with self.assertRaises(ValidationError):
            WasteRouteDesk._normalize_manifest(bad)

    def test_invalid_resolution_or_duplicate_route_is_rejected(self):
        self._monday_route()
        with self.assertRaises(StateConflict):
            self.desk.generate_route("2026-09-14", "route-duplicate")
        with self.assertRaises(ValidationError):
            self.desk.resolve_exception("whatever", "FORGE_CHARGE", "bad-resolution")


if __name__ == "__main__":
    unittest.main(verbosity=2)
