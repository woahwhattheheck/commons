"""Entity-level validators for the IMPO MTP 2055 readiness schema."""

from __future__ import annotations

from typing import Any

from .schema_core import (
    EVIDENCE_STATES,
    MAX_MINOR,
    _fail,
    _optional_text,
    _require_bool,
    _require_exact_keys,
    _require_int,
    _require_list,
    _require_mapping,
    _require_text,
)

def _validate_evidence(value: Any, path: str) -> dict[str, Any]:
    obj = _require_mapping(value, path)
    _require_exact_keys(obj, path, ("state", "reference", "note"))
    state = _require_text(obj["state"], f"{path}.state", max_length=32)
    if state not in EVIDENCE_STATES:
        _fail(f"{path}.state", f"must be one of {sorted(EVIDENCE_STATES)}")
    reference = _optional_text(obj["reference"], f"{path}.reference", max_length=2_048)
    note = _optional_text(obj["note"], f"{path}.note", max_length=4_096)
    if state == "VERIFIED" and reference is None:
        _fail(path, "VERIFIED evidence requires a non-empty reference")
    if state == "NOT_APPLICABLE" and reference is not None:
        _fail(path, "NOT_APPLICABLE evidence must not claim a reference")
    return {"state": state, "reference": reference, "note": note}


def _validate_person(value: Any, path: str) -> dict[str, Any]:
    obj = _require_mapping(value, path)
    _require_exact_keys(
        obj,
        path,
        ("name", "role", "years_relevant", "allocation_percent", "resume_evidence"),
    )
    name = _require_text(obj["name"], f"{path}.name", max_length=200)
    role = _require_text(obj["role"], f"{path}.role", max_length=200)
    years = _require_int(obj["years_relevant"], f"{path}.years_relevant", maximum=100)
    allocation = _require_int(
        obj["allocation_percent"], f"{path}.allocation_percent", maximum=100
    )
    resume = _validate_evidence(obj["resume_evidence"], f"{path}.resume_evidence")
    return {
        "name": name,
        "role": role,
        "years_relevant": years,
        "allocation_percent": allocation,
        "resume_evidence": resume,
    }


def _validate_project(value: Any, path: str) -> dict[str, Any]:
    obj = _require_mapping(value, path)
    _require_exact_keys(
        obj,
        path,
        (
            "name",
            "client",
            "is_impo_client",
            "staff_roles",
            "relevance",
            "reference_name",
            "reference_email",
            "evidence",
        ),
    )
    roles = _require_list(obj["staff_roles"], f"{path}.staff_roles", max_items=32)
    clean_roles = [
        _require_text(role, f"{path}.staff_roles[{index}]", max_length=200)
        for index, role in enumerate(roles)
    ]
    if len(set(clean_roles)) != len(clean_roles):
        _fail(f"{path}.staff_roles", "must not contain duplicates")
    reference_email = _require_text(
        obj["reference_email"], f"{path}.reference_email", max_length=320
    )
    if "@" not in reference_email or reference_email.startswith("@") or reference_email.endswith("@"):
        _fail(f"{path}.reference_email", "must look like an email address")
    return {
        "name": _require_text(obj["name"], f"{path}.name", max_length=300),
        "client": _require_text(obj["client"], f"{path}.client", max_length=300),
        "is_impo_client": _require_bool(obj["is_impo_client"], f"{path}.is_impo_client"),
        "staff_roles": clean_roles,
        "relevance": _require_text(obj["relevance"], f"{path}.relevance", max_length=2_000),
        "reference_name": _require_text(
            obj["reference_name"], f"{path}.reference_name", max_length=200
        ),
        "reference_email": reference_email,
        "evidence": _validate_evidence(obj["evidence"], f"{path}.evidence"),
    }


def _validate_partner(value: Any, path: str) -> dict[str, Any]:
    obj = _require_mapping(value, path)
    _require_exact_keys(obj, path, ("name", "role", "commitment_evidence", "approved_for_disclosure"))
    return {
        "name": _require_text(obj["name"], f"{path}.name", max_length=300),
        "role": _require_text(obj["role"], f"{path}.role", max_length=500),
        "commitment_evidence": _validate_evidence(
            obj["commitment_evidence"], f"{path}.commitment_evidence"
        ),
        "approved_for_disclosure": _require_bool(
            obj["approved_for_disclosure"], f"{path}.approved_for_disclosure"
        ),
    }


def _validate_pricing_task(value: Any, path: str) -> dict[str, Any]:
    obj = _require_mapping(value, path)
    _require_exact_keys(obj, path, ("id", "name", "rate_minor", "hours", "other_cost_minor"))
    rate = _require_int(obj["rate_minor"], f"{path}.rate_minor", maximum=100_000_000)
    hours = _require_int(obj["hours"], f"{path}.hours", maximum=1_000_000)
    other = _require_int(obj["other_cost_minor"], f"{path}.other_cost_minor")
    subtotal = rate * hours + other
    if subtotal > MAX_MINOR:
        _fail(path, "task subtotal exceeds supported range")
    return {
        "id": _require_text(obj["id"], f"{path}.id", max_length=100),
        "name": _require_text(obj["name"], f"{path}.name", max_length=300),
        "rate_minor": rate,
        "hours": hours,
        "other_cost_minor": other,
        "subtotal_minor": subtotal,
    }


