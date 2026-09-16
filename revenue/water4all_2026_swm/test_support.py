from __future__ import annotations

import copy
import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from revenue.water4all_2026_swm import cli
from revenue.water4all_2026_swm.engine import (
    ReadinessError,
    canonical_bytes,
    compile_at,
    compile_current,
    compile_historical,
    render_owner_markdown,
    seal_source,
    sha256_hex,
    strict_json_loads,
    verify_bundle,
)

UTC = dt.timezone.utc
T0 = dt.datetime(2026, 9, 14, 4, 0, 0, tzinfo=UTC)
HERE = Path(__file__).resolve().parent


def load_json(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def base_valid():
    example = load_json("example_input.json")
    sources = copy.deepcopy(example["official_sources"])
    for source in sources:
        source["observed_at"] = "2026-09-14T03:40:00Z"
        source["preproposal_deadline_at"] = "2026-11-10T14:00:00Z"
        source.update(seal_source(source))

    members = []
    for partner_id, country, coordinator in [
        ("p1", "DE", True),
        ("p2", "ES", False),
        ("p3", "NL", False),
    ]:
        members.append(
            {
                "partner_id": partner_id,
                "organization_label": "Verified %s entity" % partner_id,
                "country_code": country,
                "role": "FUNDED_PARTNER",
                "eu_or_associated": True,
                "participating_fpo_country": True,
                "fpo_eligibility_verified": True,
                "undersubscribed_fpo": False,
                "legal_entity_verified": True,
                "pic_verified": True,
                "self_funding_commitment_verified": False,
                "coordinator": coordinator,
                "person_months_milli": 10000,
                "synthetic_placeholder": False,
                "water4all_partnership_beneficiary": False,
            }
        )
    evidence = [
        {
            "evidence_id": "ev1",
            "repo_full_name": "owner/repo",
            "commit_sha": "a" * 40,
            "path": "src/water.py",
            "content_sha256": "b" * 64,
            "observed_at": "2026-09-14T03:45:00Z",
            "verified": True,
            "publicability": "PUBLIC_DESCRIPTOR",
            "capability_tags": [
                "water_monitoring",
                "multimodal_data_integration",
                "uncertainty_quantification",
                "decision_support",
                "provenance_receipts",
            ],
        }
    ]
    return {
        "schema": "water4all-2026-readiness-input/v1",
        "official_sources": sources,
        "consortium": {"members": members},
        "applicant": {
            "applicant_id": "p1",
            "organization_label": "Verified p1 entity",
            "country_code": "DE",
            "intended_role": "FUNDED_PARTNER",
            "legal_entity_verified": True,
            "pic_verified": True,
            "paid_role_authority_verified": False,
            "subcontract_rule_verified": False,
            "synthetic_placeholder": False,
        },
        "concept": {
            "concept_title": "Verified monitoring concept",
            "topic_ids": [1],
            "status": "PROPOSED_NOT_ACCEPTED",
        },
        "technical_evidence": evidence,
        "partner_shortlist": copy.deepcopy(example["partner_shortlist"]),
        "commercial": {
            "status": "OWNER_APPROVED_INTERNAL",
            "paid_path": "OWNER_APPROVED_PARTICIPATION_PATH",
            "owner_approved_internal": True,
            "accepted_external": False,
            "price_quote_authorized": False,
            "self_funding_authorized": False,
            "consortium_commitment_authorized": False,
        },
    }


def compile_valid(value=None, mode="HISTORICAL", when=T0):
    if mode != "HISTORICAL":
        raise ValueError("compile_valid is historical-only; use compile_current_at")
    return compile_at(base_valid() if value is None else value, when, "HISTORICAL")


def compile_current_at(value=None, when=T0):
    with mock.patch("revenue.water4all_2026_swm.engine.utc_now", return_value=when):
        return compile_current(base_valid() if value is None else value)


def reason_codes(bundle):
    return {item["code"] for item in bundle["packet"]["decision"]["reasons"]}


def reseal(source):
    source.update(seal_source(source))
