from __future__ import annotations

"""Bounded-identity facade for the commercial laundry operations desk.

The durable SQLite/state engine lives in :mod:`laundry_desk_core`.  This facade
preserves its public API while making every derived identity satisfy the same
255-character contract accepted for owner-authored identifiers.  Short derived
IDs remain readable; over-bound IDs are deterministically bound to their full
source tuple with SHA-256.
"""

import csv
import hashlib
import io
from typing import Any

import laundry_desk_core as _core

SCHEMA_VERSION = _core.SCHEMA_VERSION
ID_RE = _core.ID_RE
AUTHORITY = _core.AUTHORITY
MAX_ID_LENGTH = 255

LaundryDeskError = _core.LaundryDeskError
ValidationError = _core.ValidationError
IdempotencyConflict = _core.IdempotencyConflict
StateConflict = _core.StateConflict
InvoiceBlocked = _core.InvoiceBlocked
OperationResult = _core.OperationResult


def _generated_id(namespace: str, *parts: object) -> str:
    namespace = _core._ident(namespace, "generated ID namespace")
    text_parts = [str(part) for part in parts]
    candidate = f"{namespace}:" + ":".join(text_parts)
    if len(candidate) <= MAX_ID_LENGTH and ID_RE.fullmatch(candidate):
        return candidate
    digest = hashlib.sha256(
        _core._canonical_json({"namespace": namespace, "parts": text_parts}).encode("utf-8")
    ).hexdigest()
    bounded = f"{namespace}:sha256:{digest}"
    if len(bounded) > MAX_ID_LENGTH or not ID_RE.fullmatch(bounded):
        raise LaundryDeskError("generated identifier contract violated")
    return bounded


def _csv_safe(value: str) -> str:
    """Neutralize spreadsheet formulas in human-authored text projections only."""
    if not isinstance(value, str):
        raise ValidationError("CSV projection text must be text")
    return "'" + value if value.startswith(("=", "+", "-", "@")) else value


def _md_literal(value: str) -> str:
    """Render human-authored text literally without Markdown structural meaning."""
    if not isinstance(value, str):
        raise ValidationError("Markdown projection text must be text")
    entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "|": "&#124;",
        "`": "&#96;",
        "\\": "&#92;",
        "*": "&#42;",
        "_": "&#95;",
        "[": "&#91;",
        "]": "&#93;",
        "#": "&#35;",
        "!": "&#33;",
    }
    return "".join(entities.get(ch, ch) for ch in value)


