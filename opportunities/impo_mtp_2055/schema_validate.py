"""Root packet validation for the IMPO MTP 2055 readiness schema."""

from __future__ import annotations

from typing import Any

from .schema_core import SCHEMA_VERSION, _require_exact_keys, _require_int, _require_mapping, parse_timestamp
from .schema_validate_commercial import validate_authority, validate_owner_notes, validate_pricing
from .schema_validate_qualification import (
    validate_capabilities,
    validate_documents,
    validate_organization,
    validate_projects,
    validate_team,
)
from .schema_validate_source import validate_opportunity, validate_source_checks


def validate_input(value: Any) -> dict[str, Any]:
    """Validate, normalize, and detach a readiness input from caller-owned objects."""

    root = _require_mapping(value, "$input")
    _require_exact_keys(
        root,
        "$input",
        (
            "schema_version",
            "as_of",
            "opportunity",
            "source_checks",
            "organization",
            "team",
            "projects",
            "capabilities",
            "documents",
            "pricing",
            "authority",
            "owner_notes",
        ),
    )
    version = _require_int(root["schema_version"], "schema_version", minimum=SCHEMA_VERSION, maximum=SCHEMA_VERSION)
    as_of_dt = parse_timestamp(root["as_of"], "as_of")
    opportunity, source_sha = validate_opportunity(root["opportunity"])
    return {
        "schema_version": version,
        "as_of": as_of_dt.isoformat(),
        "opportunity": opportunity,
        "source_checks": validate_source_checks(
            root["source_checks"],
            as_of_dt=as_of_dt,
            source_sha=source_sha,
        ),
        "organization": validate_organization(root["organization"]),
        "team": validate_team(root["team"]),
        "projects": validate_projects(root["projects"]),
        "capabilities": validate_capabilities(root["capabilities"]),
        "documents": validate_documents(root["documents"]),
        "pricing": validate_pricing(root["pricing"]),
        "authority": validate_authority(root["authority"]),
        "owner_notes": validate_owner_notes(root["owner_notes"]),
    }
