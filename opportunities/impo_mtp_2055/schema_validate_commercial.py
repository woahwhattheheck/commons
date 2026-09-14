"""Pricing, authority, and owner-note validation for IMPO MTP 2055."""

from __future__ import annotations

from typing import Any

from .schema_core import (
    AUTHORITY_KEYS,
    _fail,
    _optional_text,
    _require_bool,
    _require_exact_keys,
    _require_int,
    _require_list,
    _require_mapping,
    _require_text,
)
from .schema_entities import _validate_evidence, _validate_pricing_task


def validate_pricing(value: Any) -> dict[str, Any]:
    pricing = _require_mapping(value, "pricing")
    _require_exact_keys(pricing, "pricing", ("tasks", "stated_total_minor", "commercial_approval"))
    task_values = _require_list(pricing["tasks"], "pricing.tasks", max_items=100)
    tasks = [_validate_pricing_task(item, f"pricing.tasks[{i}]") for i, item in enumerate(task_values)]
    task_ids = [item["id"] for item in tasks]
    if len(set(task_ids)) != len(task_ids):
        _fail("pricing.tasks", "task ids must be unique")
    computed_total = sum(item["subtotal_minor"] for item in tasks)
    stated_total = _require_int(pricing["stated_total_minor"], "pricing.stated_total_minor")
    if computed_total != stated_total:
        _fail(
            "pricing.stated_total_minor",
            f"must equal computed task total {computed_total}",
        )
    return {
        "tasks": tasks,
        "stated_total_minor": stated_total,
        "commercial_approval": _validate_evidence(
            pricing["commercial_approval"], "pricing.commercial_approval"
        ),
    }


def validate_authority(value: Any) -> dict[str, Any]:
    authority = _require_mapping(value, "authority")
    _require_exact_keys(authority, "authority", (*AUTHORITY_KEYS, "approved_by", "approval_reference"))
    normalized = {key: _require_bool(authority[key], f"authority.{key}") for key in AUTHORITY_KEYS}
    approved_by = _optional_text(authority["approved_by"], "authority.approved_by", max_length=300)
    approval_reference = _optional_text(
        authority["approval_reference"], "authority.approval_reference", max_length=2_048
    )
    if any(normalized.values()) and (approved_by is None or approval_reference is None):
        _fail("authority", "any true authority requires approved_by and approval_reference")
    if not any(normalized.values()) and (approved_by is not None or approval_reference is not None):
        _fail("authority", "approval metadata must be absent when all authority is false")
    normalized.update(
        {"approved_by": approved_by, "approval_reference": approval_reference}
    )
    return normalized


def validate_owner_notes(value: Any) -> list[str]:
    owner_notes = _require_list(value, "owner_notes", max_items=100)
    return [
        _require_text(note, f"owner_notes[{index}]", max_length=2_000)
        for index, note in enumerate(owner_notes)
    ]
