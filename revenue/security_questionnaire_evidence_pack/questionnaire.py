#!/usr/bin/env python3
"""Deterministic, evidence-bound enterprise security questionnaire compiler."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from typing import Any

SCHEMA = "security-questionnaire-evidence-v1"
REPORT_SCHEMA = "security-questionnaire-report-v1"
MAX_EVIDENCE = 300
MAX_QUESTIONS = 150
MAX_ARTIFACT_BYTES = 2_000_000
ID_RE = re.compile(r"^[A-Z][A-Z0-9_.-]{0,63}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
STATUSES = (
    "SUPPORTED",
    "PARTIAL",
    "HOLD_MISSING_EVIDENCE",
    "HOLD_STALE_EVIDENCE",
    "NOT_APPLICABLE",
)
AUTHORITY = {
    "certifies_compliance": False,
    "attests_soc2": False,
    "attests_hipaa": False,
    "buyer_contact_authorized": False,
    "contract_acceptance_authorized": False,
    "payment_authorized": False,
    "revenue_recognition_authorized": False,
}
OFFER = {
    "fixed_sprint_usd_cents": 1_500_000,
    "optional_quarterly_refresh_usd_cents": 200_000,
    "commercial_state": "PROPOSED_NOT_ACCEPTED",
}


class PackError(ValueError):
    """Closed validation/verification failure for this evidence pack."""


def _reject_float(value: str) -> None:
    raise PackError(f"floating-point JSON is not allowed: {value}")


def _reject_constant(value: str) -> None:
    raise PackError(f"non-finite JSON is not allowed: {value}")


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise PackError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def loads_strict(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PackError("input must be UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except PackError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise PackError(f"invalid JSON: {exc}") from exc
