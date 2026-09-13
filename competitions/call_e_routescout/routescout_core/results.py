from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .contracts import (RouteScoutError, _CONTROL, _RESULT_FIELDS, CHANNEL_TYPES, PERMISSION_STATES, TERMINAL, _exact_keys, inquiry_digest, validate_inquiry)

def _clean_result_text(value: Any, field: str, limit: int) -> str:
    if not isinstance(value, str):
        raise RouteScoutError(f"{field}: must be string")
    if _CONTROL.search(value) or len(value) > limit:
        raise RouteScoutError(f"{field}: invalid text")
    return value.strip()

def validate_structured_result(result: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(result, _RESULT_FIELDS, "structured_result")
    for field in ("organization_confirmed","consented_to_continue","routing_answered",
                  "channel_is_business","do_not_contact"):
        if type(result[field]) is not bool:
            raise RouteScoutError(f"{field}: must be boolean")
    channel_type = _clean_result_text(result["channel_type"], "channel_type", 24)
    permission_state = _clean_result_text(result["permission_state"], "permission_state", 24)
    if channel_type not in CHANNEL_TYPES:
        raise RouteScoutError("channel_type: invalid")
    if permission_state not in PERMISSION_STATES:
        raise RouteScoutError("permission_state: invalid")
    return {
        "organization_confirmed": result["organization_confirmed"],
        "consented_to_continue": result["consented_to_continue"],
        "routing_answered": result["routing_answered"],
        "department_or_role": _clean_result_text(result["department_or_role"], "department_or_role", 160),
        "channel_type": channel_type,
        "channel_value": _clean_result_text(result["channel_value"], "channel_value", 240),
        "channel_is_business": result["channel_is_business"],
        "permission_state": permission_state,
        "do_not_contact": result["do_not_contact"],
        "verbatim_route": _clean_result_text(result["verbatim_route"], "verbatim_route", 500),
        "notes": _clean_result_text(result["notes"], "notes", 500),
    }

def normalize_terminal_call(call: Mapping[str, Any]) -> dict[str, Any]:
    status = call.get("status")
    if status not in TERMINAL:
        raise RouteScoutError("CALL-E call is not terminal")
    recipients = call.get("recipients")
    structured: Any = None
    if isinstance(recipients, list) and len(recipients) == 1 and isinstance(recipients[0], Mapping):
        structured = recipients[0].get("structured_result")
    if not isinstance(structured, Mapping):
        structured = call.get("structured_result")
    if not isinstance(structured, Mapping):
        structured = {}
    return {
        "provider_status": status,
        "task_completed": call.get("task_completed") is True,
        "structured_result": dict(structured),
        "provider_evidence": [x for x in (call.get("evidence") or []) if isinstance(x, str)][:20],
    }

def reconcile(inquiry: Mapping[str, Any], terminal: Mapping[str, Any]) -> dict[str, Any]:
    i = validate_inquiry(inquiry)
    normalized = normalize_terminal_call(terminal)
    reasons: list[str] = []
    try:
        r = validate_structured_result(normalized["structured_result"])
    except RouteScoutError as exc:
        r = None
        reasons.append(f"unusable structured result: {exc}")
    if normalized["provider_status"] != "completed" or not normalized["task_completed"] or r is None:
        outcome = "HUMAN_REQUIRED"
        if not reasons:
            reasons.append("provider call did not complete with usable structured result")
    elif r["do_not_contact"] or r["permission_state"] == "declined":
        outcome = "DO_NOT_CONTACT"
    elif not (r["organization_confirmed"] and r["consented_to_continue"] and r["routing_answered"]):
        outcome = "NO_ROUTE"
        reasons.append("organization/consent/routing answer not all confirmed")
    elif (
        r["channel_type"] != "none"
        and bool(r["channel_value"])
        and r["channel_is_business"]
        and r["permission_state"] in {"invited", "permitted"}
        and bool(r["verbatim_route"])
    ):
        outcome = "ROUTE_FOUND"
    else:
        outcome = "NO_ROUTE"
        reasons.append("no permitted business follow-up channel proven")
    core = {
        "schema_version": 1,
        "inquiry_digest_sha256": inquiry_digest(i),
        "inquiry_id": i["inquiry_id"],
        "outcome": outcome,
        "route": None if r is None else {
            "department_or_role": r["department_or_role"],
            "channel_type": r["channel_type"],
            "channel_value": r["channel_value"],
            "permission_state": r["permission_state"],
            "verbatim_route": r["verbatim_route"],
        },
        "reasons": reasons,
        "provider_evidence": normalized["provider_evidence"],
        "authority": {
            "may_send_followup": False,
            "may_pitch": False,
            "may_negotiate": False,
            "may_bypass_procurement": False,
            "may_claim_acceptance": False,
            "may_claim_revenue": False,
        },
    }
    receipt = dict(core)
    receipt["receipt_sha256"] = hashlib.sha256(
        (json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")
    ).hexdigest()
    return receipt
