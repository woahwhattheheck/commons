"""Opportunity and source-generation validation for IMPO MTP 2055."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .schema_core import (
    CURRENCY_RE,
    HEX64_RE,
    _fail,
    _require_bool,
    _require_exact_keys,
    _require_int,
    _require_list,
    _require_mapping,
    _require_text,
    parse_timestamp,
)
from .schema_entities import _validate_evidence


def validate_opportunity(value: Any) -> tuple[dict[str, Any], str | None]:
    opportunity = _require_mapping(value, "opportunity")
    _require_exact_keys(
        opportunity,
        "opportunity",
        (
            "id",
            "title",
            "buyer",
            "source_url",
            "source_sha256",
            "released_at",
            "questions_due_at",
            "proposal_due_at",
            "currency",
            "budget_cap_minor",
        ),
    )
    source_sha = opportunity["source_sha256"]
    if source_sha is not None:
        source_sha = _require_text(source_sha, "opportunity.source_sha256", max_length=64)
        if not HEX64_RE.fullmatch(source_sha):
            _fail("opportunity.source_sha256", "must be 64 lowercase hexadecimal characters")
    released = parse_timestamp(opportunity["released_at"], "opportunity.released_at")
    questions_due = parse_timestamp(opportunity["questions_due_at"], "opportunity.questions_due_at")
    proposal_due = parse_timestamp(opportunity["proposal_due_at"], "opportunity.proposal_due_at")
    if not released < questions_due < proposal_due:
        _fail("opportunity", "timestamps must satisfy released_at < questions_due_at < proposal_due_at")
    currency = _require_text(opportunity["currency"], "opportunity.currency", max_length=3)
    if not CURRENCY_RE.fullmatch(currency):
        _fail("opportunity.currency", "must be an ISO-style three-letter uppercase code")
    normalized = {
        "id": _require_text(opportunity["id"], "opportunity.id", max_length=200),
        "title": _require_text(opportunity["title"], "opportunity.title", max_length=500),
        "buyer": _require_text(opportunity["buyer"], "opportunity.buyer", max_length=300),
        "source_url": _require_text(opportunity["source_url"], "opportunity.source_url", max_length=2_048),
        "source_sha256": source_sha,
        "released_at": released.isoformat(),
        "questions_due_at": questions_due.isoformat(),
        "proposal_due_at": proposal_due.isoformat(),
        "currency": currency,
        "budget_cap_minor": _require_int(
            opportunity["budget_cap_minor"], "opportunity.budget_cap_minor", minimum=1
        ),
    }
    return normalized, source_sha


def validate_source_checks(
    value: Any,
    *,
    as_of_dt: datetime,
    source_sha: str | None,
) -> dict[str, Any]:
    source_checks = _require_mapping(value, "source_checks")
    _require_exact_keys(
        source_checks,
        "source_checks",
        ("base_rfp_bytes_verified", "last_checked_at", "addenda", "questions_addendum"),
    )
    last_checked = parse_timestamp(source_checks["last_checked_at"], "source_checks.last_checked_at")
    if last_checked > as_of_dt:
        _fail("source_checks.last_checked_at", "must not be later than as_of")
    addenda_values = _require_list(source_checks["addenda"], "source_checks.addenda", max_items=100)
    addenda: list[dict[str, Any]] = []
    addendum_ids: set[str] = set()
    for index, raw in enumerate(addenda_values):
        path = f"source_checks.addenda[{index}]"
        obj = _require_mapping(raw, path)
        _require_exact_keys(obj, path, ("id", "sha256", "published_at", "signed_acknowledgement"))
        identifier = _require_text(obj["id"], f"{path}.id", max_length=200)
        if identifier in addendum_ids:
            _fail(f"{path}.id", "must be unique")
        addendum_ids.add(identifier)
        digest = _require_text(obj["sha256"], f"{path}.sha256", max_length=64)
        if not HEX64_RE.fullmatch(digest):
            _fail(f"{path}.sha256", "must be 64 lowercase hexadecimal characters")
        published = parse_timestamp(obj["published_at"], f"{path}.published_at")
        if published > as_of_dt:
            _fail(f"{path}.published_at", "must not be later than as_of")
        addenda.append(
            {
                "id": identifier,
                "sha256": digest,
                "published_at": published.isoformat(),
                "signed_acknowledgement": _require_bool(
                    obj["signed_acknowledgement"], f"{path}.signed_acknowledgement"
                ),
            }
        )
    normalized = {
        "base_rfp_bytes_verified": _require_bool(
            source_checks["base_rfp_bytes_verified"], "source_checks.base_rfp_bytes_verified"
        ),
        "last_checked_at": last_checked.isoformat(),
        "addenda": addenda,
        "questions_addendum": _validate_evidence(
            source_checks["questions_addendum"], "source_checks.questions_addendum"
        ),
    }
    if normalized["base_rfp_bytes_verified"] and source_sha is None:
        _fail("source_checks.base_rfp_bytes_verified", "cannot be true without source_sha256")
    return normalized
