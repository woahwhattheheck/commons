#!/usr/bin/env python3
"""Load landed $199 diagnostic receipt.json by slug for transferable roles.

TENON claim tenon-r4-diagnostic-receipt-cli-20260905-01 (HINGE peer-assist).
Gates on tool `diagnostic_receipt`; reads checked-in receipt.json for
dealer|referral|plant (repair has no receipt twin — refuse). Does not remint
receipts, invent Stripe, or write CRM.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from roles import RoleError

_TOOL_NAME = "diagnostic_receipt"
_TOOL_ENTRY = "integrations/transferable_roles/diagnostic_receipt.py"

_ROOT = Path(__file__).resolve().parents[2]

SLUG_TO_RECEIPT_JSON = {
    "dealer": "revenue/dealer_service_lead_rescue/receipt.json",
    "referral": "revenue/referral_intake_completeness/receipt.json",
    "plant": "revenue/plant_downtime_handoff/receipt.json",
}

SLUG_TO_RECEIPT_MD = {
    "dealer": "revenue/dealer_service_lead_rescue/receipt.md",
    "referral": "revenue/referral_intake_completeness/receipt.md",
    "plant": "revenue/plant_downtime_handoff/receipt.md",
}


def require_diagnostic_receipt_tool(role: Mapping[str, Any]) -> dict[str, Any]:
    """Refuse unless the role tools this module's execute entry."""
    if not isinstance(role, Mapping):
        raise RoleError("role must be an object")
    for tool in role.get("tools") or []:
        if not isinstance(tool, Mapping):
            continue
        if tool.get("name") != _TOOL_NAME:
            continue
        entry = str(tool.get("entry") or "").strip()
        if entry != _TOOL_ENTRY and not entry.endswith("/diagnostic_receipt.py"):
            raise RoleError(
                f"{_TOOL_NAME} entry must be {_TOOL_ENTRY}; got {entry!r}"
            )
        return dict(tool)
    raise RoleError(
        f"role lacks tool {_TOOL_NAME} → {_TOOL_ENTRY}; "
        "refusing diagnostic receipt load"
    )


def _role_knows(role: Mapping[str, Any], *pointers: str) -> bool:
    known: set[str] = set()
    for item in role.get("knowledge") or []:
        if isinstance(item, str):
            known.add(item.strip())
        elif isinstance(item, Mapping):
            known.add(str(item.get("pointer") or "").strip())
    return any(p in known for p in pointers if p)


def load_receipt_from_role(
    role: Mapping[str, Any],
    *,
    slug: str,
) -> dict[str, Any]:
    """Read landed receipt.json for slug; return a compact operator card."""
    require_diagnostic_receipt_tool(role)
    key = str(slug or "").strip().lower()
    if key == "repair":
        raise RoleError(
            "repair slug has contract only — no receipt.json twin; refusing invent"
        )
    try:
        pointer = SLUG_TO_RECEIPT_JSON[key]
        md_pointer = SLUG_TO_RECEIPT_MD[key]
    except KeyError as exc:
        raise RoleError(
            f"unknown diagnostic receipt slug {key!r}; "
            f"expected one of {sorted(SLUG_TO_RECEIPT_JSON)}"
        ) from exc
    if not _role_knows(role, pointer, md_pointer):
        raise RoleError(
            f"role knowledge missing pointer {md_pointer} or {pointer}; "
            "refusing load"
        )
    path = _ROOT / pointer
    if not path.is_file():
        raise RoleError(f"landed receipt missing on disk: {pointer}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RoleError(f"failed to read {pointer}: {exc}") from exc
    if not isinstance(raw, dict):
        raise RoleError(f"{pointer} must be a JSON object")

    out: dict[str, Any] = {
        "slug": key,
        "pointer": pointer,
        "receipt_id": raw.get("receipt_id"),
        "status": raw.get("status"),
        "cash_usd": raw.get("cash_usd"),
        "payment_verified": raw.get("payment_verified"),
        "buyer_delivery": raw.get("buyer_delivery"),
        "live_crm_writes": raw.get("live_crm_writes"),
        "real_dealerships": raw.get("real_dealerships"),
        "pii_emitted": raw.get("pii_emitted"),
        "external_messages_sent": raw.get("external_messages_sent"),
        "outreach": raw.get("outreach"),
        "test_command": raw.get("test_command"),
        "expected": raw.get("expected"),
    }
    blob = json.dumps(out)
    for forbidden in ("sk_", "rk_", "whsec_", "prod_", "price_", "plink_"):
        if forbidden in blob:
            raise RoleError(f"receipt card leaked forbidden token prefix {forbidden}")
    return out
