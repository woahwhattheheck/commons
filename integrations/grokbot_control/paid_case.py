#!/usr/bin/env python3
"""Build grokbot_control `case` dicts from paid Autopsy offer truth.

Does not touch Stripe, fulfillment.py, or checkout URLs. Callers pass the
normalized case into GrokBotControlClient.submit / grokbot_submit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .store import normalize_case

_DEFAULT_OFFER = (
    Path(__file__).resolve().parents[2]
    / "revenue"
    / "agent_failure_autopsy"
    / "offer.json"
)

_RECEIPT_OPTIONAL = (
    "client_reference_id",
    "g2_run_id",
    "g2_session_id",
    "payment_observed_at",
)
_RECEIPT_MAX = 200
_FORBIDDEN_RECEIPT_KEYS = frozenset(
    {
        "email",
        "buyer_email",
        "customer",
        "name",
        "phone",
        "artifact",
        "artifacts",
        "pii",
        "secret",
        "token",
    }
)


def load_autopsy_offer(path: Path | str | None = None) -> dict[str, Any]:
    """Load the checked-in Autopsy offer.json (LIVE_VERIFIED truth)."""
    target = Path(path) if path is not None else _DEFAULT_OFFER
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("offer.json must be an object")
    return data


def case_from_autopsy_offer(
    offer: Mapping[str, Any] | Path | str | None = None,
    *,
    case_ref: str,
    client_reference_id: str | None = None,
    sku: str | None = None,
) -> dict[str, str]:
    """Map Autopsy offer + private case pointers into a G2 `case` object.

    Required: nonempty case_ref (opaque private case id — never buyer PII).
    offer_id comes from offer.json. sku defaults to offer_id when omitted.
    client_reference_id is optional (Stripe client_reference_id when known).
    """
    if isinstance(offer, (str, Path)) or offer is None:
        payload = load_autopsy_offer(offer)
    elif isinstance(offer, Mapping):
        payload = dict(offer)
    else:
        raise ValueError("offer must be a mapping, path, or None")

    offer_id = payload.get("offer_id")
    if not isinstance(offer_id, str) or not offer_id.strip():
        raise ValueError("offer.offer_id must be a nonempty string")

    ref = case_ref.strip() if isinstance(case_ref, str) else ""
    if not ref:
        raise ValueError("case_ref must be a nonempty string")

    raw: dict[str, Any] = {
        "offer_id": offer_id.strip(),
        "case_ref": ref,
        "sku": (sku.strip() if isinstance(sku, str) and sku.strip() else offer_id.strip()),
    }
    if client_reference_id is not None:
        raw["client_reference_id"] = client_reference_id

    normalized = normalize_case(raw)
    if normalized is None:
        raise ValueError("normalized case is empty")
    return normalized


def _receipt_text(value: str) -> str:
    text = value.strip()
    if len(text) > _RECEIPT_MAX:
        raise ValueError(f"receipt values must not exceed {_RECEIPT_MAX} characters")
    return text


def receipt_row_from_case(
    case: Mapping[str, Any],
    *,
    g2_run_id: str | None = None,
    g2_session_id: str | None = None,
    payment_observed_at: str | None = None,
    state: str = "UNVERIFIED",
) -> dict[str, str]:
    """Build an opaque public seats `case_row` from a G2 case + optional run ids.

    Required on the row: offer_id, case_ref, sku, state.
    Optional: client_reference_id, g2_run_id, g2_session_id, payment_observed_at.
    Callers supply opaque identifiers; this helper is not a PII sanitizer or
    payment verifier. State defaults to UNVERIFIED; callers pass an observed
    state only when supported by evidence. Values over 200 characters raise
    instead of silently changing identifiers. Does not append to seats.json;
    callers append after REAL_STRIPE_PAYMENT_OBSERVED + owner authorization.
    """
    if any(k in case for k in _FORBIDDEN_RECEIPT_KEYS):
        raise ValueError("case must not carry buyer PII / artifact keys")

    normalized = normalize_case(case)
    if normalized is None:
        raise ValueError("case must normalize to a nonempty object")
    for required in ("offer_id", "case_ref", "sku"):
        if required not in normalized:
            raise ValueError(f"case missing {required}")

    if not isinstance(state, str) or not state.strip():
        raise ValueError("state must be a nonempty string")

    row: dict[str, str] = {
        "offer_id": normalized["offer_id"],
        "case_ref": normalized["case_ref"],
        "sku": normalized["sku"],
        "state": _receipt_text(state),
    }
    if "client_reference_id" in normalized:
        row["client_reference_id"] = normalized["client_reference_id"]

    optionals = {
        "g2_run_id": g2_run_id,
        "g2_session_id": g2_session_id,
        "payment_observed_at": payment_observed_at,
    }
    for key, value in optionals.items():
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a nonempty string when provided")
        row[key] = _receipt_text(value)

    for key in row:
        if key in _FORBIDDEN_RECEIPT_KEYS:
            raise ValueError(f"forbidden receipt key: {key}")
    return row
