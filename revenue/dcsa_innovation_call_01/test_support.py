from __future__ import annotations

import copy
import datetime as dt
import hashlib
import inspect
import io
import json
import os
import pathlib
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from revenue.dcsa_innovation_call_01 import acceptance, concept, gate, strict
from revenue.dcsa_innovation_call_01.cli import build_parser, main

UTC = dt.timezone.utc
BASE_NOW = dt.datetime(2026, 9, 14, 5, 0, 0, tzinfo=UTC)


def candidate() -> dict:
    return {
        "schema": gate.CANDIDATE_SCHEMA,
        "subject_id": "subject-1",
        "operation_id": "DCSA-INNOVATION-CALL-01-TEST",
        "route_preference": "AUTO",
        "concept_title": "Mission Access Fabric",
        "declared_capabilities": list(gate.REQUIRED_CAPABILITIES),
        "background_ip": ["Evidence compiler"],
        "third_party_dependencies": ["Government identity provider"],
        "risks": ["Sustainment transition"],
        "question_drafts": ["Which identity providers are in scope?"],
        "rom_state": "OWNER_APPROVED",
    }


def source(*, complete: bool = True, observed_at: str = "2026-09-14T04:45:00Z") -> dict:
    role_map = {
        "innovation_call_pdf": "CONTROLLING_CALL",
        "general_solicitation_pdf": "CONTROLLING_GENERAL_SOLICITATION",
        "concept_paper_template": "MANDATORY_TEMPLATE",
        "ecosystem_style_guide": "DESIGN_REFERENCE",
    }
    rows = []
    for index, document_id in enumerate(gate.REQUIRED_DOCUMENTS):
        rows.append(
            {
                "document_id": document_id,
                "role": role_map[document_id],
                "authority": "OFFICIAL_FIRST_PARTY",
                "official_url": f"https://sam.gov/{document_id}",
                "mirror_url": f"https://mirror.invalid/{document_id}",
                "posted_at": "2026-09-10T14:28:00Z",
                "retained_bytes": complete,
                "sha256": hashlib.sha256(document_id.encode()).hexdigest() if complete else None,
            }
        )
    return {
        "schema": gate.SOURCE_SCHEMA,
        "notice_id": gate.NOTICE_ID,
        "general_solicitation_id": gate.GENERAL_SOLICITATION_ID,
        "observed_at": observed_at,
        "documents": rows,
    }


def evidence(state: str = "VERIFIED", name: str = "evidence") -> dict:
    if state == "VERIFIED":
        return {
            "state": state,
            "evidence_ref": f"retained:{name}",
            "evidence_sha256": hashlib.sha256(name.encode()).hexdigest(),
        }
    return {"state": state, "evidence_ref": None, "evidence_sha256": None}


def authority(
    source_value: dict,
    *,
    direct: bool = True,
    team: bool = True,
    subject_id: str = "subject-1",
    issued_at: str = "2026-09-14T04:40:00Z",
    valid_until: str = "2026-09-14T12:00:00Z",
    rom: bool = True,
    direct_approved: bool = True,
    team_approved: bool = True,
) -> dict:
    source_norm = gate.normalize_source_ledger(source_value)
    direct_state = "VERIFIED" if direct else "NOT_HELD"
    return {
        "schema": gate.AUTHORITY_SCHEMA,
        "generation": 7,
        "issued_at": issued_at,
        "valid_until": valid_until,
        "subject_id": subject_id,
        "source_generation_sha256": source_norm["source_generation_sha256"],
        "direct_clearance": {
            "active_top_secret_fcl": evidence(direct_state, "fcl")
        },
        "personnel": {
            "all_assigned_us_citizens": evidence(direct_state, "citizenship"),
            "all_assigned_interim_secret_or_higher": evidence(direct_state, "personnel-clearance"),
            "privileged_users_t5_or_ts_start": evidence(direct_state, "t5"),
            "cac_operability": evidence(direct_state, "cac"),
        },
        "ota_eligibility": {
            "direct_path": evidence(direct_state, "direct-ota"),
            "teaming_prime_path": evidence("VERIFIED" if team else "UNVERIFIED", "team-ota"),
        },
        "capability_evidence": [
            {"capability": cap, **evidence("VERIFIED", cap)}
            for cap in gate.REQUIRED_CAPABILITIES
        ],
        "owner_decisions": {
            "direct_route_approved": direct_approved,
            "teaming_route_approved": team_approved,
            "rom_approved": rom,
            "external_contact_approved": False,
            "external_submission_approved": False,
        },
    }


def floor(authority_value: dict) -> dict:
    return {
        "schema": gate.FLOOR_SCHEMA,
        "generation": authority_value["generation"],
        "authority_sha256": gate.authority_sha256(authority_value),
        "source_generation_sha256": authority_value["source_generation_sha256"],
    }


def compile_at(
    candidate_value: dict | None = None,
    source_value: dict | None = None,
    authority_value: dict | None = None,
    floor_value: dict | None = None,
    *,
    now: dt.datetime = BASE_NOW,
    mode: str = "CURRENT",
) -> dict:
    c = candidate() if candidate_value is None else candidate_value
    s = source() if source_value is None else source_value
    a = authority(s) if authority_value is None else authority_value
    f = floor(a) if floor_value is None else floor_value
    return gate._compile_at(c, s, a, f, now=now, mode=mode)

