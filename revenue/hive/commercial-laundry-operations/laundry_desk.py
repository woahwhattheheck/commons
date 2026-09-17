from __future__ import annotations

"""Public hardened facade for the commercial laundry operations desk.

The reviewed facade implementation is loaded privately.  Public semantic
authority does not depend on its rebindable module AUTHORITY name: invoice
creation below uses source-literal hard-false authority, while inherited
snapshot/integrity projections are sealed by ``laundry_desk_core``.
"""

import importlib.machinery as _machinery
import importlib.util as _importlib_util
import sys as _sys
from pathlib import Path as _LoaderPath
from types import MappingProxyType

_PRIVATE_FACADE_NAME = "_commercial_laundry_facade_private"
_PRIVATE_FACADE_PATH = _LoaderPath(__file__).with_name("_laundry_desk_facade_impl.py.disabled")
_loader = _machinery.SourceFileLoader(_PRIVATE_FACADE_NAME, str(_PRIVATE_FACADE_PATH))
_spec = _importlib_util.spec_from_loader(_PRIVATE_FACADE_NAME, _loader)
if _spec is None:
    raise ImportError("unable to load retained commercial-laundry facade")
_facade = _importlib_util.module_from_spec(_spec)
_sys.modules[_PRIVATE_FACADE_NAME] = _facade
try:
    _loader.exec_module(_facade)
finally:
    _sys.modules.pop(_PRIVATE_FACADE_NAME, None)

AUTHORITY = MappingProxyType(
    {
        "customer_messaging": False,
        "provider_navigation": False,
        "accounting_mutation": False,
        "payment_mutation": False,
        "deployment": False,
        "revenue_assertion": False,
        "sanitation_certification": False,
        "quality_inference": False,
    }
)
_facade.AUTHORITY = AUTHORITY

for _name, _value in vars(_facade).items():
    if _name not in {"LaundryDesk", "AUTHORITY"} and not _name.startswith("__"):
        globals()[_name] = _value
LaundryDesk = _facade.LaundryDesk


def _make_authority_safe_draft(core_module, generated_id):
    def draft_invoice(self, operation_key: str, stop_id: str) -> OperationResult:
        stop_id = core_module._ident(stop_id, "stop_id")
        invoice_id = generated_id("draft", stop_id)
        payload = {"stop_id": stop_id}

        def mutate(conn: core_module.sqlite3.Connection) -> dict[str, Any]:
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
                cents = core_module._money(auth[0]["unit_price_cents"], "stored unit_price_cents")
                line_total = core_module._money(qty * cents, "line total")
                total = core_module._money(total + line_total, "invoice total")
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
                "authority": {
                    "customer_messaging": False,
                    "provider_navigation": False,
                    "accounting_mutation": False,
                    "payment_mutation": False,
                    "deployment": False,
                    "revenue_assertion": False,
                    "sanitation_certification": False,
                    "quality_inference": False,
                },
            }
            conn.execute(
                "INSERT INTO invoices(invoice_id,stop_id,state,total_cents,payload_json) VALUES (?,?,'DRAFT',?,?)",
                (invoice_id, stop_id, total, core_module._canonical_json(invoice)),
            )
            changed = conn.execute(
                "UPDATE stops SET state='INVOICE_DRAFTED' WHERE stop_id=? AND state='DELIVERED'", (stop_id,)
            ).rowcount
            if changed != 1:
                raise StateConflict("invoice drafting lost a concurrent terminal race")
            return invoice

        return self._operation(operation_key, "INVOICE_DRAFTED", "invoice", invoice_id, payload, mutate)

    return draft_invoice


# Replace the retained method with a source-literal authority implementation.
# Mutating/rebinding any module ``AUTHORITY`` name or this method's globals does
# not participate in invoice authority generation.
LaundryDesk.draft_invoice = _make_authority_safe_draft(_core, _generated_id)

# Do not leave the privately loaded facade module or factory as ordinary raw
# semantic handles.  The class methods retain only the closures they need.
del _facade, _loader, _spec, _name, _value, _make_authority_safe_draft
