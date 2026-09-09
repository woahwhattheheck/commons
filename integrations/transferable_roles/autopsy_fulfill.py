#!/usr/bin/env python3
"""Role-gated execute wrap into landed Autopsy fulfillment.py.

Gates on tool `autopsy_fulfillment` and calls landed
`revenue/agent_failure_autopsy/fulfillment.py` helpers (`next_business_day`,
`validate_bundle`) — import-only; do not remint fulfillment.py.

`run_deadline` returns delivery_due_at + landed offer refund + amount_usd.
`run_sla_status` compares as_of vs due → OPEN|MISSED and reuses deadline cash
fields (WEDGE leftovers after #8999 / #9015 / #9041).
"""

from __future__ import annotations

import importlib.util
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from roles import RoleError

_TOOL_NAME = "autopsy_fulfillment"
_TOOL_ENTRY = "python3 revenue/agent_failure_autopsy/fulfillment.py"
_FULFILL_REL = "revenue/agent_failure_autopsy/fulfillment.py"
_OFFER_REL = "revenue/agent_failure_autopsy/offer.json"
_EXAMPLES_REL = "revenue/agent_failure_autopsy/examples"

_ROOT = Path(__file__).resolve().parents[2]


def require_autopsy_fulfillment_tool(role: Mapping[str, Any]) -> dict[str, Any]:
    """Refuse unless the role tools the landed Autopsy fulfillment entry."""
    if not isinstance(role, Mapping):
        raise RoleError("role must be an object")
    for tool in role.get("tools") or []:
        if not isinstance(tool, Mapping):
            continue
        if tool.get("name") != _TOOL_NAME:
            continue
        entry = str(tool.get("entry") or "").strip()
        if entry != _TOOL_ENTRY and not entry.endswith(
            "/agent_failure_autopsy/fulfillment.py"
        ):
            raise RoleError(
                f"{_TOOL_NAME} entry must be {_TOOL_ENTRY}; got {entry!r}"
            )
        return dict(tool)
    raise RoleError(
        f"role lacks tool {_TOOL_NAME} → {_TOOL_ENTRY}; "
        "refusing autopsy fulfill execute (not an Autopsy fulfillment role)"
    )


