from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from . import cli
from .engine import PacketVerificationError, compile_packet, verify_packet
from .schema import OpportunityInputError, validate_input

ROOT = Path(__file__).resolve().parent


def evidence(reference: str, note: str = "Verified for test fixture.") -> dict[str, object]:
    return {"state": "VERIFIED", "reference": reference, "note": note}


def load_owner_fixture() -> dict:
    return json.loads((ROOT / "input.owner-review.json").read_text(encoding="utf-8"))


def ready_fixture(*, authority: bool = False) -> dict:
    value = load_owner_fixture()
    value["opportunity"]["source_sha256"] = "a" * 64
    value["source_checks"]["base_rfp_bytes_verified"] = True
    value["source_checks"]["last_checked_at"] = value["as_of"]
    value["source_checks"]["questions_addendum"] = evidence("questions-addendum-sha256:" + "b" * 64)
    value["organization"].update(
        {
            "legal_name": "Example Planning Systems LLC",
            "legal_form": "Limited liability company",
            "sam_uei": "ABCDEF123456",
            "marion_county_vendor_profile": evidence("vendor-profile:VP-123"),
            "liability_insurance": evidence("broker-letter:2026-09-13"),
            "debarment_and_suspension": evidence("sam-status:2026-09-13"),
            "title_vi_compliance": evidence("signed-title-vi-assurances.pdf"),
        }
    )
    value["team"] = {
        "project_manager": {
            "name": "Avery Project",
            "role": "Project manager and MTP lead",
            "years_relevant": 15,
            "allocation_percent": 35,
            "resume_evidence": evidence("resume:avery-project"),
        },
        "staff": [
            {
                "name": "Morgan Model",
                "role": "Travel demand and scenario lead",
                "years_relevant": 11,
                "allocation_percent": 25,
                "resume_evidence": evidence("resume:morgan-model"),
            },
            {
                "name": "Riley Engage",
                "role": "Engagement and survey lead",
                "years_relevant": 10,
                "allocation_percent": 25,
                "resume_evidence": evidence("resume:riley-engage"),
            },
        ],
        "partners": [
            {
                "name": "Survey Methods Cooperative",
                "role": "Sampling, weighting, and survey quality",
                "commitment_evidence": evidence("signed-teaming-letter:survey-methods"),
                "approved_for_disclosure": True,
            }
        ],
    }
    value["projects"] = [
        {
            "name": "Regional Mobility Plan Alpha",
            "client": "Alpha Regional Council",
            "is_impo_client": False,
            "staff_roles": ["Avery Project - PM", "Morgan Model - modeling"],
            "relevance": "Long-range transportation plan, scoring, and model integration.",
            "reference_name": "Alex Alpha",
            "reference_email": "alex.alpha@example.org",
            "evidence": evidence("project-sheet:alpha"),
        },
        {
            "name": "Metro Investment Framework Beta",
            "client": "Beta Planning Commission",
            "is_impo_client": False,
            "staff_roles": ["Avery Project - PM", "Riley Engage - engagement"],
            "relevance": "Regional engagement, performance framework, and fiscal constraint.",
            "reference_name": "Blair Beta",
            "reference_email": "blair.beta@example.org",
            "evidence": evidence("project-sheet:beta"),
        },
        {
            "name": "Accessible Plan Gamma",
            "client": "Gamma Council of Governments",
            "is_impo_client": False,
            "staff_roles": ["Riley Engage - engagement", "Morgan Model - analysis"],
            "relevance": "Accessible public deliverables, survey work, GIS, and implementation plan.",
            "reference_name": "Gray Gamma",
            "reference_email": "gray.gamma@example.org",
            "evidence": evidence("project-sheet:gamma"),
        },
    ]
    for key in value["capabilities"]:
        value["capabilities"][key] = evidence(f"capability:{key}")
    for key in value["documents"]:
        value["documents"][key] = evidence(f"document:{key}")
    value["pricing"] = {
        "tasks": [
            {"id": "T01", "name": "Project management and regulatory framework", "rate_minor": 20000, "hours": 150, "other_cost_minor": 0},
            {"id": "T02", "name": "Regional conditions and performance framework", "rate_minor": 18000, "hours": 200, "other_cost_minor": 0},
            {"id": "T03", "name": "Engagement and statistically valid survey", "rate_minor": 17500, "hours": 250, "other_cost_minor": 500000},
            {"id": "T04", "name": "Scenario and travel-model integration", "rate_minor": 20000, "hours": 200, "other_cost_minor": 0},
            {"id": "T05", "name": "Project scoring and fiscal constraint", "rate_minor": 19000, "hours": 150, "other_cost_minor": 0},
            {"id": "T06", "name": "Implementation, public review, and final delivery", "rate_minor": 17000, "hours": 100, "other_cost_minor": 0},
        ],
        "stated_total_minor": 20025000,
        "commercial_approval": evidence("owner-price-approval:fixture"),
    }
    if authority:
        value["authority"]["sign_forms"] = True
        value["authority"]["commit_pricing"] = True
        value["authority"]["submit_proposal"] = True
        value["authority"]["approved_by"] = "Authorized Owner"
        value["authority"]["approval_reference"] = "owner-approval:fixture"
    return value


