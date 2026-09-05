#!/usr/bin/env python3
"""Executable Autopsy paid→G2 helpers for transferable roles.

Wraps SPARK `paid_case.py` so a successor can build a G2 `case` or opaque
seats `case_row` from an Autopsy R4 role without reminting SPARK code.
Roles still confer no Stripe access and never invent paid seats rows.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping

from roles import RoleError

_PAID_CASE_ENTRY = "integrations/grokbot_control/paid_case.py"
_AUTOPSY_TOOL = "autopsy_paid_case"

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from integrations.grokbot_control.paid_case import (  # noqa: E402
    case_from_autopsy_offer,
    receipt_row_from_case,
)


def require_autopsy_paid_tool(role: Mapping[str, Any]) -> dict[str, Any]:
    """Refuse unless the role tools the landed SPARK paid_case entry."""
    if not isinstance(role, Mapping):
        raise RoleError("role must be an object")
    for tool in role.get("tools") or []:
        if not isinstance(tool, Mapping):
            continue
        if tool.get("name") != _AUTOPSY_TOOL:
            continue
        entry = str(tool.get("entry") or "").strip()
        if entry != _PAID_CASE_ENTRY and not entry.endswith("/paid_case.py"):
            raise RoleError(
                f"{_AUTOPSY_TOOL} entry must be {_PAID_CASE_ENTRY}; got {entry!r}"
            )
        return dict(tool)
    raise RoleError(
        f"role lacks tool {_AUTOPSY_TOOL} → {_PAID_CASE_ENTRY}; "
        "refusing autopsy case build (not an Autopsy paid-fulfillment role)"
    )


def build_g2_case_from_role(
    role: Mapping[str, Any],
    *,
    case_ref: str,
    client_reference_id: str | None = None,
    sku: str | None = None,
) -> dict[str, str]:
    """Build a G2 case via SPARK case_from_autopsy_offer for an Autopsy role."""
    require_autopsy_paid_tool(role)
    try:
        return case_from_autopsy_offer(
            case_ref=case_ref,
            client_reference_id=client_reference_id,
            sku=sku,
        )
    except ValueError as exc:
        raise RoleError(str(exc)) from exc


def build_receipt_row_from_role(
    role: Mapping[str, Any],
    *,
    case_ref: str,
    client_reference_id: str | None = None,
    sku: str | None = None,
    g2_run_id: str | None = None,
    g2_session_id: str | None = None,
    payment_observed_at: str | None = None,
    state: str = "UNVERIFIED",
) -> dict[str, str]:
    """Build an opaque seats case_row via SPARK receipt_row_from_case.

    Does not append to seats.json. Callers append only after
    REAL_STRIPE_PAYMENT_OBSERVED + owner authorization.
    """
    case = build_g2_case_from_role(
        role,
        case_ref=case_ref,
        client_reference_id=client_reference_id,
        sku=sku,
    )
    try:
        return receipt_row_from_case(
            case,
            g2_run_id=g2_run_id,
            g2_session_id=g2_session_id,
            payment_observed_at=payment_observed_at,
            state=state,
        )
    except ValueError as exc:
        raise RoleError(str(exc)) from exc
