"""Organization, team, project, capability, and document validation."""

from __future__ import annotations

from typing import Any

from .schema_core import (
    CAPABILITY_KEYS,
    DOCUMENT_KEYS,
    UEI_RE,
    _fail,
    _optional_text,
    _require_exact_keys,
    _require_list,
    _require_mapping,
)
from .schema_entities import (
    _validate_evidence,
    _validate_partner,
    _validate_person,
    _validate_project,
)


def validate_organization(value: Any) -> dict[str, Any]:
    organization = _require_mapping(value, "organization")
    _require_exact_keys(
        organization,
        "organization",
        (
            "legal_name",
            "legal_form",
            "sam_uei",
            "marion_county_vendor_profile",
            "liability_insurance",
            "debarment_and_suspension",
            "title_vi_compliance",
        ),
    )
    sam_uei = _optional_text(organization["sam_uei"], "organization.sam_uei", max_length=12)
    if sam_uei is not None and not UEI_RE.fullmatch(sam_uei):
        _fail("organization.sam_uei", "must contain exactly 12 uppercase alphanumeric characters")
    return {
        "legal_name": _optional_text(organization["legal_name"], "organization.legal_name", max_length=300),
        "legal_form": _optional_text(organization["legal_form"], "organization.legal_form", max_length=200),
        "sam_uei": sam_uei,
        "marion_county_vendor_profile": _validate_evidence(
            organization["marion_county_vendor_profile"], "organization.marion_county_vendor_profile"
        ),
        "liability_insurance": _validate_evidence(
            organization["liability_insurance"], "organization.liability_insurance"
        ),
        "debarment_and_suspension": _validate_evidence(
            organization["debarment_and_suspension"], "organization.debarment_and_suspension"
        ),
        "title_vi_compliance": _validate_evidence(
            organization["title_vi_compliance"], "organization.title_vi_compliance"
        ),
    }


def validate_team(value: Any) -> dict[str, Any]:
    team = _require_mapping(value, "team")
    _require_exact_keys(team, "team", ("project_manager", "staff", "partners"))
    project_manager_raw = team["project_manager"]
    project_manager = None if project_manager_raw is None else _validate_person(project_manager_raw, "team.project_manager")
    staff_values = _require_list(team["staff"], "team.staff", max_items=50)
    staff = [_validate_person(item, f"team.staff[{i}]") for i, item in enumerate(staff_values)]
    partner_values = _require_list(team["partners"], "team.partners", max_items=50)
    partners = [_validate_partner(item, f"team.partners[{i}]") for i, item in enumerate(partner_values)]
    person_names = ([project_manager["name"]] if project_manager else []) + [item["name"] for item in staff]
    if len(set(person_names)) != len(person_names):
        _fail("team", "person names must be unique")
    partner_names = [item["name"] for item in partners]
    if len(set(partner_names)) != len(partner_names):
        _fail("team.partners", "partner names must be unique")
    return {"project_manager": project_manager, "staff": staff, "partners": partners}


def validate_projects(value: Any) -> list[dict[str, Any]]:
    project_values = _require_list(value, "projects", max_items=50)
    projects = [_validate_project(item, f"projects[{i}]") for i, item in enumerate(project_values)]
    project_names = [item["name"] for item in projects]
    if len(set(project_names)) != len(project_names):
        _fail("projects", "project names must be unique")
    return projects


def validate_capabilities(value: Any) -> dict[str, Any]:
    capabilities = _require_mapping(value, "capabilities")
    _require_exact_keys(capabilities, "capabilities", CAPABILITY_KEYS)
    return {
        key: _validate_evidence(capabilities[key], f"capabilities.{key}")
        for key in CAPABILITY_KEYS
    }


def validate_documents(value: Any) -> dict[str, Any]:
    documents = _require_mapping(value, "documents")
    _require_exact_keys(documents, "documents", DOCUMENT_KEYS)
    return {
        key: _validate_evidence(documents[key], f"documents.{key}")
        for key in DOCUMENT_KEYS
    }
