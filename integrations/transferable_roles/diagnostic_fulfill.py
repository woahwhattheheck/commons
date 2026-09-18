#!/usr/bin/env python3
"""Role-gated SLA deadline + status for $199 diagnostic fulfillment roles.

Gates on tool `diagnostic_contract`, loads landed contract commercial window
via `diagnostic_contract.load_contract_from_role`, then calls landed
`revenue/agent_failure_autopsy/fulfillment.py` `next_business_day` — import-only;
do not remint fulfillment.py / contracts / Stripe.

`run_deadline` returns delivery_due_at.
`run_sla_status` compares as_of vs due → OPEN|MISSED + refund miss-remedy card.
"""

from __future__ import annotations

import importlib.util
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from diagnostic_contract import load_contract_from_role, require_diagnostic_contract_tool
from roles import RoleError

_FULFILL_REL = "revenue/agent_failure_autopsy/fulfillment.py"
_ROOT = Path(__file__).resolve().parents[2]


def _load_fulfillment_module() -> Any:
    path = _ROOT / _FULFILL_REL
    if not path.is_file():
        raise RoleError(f"landed fulfillment missing on disk: {_FULFILL_REL}")
    spec = importlib.util.spec_from_file_location(
        "commons_autopsy_fulfillment_landed_for_diag", path
    )
    if spec is None or spec.loader is None:
        raise RoleError(f"failed to load {_FULFILL_REL}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _require_one_business_day_window(window: Any) -> str:
    text = str(window or "").strip()
    if "one business day" not in text.lower():
        raise RoleError(
            f"diagnostic_window must be one business day; got {text!r}"
        )
    return text


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
    slug: str,
    usable_evidence_at: str,
) -> dict[str, Any]:
    """Compute delivery_due_at for a $199 diagnostic slug.

    Uses landed Autopsy calendar helper `next_business_day` (shared; not a remint)
    after confirming the role can load the landed contract for the slug.
    """
    require_diagnostic_contract_tool(role)
    stamp = str(usable_evidence_at or "").strip()
    if not stamp:
        raise RoleError("usable_evidence_at must be a nonempty string")
    card = load_contract_from_role(role, slug=slug)
    window = _require_one_business_day_window(card.get("diagnostic_window"))
    mod = _load_fulfillment_module()
    try:
        due = mod.next_business_day(stamp)
    except Exception as exc:  # noqa: BLE001 — map landed errors
        raise RoleError(str(exc)) from exc
    out: dict[str, Any] = {
        "slug": card.get("slug"),
        "pointer": card.get("pointer"),
        "usable_evidence_at": stamp,
        "delivery_due_at": due,
        "diagnostic_window": window,
        "diagnostic_usd": card.get("diagnostic_usd"),
        "refund": card.get("refund"),
    }
    _forbid_secrets(json.dumps(out))
    return out


def run_sla_status(
    role: Mapping[str, Any],
    *,
    slug: str,
    usable_evidence_at: str,
    as_of: str,
) -> dict[str, Any]:
    """OPEN|MISSED SLA card vs as_of, with landed miss-remedy refund text.

    Reuses run_deadline calendar path; does not remint autopsy-fulfill.
    within_one_business_day matches Autopsy report rule: as_of <= delivery_due_at.
    """
    base = run_deadline(
        role, slug=slug, usable_evidence_at=usable_evidence_at
    )
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
