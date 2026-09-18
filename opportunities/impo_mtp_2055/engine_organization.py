"""Organization and team gates for IMPO MTP 2055 readiness."""

from __future__ import annotations

from typing import Any

from .engine_core import _evidence_row, _row

def _organization_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    organization = packet["organization"]
    rows: list[dict[str, Any]] = []
    legal_ready = organization["legal_name"] is not None and organization["legal_form"] is not None
    rows.append(
        _row(
            "ORG-001",
            "SUBMISSION",
            "Truthful lead-firm identity and legal form",
            "READY" if legal_ready else "BLOCKED",
            "Lead-firm legal identity and form are present."
            if legal_ready
            else "Lead-firm legal name and legal form are both required.",
            blocking=not legal_ready,
            evidence_reference=organization["legal_name"] if legal_ready else None,
        )
    )
    uei_ready = organization["sam_uei"] is not None
    rows.append(
        _row(
            "ORG-002",
            "SUBMISSION",
            "SAM.gov Unique Entity ID",
            "READY" if uei_ready else "BLOCKED",
            "A syntactically valid UEI is present."
            if uei_ready
            else "Form A requests a SAM.gov Unique Entity ID; none is verified.",
            blocking=not uei_ready,
            evidence_reference=organization["sam_uei"] if uei_ready else None,
        )
    )
    rows.append(
        _evidence_row(
            "ORG-003",
            "SUBMISSION",
            "Indianapolis/Marion County vendor-profile evidence",
            organization["marion_county_vendor_profile"],
            mandatory=False,
            missing_disposition="AT_RISK",
            missing_reason="The response asks for vendor-profile evidence; the RFP says registration may be completed if selected, so this is an explicit submission risk rather than invented registration authority.",
        )
    )
    rows.append(
        _evidence_row(
            "ORG-004",
            "AWARD",
            "Liability-insurance capacity",
            organization["liability_insurance"],
            mandatory=False,
            missing_disposition="DEFERRED",
            missing_reason="Insurance is an award/contract condition; evidence must be obtained before representing capacity or accepting an award.",
        )
    )
    rows.append(
        _evidence_row(
            "ORG-005",
            "SUBMISSION",
            "Debarment and suspension certification",
            organization["debarment_and_suspension"],
        )
    )
    rows.append(
        _evidence_row(
            "ORG-006",
            "SUBMISSION",
            "Title VI and federal-assurance compliance",
            organization["title_vi_compliance"],
        )
    )
    return rows


def _team_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    team = packet["team"]
    rows: list[dict[str, Any]] = []
    pm = team["project_manager"]
    if pm is None:
        rows.append(
            _row(
                "TEAM-001",
                "SUBMISSION",
                "Named project manager",
                "BLOCKED",
                "No project manager is named.",
                blocking=True,
            )
        )
    else:
        allocation_ok = pm["allocation_percent"] > 0
        resume_ok = pm["resume_evidence"]["state"] == "VERIFIED"
        ready = allocation_ok and resume_ok
        reasons = []
        if not allocation_ok:
            reasons.append("allocation_percent must be greater than zero")
        if not resume_ok:
            reasons.append("resume evidence is not verified")
        rows.append(
            _row(
                "TEAM-001",
                "SUBMISSION",
                "Named project manager",
                "READY" if ready else "BLOCKED",
                "Project manager, allocation, and resume evidence are present."
                if ready
                else "; ".join(reasons),
                blocking=not ready,
                evidence_reference=pm["resume_evidence"]["reference"] if resume_ok else None,
            )
        )

    if not team["staff"]:
        rows.append(
            _row(
                "TEAM-002",
                "SUBMISSION",
                "Named supporting staff",
                "BLOCKED",
                "At least one supporting staff member is required to substantiate a project team.",
                blocking=True,
            )
        )
    else:
        bad_staff = [
            person["name"]
            for person in team["staff"]
            if person["allocation_percent"] <= 0
            or person["resume_evidence"]["state"] != "VERIFIED"
        ]
        rows.append(
            _row(
                "TEAM-002",
                "SUBMISSION",
                "Named supporting staff",
                "READY" if not bad_staff else "BLOCKED",
                f"{len(team['staff'])} supporting staff have verified resumes and nonzero allocations."
                if not bad_staff
                else "Missing verified resume/allocation for: " + ", ".join(bad_staff),
                blocking=bool(bad_staff),
            )
        )

    bad_partners = [
        partner["name"]
        for partner in team["partners"]
        if partner["commitment_evidence"]["state"] != "VERIFIED"
        or not partner["approved_for_disclosure"]
    ]
    rows.append(
        _row(
            "TEAM-003",
            "SUBMISSION",
            "Truthful partnering-vendor commitments",
            "READY" if not bad_partners else "BLOCKED",
            f"{len(team['partners'])} disclosed partner(s) have verified commitments and disclosure approval."
            if not bad_partners
            else "Partner commitments/disclosure approval are incomplete for: " + ", ".join(bad_partners),
            blocking=bool(bad_partners),
        )
    )
    return rows


