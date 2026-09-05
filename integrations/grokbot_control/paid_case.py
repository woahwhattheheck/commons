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
