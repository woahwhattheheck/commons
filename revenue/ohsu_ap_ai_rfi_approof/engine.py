"""APProof deterministic shadow classification and verification."""
from __future__ import annotations
import hashlib
from typing import Any, Iterable, Mapping, Sequence
from .common import (
    APProofError, AUTHORITY, PROJECTION_SCHEMA, SCHEMA, canonical_json_bytes, digest,
)
from .validate import semantic_packet

def _receipt_quantities(receipts: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = {}
    for rec in receipts:
        key = (rec["po_id"], rec["line_id"])
        out[key] = out.get(key, 0) + rec["quantity"]
        if out[key] > 10**9:
            raise APProofError("receipt quantity overflow")
    return out


def _approval_state(invoice_id: str, approvals: Sequence[Mapping[str, Any]]) -> str:
    rows = [a for a in approvals if a["invoice_id"] == invoice_id]
    if not rows:
        return "MISSING"
    statuses = {a["status"] for a in rows}
    if "REJECTED" in statuses:
        return "REJECTED"
    if statuses == {"APPROVED"}:
        return "APPROVED"
    return "PENDING"


def _match(inv: Mapping[str, Any], po: Mapping[str, Any] | None,
           received: Mapping[tuple[str, str], int]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if po is None:
        return out
    po_lines = {line["line_id"]: line for line in po["lines"]}
    for line in inv["lines"]:
        pline = po_lines.get(line["line_id"])
        if pline is None:
            out.append({"code": "PO_LINE_MISSING", "line_id": line["line_id"]})
            continue
        if pline["sku"] != line["sku"]:
            out.append({"code": "SKU_MISMATCH", "line_id": line["line_id"],
                        "invoice_sku": line["sku"], "po_sku": pline["sku"]})
        if pline["unit_price_cents"] != line["unit_price_cents"]:
            out.append({"code": "PRICE_MISMATCH", "line_id": line["line_id"],
                        "invoice_unit_price_cents": line["unit_price_cents"],
                        "po_unit_price_cents": pline["unit_price_cents"]})
        if pline["quantity"] < line["quantity"]:
            out.append({"code": "PO_QUANTITY_EXCEEDED", "line_id": line["line_id"],
                        "invoice_quantity": line["quantity"], "po_quantity": pline["quantity"]})
        got = received.get((po["po_id"], line["line_id"]), 0)
        if got < line["quantity"]:
            out.append({"code": "RECEIPT_QUANTITY_SHORT", "line_id": line["line_id"],
                        "invoice_quantity": line["quantity"], "received_quantity": got})
    return out


def _statement_findings(inv: Mapping[str, Any],
                        statements: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [s for s in statements
            if s["vendor_id"] == inv["vendor_id"] and s["currency"] == inv["currency"]]
    if not rows:
        return [{"code": "NO_VENDOR_STATEMENT"}]
    if not any(inv["invoice_number"] in s["invoice_numbers"] for s in rows):
        return [{"code": "INVOICE_NOT_ON_STATEMENT"}]
    return []


def _duplicates(invoices: Sequence[Mapping[str, Any]]) -> set[tuple[str, str, str, int]]:
    counts: dict[tuple[str, str, str, int], int] = {}
    for inv in invoices:
        key = (inv["vendor_id"], inv["invoice_number"], inv["currency"], inv["total_cents"])
        counts[key] = counts.get(key, 0) + 1
    return {key for key, count in counts.items() if count > 1}


def _audit(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    prev = "0" * 64
    rows = []
    for idx, event in enumerate(events):
        event_sha = digest(event)
        chain_sha = hashlib.sha256(f"{idx}:{prev}:{event_sha}".encode("ascii")).hexdigest()
        rows.append({"index": idx, "event_sha256": event_sha,
                     "previous_chain_sha256": prev, "chain_sha256": chain_sha})
        prev = chain_sha
    return rows


def compile_packet(packet: Any) -> dict[str, Any]:
    p = semantic_packet(packet)
    packet_sha = digest(p)
    invoices = p["invoices"]
    pos = {po["po_id"]: po for po in p["purchase_orders"]}
    received = _receipt_quantities(p["receipts"])
    duplicate_keys = _duplicates(invoices)
    results: list[dict[str, Any]] = []
    exception_counts: dict[str, int] = {}
    shadow_rows: list[dict[str, Any]] = []

    for inv in invoices:
        findings: list[dict[str, Any]] = []
        key = (inv["vendor_id"], inv["invoice_number"], inv["currency"], inv["total_cents"])
        if key in duplicate_keys:
            findings.append({"code": "DUPLICATE_ECONOMIC_INVOICE_HOLD"})
        if inv["po_id"] is None:
            po = None
            findings.append({"code": "NON_PO_CODING_REVIEW"})
        else:
            po = pos.get(inv["po_id"])
            if po is None:
                findings.append({"code": "PO_NOT_FOUND"})
            else:
                if po["vendor_id"] != inv["vendor_id"]:
                    findings.append({"code": "PO_VENDOR_MISMATCH"})
                if po["currency"] != inv["currency"]:
                    findings.append({"code": "PO_CURRENCY_MISMATCH"})
                findings.extend(_match(inv, po, received))

        approval = _approval_state(inv["invoice_id"], p["approvals"])
        if approval == "MISSING":
            findings.append({"code": "APPROVAL_MISSING"})
        elif approval == "PENDING":
            findings.append({"code": "APPROVAL_PENDING"})
        elif approval == "REJECTED":
            findings.append({"code": "APPROVAL_REJECTED"})
        findings.extend(_statement_findings(inv, p["supplier_statements"]))
        findings = sorted(findings, key=canonical_json_bytes)
        for finding in findings:
            code = finding["code"]
            exception_counts[code] = exception_counts.get(code, 0) + 1
        state = "READY_FOR_SHADOW_EXPORT" if not findings else "HOLD_OWNER_REVIEW"
        results.append({"invoice_id": inv["invoice_id"], "state": state,
                        "approval_state": approval, "findings": findings,
                        "source_sha256": inv["source_sha256"]})
        if state == "READY_FOR_SHADOW_EXPORT":
            shadow_rows.append({
                "invoice_id": inv["invoice_id"], "vendor_id": inv["vendor_id"],
                "invoice_number": inv["invoice_number"], "invoice_date": inv["invoice_date"],
                "currency": inv["currency"], "total_cents": inv["total_cents"],
                "po_id": inv["po_id"], "mode": "SHADOW_ONLY",
                "oracle_ebs_transaction_id": None, "posting_authorized": False,
            })

    known: dict[tuple[str, str], set[str]] = {}
    for inv in invoices:
        known.setdefault((inv["vendor_id"], inv["currency"]), set()).add(inv["invoice_number"])
    statement_exceptions = []
    for st in p["supplier_statements"]:
        allowed = known.get((st["vendor_id"], st["currency"]), set())
        for number in sorted(set(st["invoice_numbers"]) - allowed):
            statement_exceptions.append({
                "statement_id": st["statement_id"],
                "code": "STATEMENT_INVOICE_NOT_IN_PACKET",
                "invoice_number": number,
            })

    totals: dict[str, int] = {}
    for inv in invoices:
        totals[inv["currency"]] = totals.get(inv["currency"], 0) + inv["total_cents"]
    ready = sum(r["state"] == "READY_FOR_SHADOW_EXPORT" for r in results)
    total = len(results)
    metrics = {
        "invoice_count": total, "shadow_ready_count": ready,
        "owner_review_hold_count": total - ready,
        "shadow_ready_basis_points": 0 if total == 0 else ready * 10000 // total,
        "exception_counts": {k: exception_counts[k] for k in sorted(exception_counts)},
        "invoice_total_cents_by_currency": {k: totals[k] for k in sorted(totals)},
        "statement_exception_count": len(statement_exceptions),
    }
    events = ([{"kind": "INVOICE_RESULT", "payload": row} for row in results]
              + [{"kind": "STATEMENT_EXCEPTION", "payload": row}
                 for row in statement_exceptions]
              + [{"kind": "METRICS", "payload": metrics},
                 {"kind": "AUTHORITY", "payload": AUTHORITY}])
    base = {
        "schema": PROJECTION_SCHEMA, "packet_schema": SCHEMA, "as_of": p["as_of"],
        "packet_sha256": packet_sha, "invoice_results": results,
        "statement_exceptions": statement_exceptions, "oracle_shadow_rows": shadow_rows,
        "metrics": metrics, "audit_chain": _audit(events), "authority": dict(AUTHORITY),
    }
    return {**base, "projection_sha256": digest(base)}


def verify_projection(packet: Any, projection: Any) -> bool:
    if type(projection) is not dict:
        return False
    try:
        return canonical_json_bytes(compile_packet(packet)) == canonical_json_bytes(projection)
    except APProofError:
        return False