class LaundryDesk(_core.LaundryDesk):
    """Core desk with bounded deterministic route/stop/exception/invoice IDs."""

    def create_daily_route(self, operation_key: str, service_date: str, route_code: str) -> OperationResult:
        service_date = _core._iso_date(service_date, "service_date")
        route_code = _core._ident(route_code, "route_code")
        route_id = _generated_id("route", service_date, route_code)
        weekday = _core.date.fromisoformat(service_date).weekday()
        payload = {"service_date": service_date, "route_code": route_code}

        def mutate(conn: _core.sqlite3.Connection) -> dict[str, Any]:
            if conn.execute("SELECT 1 FROM routes WHERE route_id=?", (route_id,)).fetchone():
                raise StateConflict("route already exists")
            plans = conn.execute(
                "SELECT plan_id,site_id,stop_sequence FROM service_plans "
                "WHERE route_code=? AND weekday=? AND active_from<=? "
                "AND (active_to IS NULL OR active_to>=?) "
                "ORDER BY stop_sequence, site_id, plan_id",
                (route_code, weekday, service_date, service_date),
            ).fetchall()
            if not plans:
                raise ValidationError("no active service plans for route/date")
            conn.execute(
                "INSERT INTO routes(route_id,service_date,route_code,state) VALUES (?,?,?,'MANIFESTED')",
                (route_id, service_date, route_code),
            )
            stops: list[dict[str, Any]] = []
            for row in plans:
                stop_id = _generated_id(
                    "stop", service_date, route_code, f"{row['stop_sequence']:04d}", row["site_id"]
                )
                conn.execute(
                    "INSERT INTO stops(stop_id,route_id,site_id,stop_sequence,state) VALUES (?,?,?,?,'MANIFESTED')",
                    (stop_id, route_id, row["site_id"], row["stop_sequence"]),
                )
                stops.append({"stop_id": stop_id, "site_id": row["site_id"], "sequence": row["stop_sequence"]})
            return {"route_id": route_id, "service_date": service_date, "route_code": route_code, "stops": stops}

        return self._operation(operation_key, "ROUTE_MANIFESTED", "route", route_id, payload, mutate)

    def _insert_exception(
        self,
        conn: _core.sqlite3.Connection,
        stop_id: str,
        kind: str,
        item_code: str,
        expected: int,
        actual: int,
    ) -> str:
        ordinal = conn.execute("SELECT COUNT(*) FROM exceptions WHERE stop_id=?", (stop_id,)).fetchone()[0] + 1
        exception_id = _generated_id("exc", stop_id, f"{ordinal:04d}")
        conn.execute(
            "INSERT INTO exceptions(exception_id,stop_id,kind,item_code,expected_qty,actual_qty,status) "
            "VALUES (?,?,?,?,?,?,'OPEN')",
            (exception_id, stop_id, kind, item_code, expected, actual),
        )
        return exception_id

    def draft_invoice(self, operation_key: str, stop_id: str) -> OperationResult:
        stop_id = _core._ident(stop_id, "stop_id")
        invoice_id = _generated_id("draft", stop_id)
        payload = {"stop_id": stop_id}

        def mutate(conn: _core.sqlite3.Connection) -> dict[str, Any]:
            row = conn.execute(
                "SELECT s.state,s.site_id,r.service_date,r.route_id FROM stops s "
                "JOIN routes r ON r.route_id=s.route_id WHERE s.stop_id=?",
                (stop_id,),
            ).fetchone()
            if not row:
                raise ValidationError("unknown stop")
            if row["state"] != "DELIVERED":
                raise StateConflict("invoice draft requires DELIVERED stop")
            if conn.execute("SELECT 1 FROM invoices WHERE stop_id=?", (stop_id,)).fetchone():
                raise StateConflict("invoice draft already exists")
            open_ex = conn.execute(
                "SELECT COUNT(*) FROM exceptions WHERE stop_id=? AND status='OPEN'", (stop_id,)
            ).fetchone()[0]
            if open_ex:
                raise InvoiceBlocked(f"{open_ex} unresolved custody/count exceptions block invoice readiness")
            delivered = self._phase_counts(conn, stop_id, "DELIVERED")
            lines: list[dict[str, Any]] = []
            total = 0
            for item, qty in sorted(delivered.items()):
                auth = conn.execute(
                    "SELECT agreement_id,unit_price_cents FROM agreements WHERE site_id=? AND item_code=? "
                    "AND active_from<=? AND (active_to IS NULL OR active_to>=?) "
                    "ORDER BY active_from DESC,agreement_id",
                    (row["site_id"], item, row["service_date"], row["service_date"]),
                ).fetchall()
                if len(auth) != 1:
                    raise InvoiceBlocked(f"expected exactly one active price authority for {item}; found {len(auth)}")
                cents = _core._money(auth[0]["unit_price_cents"], "stored unit_price_cents")
                line_total = _core._money(qty * cents, "line total")
                total = _core._money(total + line_total, "invoice total")
                lines.append(
                    {
                        "item_code": item,
                        "quantity": qty,
                        "unit_price_cents": cents,
                        "line_total_cents": line_total,
                        "agreement_id": auth[0]["agreement_id"],
                    }
                )
            invoice = {
                "invoice_id": invoice_id,
                "state": "DRAFT",
                "stop_id": stop_id,
                "site_id": row["site_id"],
                "route_id": row["route_id"],
                "service_date": row["service_date"],
                "currency": "USD",
                "lines": lines,
                "total_cents": total,
                "authority": AUTHORITY.copy(),
            }
            conn.execute(
                "INSERT INTO invoices(invoice_id,stop_id,state,total_cents,payload_json) VALUES (?,?,'DRAFT',?,?)",
                (invoice_id, stop_id, total, _core._canonical_json(invoice)),
            )
            changed = conn.execute(
                "UPDATE stops SET state='INVOICE_DRAFTED' WHERE stop_id=? AND state='DELIVERED'", (stop_id,)
            ).rowcount
            if changed != 1:
                raise StateConflict("invoice drafting lost a concurrent terminal race")
            return invoice

        return self._operation(operation_key, "INVOICE_DRAFTED", "invoice", invoice_id, payload, mutate)


    def deliver(
        self,
        operation_key: str,
        stop_id: str,
        delivered_counts: _core.Mapping[str, int],
        container_ids: _core.Iterable[str],
    ) -> OperationResult:
        """Record delivery and fail closed on unresolved custody discontinuity.

        Pickup containers are the custody reference. If delivery uses a different
        set, deterministic CUSTODY_MISSING/CUSTODY_UNEXPECTED exceptions are
        opened. Legitimate repack/transfer can proceed only after an operator
        explicitly resolves those exceptions; invoice drafting remains blocked
        while any exception is open.
        """
        stop_id = _core._ident(stop_id, "stop_id")
        delivered = _core._counts(delivered_counts, "delivered counts")
        containers = _core._containers(container_ids, "delivery containers")
        payload = {"stop_id": stop_id, "delivered_counts": delivered, "container_ids": containers}

        def mutate(conn: _core.sqlite3.Connection) -> dict[str, Any]:
            row = conn.execute("SELECT route_id,state FROM stops WHERE stop_id=?", (stop_id,)).fetchone()
            if not row:
                raise ValidationError("unknown stop")
            if row["state"] != "PROCESSED":
                raise StateConflict("delivery requires PROCESSED stop")
            processed = self._phase_counts(conn, stop_id, "PROCESSED")
            item_codes = sorted(set(processed) | set(delivered))
            created: list[str] = []
            for item in item_codes:
                expected = processed.get(item, 0)
                actual = delivered.get(item, 0)
                conn.execute(
                    "INSERT INTO linen_counts(stop_id,phase,item_code,qty) VALUES (?,?,?,?)",
                    (stop_id, "DELIVERED", item, actual),
                )
                if actual != expected:
                    created.append(
                        self._insert_exception(
                            conn, stop_id, "DELIVERY_COUNT_MISMATCH", item, expected, actual
                        )
                    )

            pickup_containers = {
                r[0]
                for r in conn.execute(
                    "SELECT container_id FROM container_custody "
                    "WHERE stop_id=? AND phase='PICKUP' ORDER BY container_id",
                    (stop_id,),
                )
            }
            delivery_containers = set(containers)
            for container_id in sorted(pickup_containers - delivery_containers):
                created.append(
                    self._insert_exception(
                        conn, stop_id, "CUSTODY_MISSING", container_id, 1, 0
                    )
                )
            for container_id in sorted(delivery_containers - pickup_containers):
                created.append(
                    self._insert_exception(
                        conn, stop_id, "CUSTODY_UNEXPECTED", container_id, 0, 1
                    )
                )
            for container_id in containers:
                conn.execute(
                    "INSERT INTO container_custody(stop_id,phase,container_id) VALUES (?,?,?)",
                    (stop_id, "DELIVERY", container_id),
                )
            conn.execute(
                "UPDATE stops SET state='DELIVERED' WHERE stop_id=? AND state='PROCESSED'",
                (stop_id,),
            )
            self._maybe_complete_route(conn, row["route_id"])
            return {
                "stop_id": stop_id,
                "state": "DELIVERED",
                "delivered_counts": delivered,
                "containers": containers,
                "open_exception_ids": created,
            }

        return self._operation(operation_key, "DELIVERY_RECORDED", "stop", stop_id, payload, mutate)

    def render_customer_exports(self, customer_id: str) -> dict[str, str]:
        """Render deterministic projections without mutating authoritative labels."""
        snap = self.customer_snapshot(customer_id)
        json_text = _core.json.dumps(snap, sort_keys=True, indent=2, ensure_ascii=False) + "\n"

        csv_buf = io.StringIO(newline="")
        writer = csv.writer(csv_buf, lineterminator="\n")
        writer.writerow(
            [
                "customer_id",
                "customer_name",
                "site_id",
                "site_name",
                "agreement_id",
                "item_code",
                "unit_price_cents",
                "active_from",
                "active_to",
            ]
        )
        for site in snap["sites"]:
            for agreement in site["agreements"]:
                writer.writerow(
                    [
                        snap["customer_id"],
                        _csv_safe(snap["name"]),
                        site["site_id"],
                        _csv_safe(site["name"]),
                        agreement["agreement_id"],
                        agreement["item_code"],
                        agreement["unit_price_cents"],
                        agreement["active_from"],
                        agreement["active_to"] or "",
                    ]
                )

        md = [
            f"# Customer {snap['customer_id']}",
            "",
            f"Name: {_md_literal(snap['name'])}",
            "",
            "| Site | Site name | Item | Unit price (cents) | Effective |",
            "|---|---|---|---:|---|",
        ]
        for site in snap["sites"]:
            for agreement in site["agreements"]:
                end = agreement["active_to"] or "open"
                md.append(
                    f"| {site['site_id']} | {_md_literal(site['name'])} | "
                    f"{agreement['item_code']} | {agreement['unit_price_cents']} | "
                    f"{agreement['active_from']}..{end} |"
                )
        md += [
            "",
            "Authority flags: all customer/provider/payment/deployment/revenue authority is `false`.",
            "",
        ]
        return {"json": json_text, "csv": csv_buf.getvalue(), "markdown": "\n".join(md)}
