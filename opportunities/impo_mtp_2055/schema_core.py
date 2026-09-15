"""Strict input validation for the IMPO MTP 2055 bid-readiness compiler."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = 1
MAX_TEXT = 8_192
MAX_LIST = 256
MAX_MINOR = 10_000_000_000
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
UEI_RE = re.compile(r"^[A-Z0-9]{12}$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")

AUTHORITY_KEYS = (
    "contact_buyer",
    "register_vendor",
    "register_prebid",
    "commit_pricing",
    "sign_forms",
    "submit_proposal",
    "accept_contract",
    "spend_funds",
)

DOCUMENT_KEYS = (
    "cover_letter",
    "firm_overview",
    "project_approach",
    "project_team",
    "project_sheets",
    "resumes",
    "form_a",
    "form_b",
    "form_c",
    "vendor_profile_evidence",
    "signed_questions_addendum",
    "separate_quote",
    "title_vi_assurances",
)

CAPABILITY_KEYS = (
    "metropolitan_transportation_planning",
    "federal_regulatory_compliance",
    "statistically_valid_regional_survey",
    "public_and_stakeholder_engagement",
    "travel_demand_and_scenario_analysis",
    "project_scoring_and_fiscal_constraint",
    "gis_and_editable_source_delivery",
    "web_accessible_publication",
    "performance_measurement_and_dashboards",
    "quality_assurance",
)

EVIDENCE_STATES = frozenset({"VERIFIED", "MISSING", "UNKNOWN", "NOT_APPLICABLE"})


class OpportunityInputError(ValueError):
    """Raised when an input packet is malformed or internally contradictory."""


def _fail(path: str, message: str) -> None:
    raise OpportunityInputError(f"{path}: {message}")


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    return value


def _require_list(value: Any, path: str, *, max_items: int = MAX_LIST) -> list[Any]:
    if not isinstance(value, list):
        _fail(path, "must be an array")
    if len(value) > max_items:
        _fail(path, f"must contain at most {max_items} items")
    return value


def _require_bool(value: Any, path: str) -> bool:
    if type(value) is not bool:
        _fail(path, "must be a boolean")
    return value


def _require_int(
    value: Any,
    path: str,
    *,
    minimum: int = 0,
    maximum: int = MAX_MINOR,
) -> int:
    if type(value) is not int:
        _fail(path, "must be an integer")
    if value < minimum or value > maximum:
        _fail(path, f"must be between {minimum} and {maximum}")
    return value


def _require_text(
    value: Any,
    path: str,
    *,
    allow_empty: bool = False,
    max_length: int = MAX_TEXT,
) -> str:
    if not isinstance(value, str):
        _fail(path, "must be a string")
    if len(value) > max_length:
        _fail(path, f"must be at most {max_length} characters")
    if not allow_empty and not value.strip():
        _fail(path, "must not be empty")
    if "\x00" in value:
        _fail(path, "must not contain NUL")
    return value


def _optional_text(value: Any, path: str, *, max_length: int = MAX_TEXT) -> str | None:
    if value is None:
        return None
    return _require_text(value, path, max_length=max_length)


def _require_exact_keys(obj: Mapping[str, Any], path: str, keys: Iterable[str]) -> None:
    expected = set(keys)
    actual = set(obj)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        _fail(path, f"missing keys: {', '.join(missing)}")
    if extra:
        _fail(path, f"unexpected keys: {', '.join(extra)}")


def parse_timestamp(value: Any, path: str) -> datetime:
    text = _require_text(value, path, max_length=64)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        _fail(path, f"must be an ISO-8601 timestamp: {exc}")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(path, "must include an explicit UTC offset")
    return parsed