def _load_fulfillment_module() -> Any:
    path = _ROOT / _FULFILL_REL
    if not path.is_file():
        raise RoleError(f"landed fulfillment missing on disk: {_FULFILL_REL}")
    spec = importlib.util.spec_from_file_location(
        "commons_autopsy_fulfillment_landed", path
    )
    if spec is None or spec.loader is None:
        raise RoleError(f"failed to load {_FULFILL_REL}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_offer_cash_fields() -> dict[str, Any]:
    """Landed offer.json refund + price.amount (read-only; no remint)."""
    path = _ROOT / _OFFER_REL
    if not path.is_file():
        raise RoleError(f"landed offer missing on disk: {_OFFER_REL}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RoleError("offer.json must be an object")
    refund = data.get("refund")
    if not isinstance(refund, str) or not refund.strip():
        raise RoleError("offer.refund must be a nonempty string")
    text = refund.strip()
    for forbidden in ("sk_", "rk_", "whsec_", "prod_", "price_", "plink_"):
        if forbidden in text:
            raise RoleError(f"offer.refund leaked forbidden token prefix {forbidden}")
    price = data.get("price")
    if not isinstance(price, dict):
        raise RoleError("offer.price must be an object")
    amount = price.get("amount")
    if not isinstance(amount, (int, float)) or isinstance(amount, bool):
        raise RoleError("offer.price.amount must be a number")
    return {"refund": text, "amount_usd": int(amount)}


def _parse_aware(stamp: str, label: str) -> datetime:
    text = str(stamp or "").strip()
    if not text:
        raise RoleError(f"{label} must be a nonempty string")
    if not re.search(r"(?:Z|[+-]\d{2}:\d{2})$", text):
        raise RoleError(f"{label} must be an offset-aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RoleError(f"{label} is not a valid timestamp") from exc
    if parsed.tzinfo is None:
        raise RoleError(f"{label} must carry a UTC offset")
    return parsed


def _forbid_secrets(blob: str) -> None:
    for forbidden in ("sk_", "rk_", "whsec_", "prod_", "price_", "plink_"):
        if forbidden in blob:
            raise RoleError(f"card leaked forbidden token prefix {forbidden}")


def run_deadline(
    role: Mapping[str, Any],
    *,
    usable_evidence_at: str,
) -> dict[str, Any]:
    """Compute delivery_due_at + landed offer cash fields.

    Parity with diagnostic deadline (already stamps diagnostic_usd + refund):
    Autopsy deadline previously omitted cash; SLA had it after #9015/#9041.
    """
    require_autopsy_fulfillment_tool(role)
    stamp = str(usable_evidence_at or "").strip()
    if not stamp:
        raise RoleError("usable_evidence_at must be a nonempty string")
    mod = _load_fulfillment_module()
    try:
        due = mod.next_business_day(stamp)
    except Exception as exc:  # noqa: BLE001 — map landed errors
        raise RoleError(str(exc)) from exc
    cash = _load_offer_cash_fields()
    out: dict[str, Any] = {
        "usable_evidence_at": stamp,
        "delivery_due_at": due,
        "refund": cash["refund"],
        "amount_usd": cash["amount_usd"],
    }
    _forbid_secrets(json.dumps(out))
    return out


def run_sla_status(
    role: Mapping[str, Any],
    *,
    usable_evidence_at: str,
    as_of: str,
) -> dict[str, Any]:
    """OPEN|MISSED Autopsy SLA; reuses deadline cash fields.

    Reuses run_deadline calendar + offer cash path; does not remint
    fulfillment.py / offer.json.
    within_one_business_day matches Autopsy report rule: as_of <= delivery_due_at.
    """
    base = run_deadline(role, usable_evidence_at=usable_evidence_at)
    as_of_stamp = str(as_of or "").strip()
    as_of_dt = _parse_aware(as_of_stamp, "as_of")
    due_dt = _parse_aware(str(base["delivery_due_at"]), "delivery_due_at")
    within = as_of_dt <= due_dt
    out: dict[str, Any] = {
        **base,
        "as_of": as_of_stamp,
        "within_one_business_day": within,
        "sla_status": "OPEN" if within else "MISSED",
    }
    _forbid_secrets(json.dumps(out))
    return out


def run_validate(
    role: Mapping[str, Any],
    *,
    intake: str | Path | None = None,
    report: str | Path | None = None,
    evidence_root: str | Path | None = None,
) -> dict[str, Any]:
    """Validate intake+report via landed fulfillment.validate_bundle.

    Defaults to checked-in examples/ (SYNTHETIC_EXAMPLE hermetic path).
    """
    require_autopsy_fulfillment_tool(role)
    examples = _ROOT / _EXAMPLES_REL
    intake_path = Path(intake) if intake is not None else examples / "intake.json"
    report_path = Path(report) if report is not None else examples / "report.json"
    root = Path(evidence_root) if evidence_root is not None else examples
    mod = _load_fulfillment_module()
    try:
        intake_obj = mod.load_json(intake_path)
        report_obj = mod.load_json(report_path)
        result = mod.validate_bundle(intake_obj, report_obj, root)
    except Exception as exc:  # noqa: BLE001 — map landed errors
        raise RoleError(str(exc)) from exc
    if not isinstance(result, dict):
        raise RoleError("fulfillment.validate_bundle must return an object")
    # Never surface secrets from validate output.
    blob = json.dumps(result)
    for forbidden in ("sk_", "rk_", "whsec_", "token", "password"):
        if forbidden in blob.lower() and forbidden in ("sk_", "rk_", "whsec_"):
            raise RoleError(f"validate result leaked forbidden prefix {forbidden}")
    return result
