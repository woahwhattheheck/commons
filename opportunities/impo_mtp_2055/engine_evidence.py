"""Experience, capability, document, commercial, and authority gates."""

from __future__ import annotations

from typing import Any

from .engine_core import _evidence_row, _row
from .schema import CAPABILITY_KEYS, DOCUMENT_KEYS

def _project_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    projects = packet["projects"]
    qualifying = [
        project
        for project in projects
        if not project["is_impo_client"] and project["evidence"]["state"] == "VERIFIED"
    ]
    rows: list[dict[str, Any]] = []
    if len(qualifying) >= 3:
        rows.append(
            _row(
                "EXP-001",
                "SUBMISSION",
                "Three relevant, verifiable project examples",
                "READY",
                f"{len(qualifying)} non-IMPO project examples have verified evidence.",
                blocking=False,
            )
        )
    else:
        rows.append(
            _row(
                "EXP-001",
                "SUBMISSION",
                "Three relevant, verifiable project examples",
                "BLOCKED",
                f"Only {len(qualifying)} qualifying non-IMPO examples are verified; at least three are required.",
                blocking=True,
            )
        )
    unique_reference_emails = {project["reference_email"].casefold() for project in qualifying}
    references_ready = len(qualifying) >= 3 and len(unique_reference_emails) >= 3
    rows.append(
        _row(
            "EXP-002",
            "SUBMISSION",
            "Three project-manager-specific external references",
            "READY" if references_ready else "BLOCKED",
            "At least three distinct non-IMPO reference routes are verified."
            if references_ready
            else "Three distinct, project-manager-specific, non-IMPO reference routes are not yet verified.",
            blocking=not references_ready,
        )
    )
    return rows


def _capability_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    titles = {
        "metropolitan_transportation_planning": "Metropolitan transportation-plan development",
        "federal_regulatory_compliance": "Federal metropolitan-planning and Title 23 compliance",
        "statistically_valid_regional_survey": "Statistically valid regional survey design and weighting",
        "public_and_stakeholder_engagement": "Public, stakeholder, committee, and jurisdiction engagement",
        "travel_demand_and_scenario_analysis": "Travel-demand, land-use, and scenario analysis",
        "project_scoring_and_fiscal_constraint": "Project scoring and fiscal-constraint analysis",
        "gis_and_editable_source_delivery": "GIS, scripts, and editable source-material delivery",
        "web_accessible_publication": "Web-accessible public documents and materials",
        "performance_measurement_and_dashboards": "Performance measures, KPIs, and dashboard integration",
        "quality_assurance": "Documented project QA/QC",
    }
    rows = []
    for index, key in enumerate(CAPABILITY_KEYS, start=1):
        rows.append(
            _evidence_row(
                f"CAP-{index:03d}",
                "SUBMISSION",
                titles[key],
                packet["capabilities"][key],
            )
        )
    return rows


def _document_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    titles = {
        "cover_letter": "One-page cover letter",
        "firm_overview": "One-to-two-page firm overview",
        "project_approach": "One-to-four-page project approach",
        "project_team": "Maximum two-page project-team section",
        "project_sheets": "Maximum three-page relevant-project sheets",
        "resumes": "Maximum four-page key-staff resumes",
        "form_a": "Completed Form A",
        "form_b": "Completed Form B",
        "form_c": "Completed Form C",
        "vendor_profile_evidence": "Vendor-profile attachment or truthful selected-stage statement",
        "signed_questions_addendum": "Signed questions addendum",
        "separate_quote": "Separate task/rate/hour quote PDF",
        "title_vi_assurances": "Title VI assurances attachment",
    }
    rows = []
    for index, key in enumerate(DOCUMENT_KEYS, start=1):
        mandatory = key != "vendor_profile_evidence"
        rows.append(
            _evidence_row(
                f"DOC-{index:03d}",
                "SUBMISSION",
                titles[key],
                packet["documents"][key],
                mandatory=mandatory,
                missing_disposition="AT_RISK" if not mandatory else None,
                missing_reason=(
                    "The packet must truthfully disclose whether a vendor profile exists and preserve the selected-stage registration condition."
                    if not mandatory
                    else None
                ),
            )
        )
    return rows


def _pricing_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    pricing = packet["pricing"]
    cap = packet["opportunity"]["budget_cap_minor"]
    total = pricing["stated_total_minor"]
    rows: list[dict[str, Any]] = []
    priced = bool(pricing["tasks"]) and total > 0 and any(
        task["subtotal_minor"] > 0 for task in pricing["tasks"]
    )
    rows.append(
        _row(
            "COM-001",
            "COMMERCIAL",
            "Task-level rate/hour/cost schedule",
            "READY" if priced else "BLOCKED",
            f"{len(pricing['tasks'])} task row(s) reconcile exactly to a positive stated total."
            if priced
            else "A positive, task-level rate/hour/cost schedule is not present.",
            blocking=not priced,
        )
    )
    within_cap = total <= cap
    rows.append(
        _row(
            "COM-002",
            "COMMERCIAL",
            "Total does not exceed the $215,000 NTE ceiling",
            "READY" if within_cap else "BLOCKED",
            f"Stated total {total} minor units is within cap {cap}."
            if within_cap
            else f"Stated total {total} minor units exceeds cap {cap}.",
            blocking=not within_cap,
        )
    )
    rows.append(
        _evidence_row(
            "COM-003",
            "COMMERCIAL",
            "Commercial approval of rates, hours, and total",
            pricing["commercial_approval"],
        )
    )
    return rows


def _authority_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    authority = packet["authority"]
    rows: list[dict[str, Any]] = []
    required = {
        "sign_forms": "Authority to sign proposal forms",
        "commit_pricing": "Authority to commit proposal pricing",
        "submit_proposal": "Authority to transmit the final proposal",
    }
    for index, (key, title) in enumerate(required.items(), start=1):
        allowed = authority[key]
        rows.append(
            _row(
                f"AUTH-{index:03d}",
                "AUTHORITY",
                title,
                "READY" if allowed else "BLOCKED",
                f"Explicit approval recorded by {authority['approved_by']}."
                if allowed
                else "No explicit owner approval is recorded; the compiler has no external authority.",
                blocking=not allowed,
                evidence_reference=authority["approval_reference"] if allowed else None,
            )
        )
    return rows


