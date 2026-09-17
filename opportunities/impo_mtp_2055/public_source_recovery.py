#!/usr/bin/env python3
"""Validate the Sep17 IMPO public-source recovery without fabricating byte custody."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from typing import Any, Mapping, Sequence

SCHEMA = "impo-mtp2055-public-source-snapshot/v1"
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class SourceRecoveryError(ValueError):
    pass


def _ts(value: Any, field: str) -> dt.datetime:
    if not isinstance(value, str) or not value.strip():
        raise SourceRecoveryError(f"{field} must be text")
    raw = value.strip()
    raw = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        out = dt.datetime.fromisoformat(raw)
    except ValueError as exc:
        raise SourceRecoveryError(f"{field} invalid") from exc
    if out.tzinfo is None or out.utcoffset() is None:
        raise SourceRecoveryError(f"{field} timezone required")
    return out.astimezone(dt.timezone.utc)


def _bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise SourceRecoveryError(f"{field} must be boolean")
    return value


def _int(value: Any, field: str, lo: int = 0) -> int:
    if type(value) is not int or value < lo:
        raise SourceRecoveryError(f"{field} must be integer >= {lo}")
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def validate_snapshot(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SourceRecoveryError("snapshot must be object")
    if value.get("schema") != SCHEMA:
        raise SourceRecoveryError("schema mismatch")
    _ts(value.get("checked_at"), "checked_at")
    if value.get("procurement_page_state") != "OFFICIAL_CURRENT":
        raise SourceRecoveryError("official current procurement page required")
    if not _bool(value.get("rfp_public_readable"), "rfp_public_readable"):
        raise SourceRecoveryError("public RFP must be readable")
    if _int(value.get("rfp_page_count"), "rfp_page_count", 1) != 34:
        raise SourceRecoveryError("expected 34-page source generation")
    retained = _bool(value.get("raw_pdf_bytes_retained"), "raw_pdf_bytes_retained")
    raw_hash = value.get("raw_pdf_sha256")
    if retained:
        if not isinstance(raw_hash, str) or not DIGEST_RE.fullmatch(raw_hash):
            raise SourceRecoveryError("retained bytes require exact sha256")
    elif raw_hash is not None:
        raise SourceRecoveryError("unretained raw bytes must not claim sha256")
    q = value.get("questions_addendum")
    if not isinstance(q, Mapping) or q.get("state") not in {"NOT_YET_POSTED", "POSTED_RETAINED"}:
        raise SourceRecoveryError("questions_addendum state invalid")
    facts = value.get("controlling_facts")
    if not isinstance(facts, Mapping):
        raise SourceRecoveryError("controlling_facts required")
    released = _ts(facts.get("released_at"), "released_at")
    questions = _ts(facts.get("questions_due_at"), "questions_due_at")
    prebid = _ts(facts.get("prebid_at"), "prebid_at")
    due = _ts(facts.get("proposal_due_at"), "proposal_due_at")
    if not released < questions < prebid < due:
        raise SourceRecoveryError("controlling schedule order invalid")
    if _int(facts.get("budget_cap_minor"), "budget_cap_minor", 1) != 21500000:
        raise SourceRecoveryError("unexpected budget cap")
    if facts.get("currency") != "USD":
        raise SourceRecoveryError("currency must be USD")
    if facts.get("response_route") != "email:procurement@indympo.gov" or facts.get("response_subject") != "MTP 2055":
        raise SourceRecoveryError("response route/subject drift")
    if _int(facts.get("qualifications_page_limit"), "qualifications_page_limit", 1) != 16:
        raise SourceRecoveryError("page-limit drift")
    pts = facts.get("evaluation_points")
    if pts != {"project_approach": 35, "project_team": 35, "past_project_experience": 30}:
        raise SourceRecoveryError("evaluation weights drift")
    if not _bool(facts.get("subconsultants_permitted"), "subconsultants_permitted"):
        raise SourceRecoveryError("subconsultant permission expected")
    auth = value.get("external_authority")
    if not isinstance(auth, Mapping) or not auth or any(v is not False for v in auth.values()):
        raise SourceRecoveryError("external authority must remain all-false")
    claimed = value.get("authority_field_digest_sha256")
    if not isinstance(claimed, str) or not DIGEST_RE.fullmatch(claimed):
        raise SourceRecoveryError("authority digest required")
    detached = dict(value)
    detached.pop("authority_field_digest_sha256", None)
    expected = hashlib.sha256(_canonical(detached)).hexdigest()
    if claimed != expected:
        raise SourceRecoveryError("authority digest mismatch")
    return dict(value)


def compile_recovery(value: Mapping[str, Any]) -> dict[str, Any]:
    snap = validate_snapshot(value)
    q = snap["questions_addendum"]["state"]
    pending = []
    if not snap["raw_pdf_bytes_retained"]:
        pending.append("RAW_PDF_BYTES_AND_SHA256_NOT_RETAINED")
    if q != "POSTED_RETAINED":
        pending.append("QUESTIONS_ADDENDUM_NOT_YET_POSTED_OR_RETAINED")
    return {
        "schema": "impo-mtp2055-public-source-recovery/v1",
        "checked_at": snap["checked_at"],
        "base_rfp_public_source_recovered": True,
        "source_fact_authority_bound": True,
        "raw_pdf_byte_custody": snap["raw_pdf_bytes_retained"],
        "questions_addendum_state": q,
        "pending_source_items": pending,
        "next_public_source_event": "2026-09-23 questions addendum publication / official-page refresh",
        "external_action_authorized": False,
        "authority_field_digest_sha256": snap["authority_field_digest_sha256"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input")
    args = ap.parse_args(argv)
    try:
        with open(args.input, encoding="utf-8") as handle:
            out = compile_recovery(json.load(handle))
    except (OSError, json.JSONDecodeError, SourceRecoveryError) as exc:
        print(f"impo-source-recovery-error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(out, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
