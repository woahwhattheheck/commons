from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA = "tjlabs.ap-acceptance-fixture/v1"
EXACT_KEYS = {
    "schema", "case_id", "invoice_id", "po_required", "po_present", "vendor_match",
    "invoice_total_cents", "po_total_cents", "tolerance_cents", "duplicate",
    "approval_required", "approval_present", "statement_balance_cents", "ledger_balance_cents",
}

class AcceptanceError(ValueError):
    pass


def _b(v: Any, name: str) -> bool:
    if type(v) is not bool:
        raise AcceptanceError(f"{name}: bool required")
    return v


def _i(v: Any, name: str) -> int:
    if type(v) is not int or v < 0 or v > 10**12:
        raise AcceptanceError(f"{name}: nonnegative safe integer required")
    return v


def evaluate(case: Any) -> dict[str, Any]:
    if type(case) is not dict or set(case) != EXACT_KEYS:
        raise AcceptanceError("case: exact schema required")
    if case["schema"] != SCHEMA:
        raise AcceptanceError("schema: unsupported")
    for field in ("case_id", "invoice_id"):
        if type(case[field]) is not str or not case[field] or len(case[field]) > 80 or any(ord(c) < 33 for c in case[field]):
            raise AcceptanceError(f"{field}: safe nonempty string required")
    for field in ("po_required", "po_present", "vendor_match", "duplicate", "approval_required", "approval_present"):
        _b(case[field], field)
    for field in ("invoice_total_cents", "po_total_cents", "tolerance_cents", "statement_balance_cents", "ledger_balance_cents"):
        _i(case[field], field)

    variance = abs(case["invoice_total_cents"] - case["po_total_cents"])
    if case["duplicate"]:
        decision = "REJECT_DUPLICATE"
    elif case["po_required"] and not case["po_present"]:
        decision = "HOLD_MISSING_PO"
    elif not case["vendor_match"]:
        decision = "HOLD_VENDOR_MISMATCH"
    elif case["po_required"] and variance > case["tolerance_cents"]:
        decision = "HOLD_AMOUNT_VARIANCE"
    elif case["approval_required"] and not case["approval_present"]:
        decision = "HOLD_APPROVAL"
    elif case["statement_balance_cents"] != case["ledger_balance_cents"]:
        decision = "HOLD_RECONCILIATION"
    else:
        decision = "ACCEPT_STP"

    core = {
        "schema": "tjlabs.ap-acceptance-result/v1",
        "case_id": case["case_id"],
        "invoice_id": case["invoice_id"],
        "decision": decision,
        "variance_cents": variance,
        "oracle_write_authorized": False,
        "payment_authorized": False,
    }
    wire = (json.dumps(core, sort_keys=True, separators=(",", ":")) + "\n").encode()
    core["receipt_sha256"] = hashlib.sha256(wire).hexdigest()
    return core
