from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
from typing import Any

SCHEMA = "tjlabs.mcc-1017-27-pursuit/v1"
REQUIRED_PACKAGE_FILES = (
    "Public Purchase - Vendor Response Instructions.docx",
    "IFB 1017-27 Pricing Form.docx",
    "1017-27 Bid Package (4) (4).docx",
)
EXTERNAL_AUTHORITY_KEYS = (
    "buyer_contact",
    "partner_contact",
    "provider_mutation",
    "proposal_submission",
    "signature",
    "award",
    "invoice",
    "payment",
    "cash",
    "revenue",
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PursuitError(ValueError):
    pass


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PursuitError(f"state is not canonical JSON: {exc}") from exc


def _parse_utc(value: str, field: str) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise PursuitError(f"{field} must be an RFC3339 UTC timestamp ending in Z")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise PursuitError(f"{field} is not a valid timestamp") from exc
    return parsed


def _sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise PursuitError(f"{field} must be a lowercase SHA-256 hex digest")
    return value


def _require_false_external_authority(state: dict[str, Any]) -> None:
    authority = state.get("external_authority")
    if not isinstance(authority, dict):
        raise PursuitError("external_authority must be an object")
    unknown = set(authority) - set(EXTERNAL_AUTHORITY_KEYS)
    if unknown:
        raise PursuitError(f"unknown external authority keys: {sorted(unknown)}")
    missing = set(EXTERNAL_AUTHORITY_KEYS) - set(authority)
    if missing:
        raise PursuitError(f"missing external authority keys: {sorted(missing)}")
    for key in EXTERNAL_AUTHORITY_KEYS:
        if authority[key] is not False:
            raise PursuitError(f"external_authority.{key} must remain false")


def _validate_secondary(state: dict[str, Any]) -> None:
    discovery = state.get("secondary_discovery")
    if not isinstance(discovery, dict):
        raise PursuitError("secondary_discovery must be an object")
    sources = discovery.get("sources")
    if not isinstance(sources, list) or not sources:
        raise PursuitError("secondary_discovery.sources must be a non-empty list")
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise PursuitError(f"secondary_discovery.sources[{index}] must be an object")
        if source.get("authority") != "secondary":
            raise PursuitError("secondary discovery may never be marked controlling")
        if not isinstance(source.get("url"), str) or not source["url"].startswith("https://"):
            raise PursuitError("secondary source URL must be HTTPS")


def _validate_documents(authority: dict[str, Any]) -> tuple[bool, list[str]]:
    documents = authority.get("documents")
    if not isinstance(documents, list):
        raise PursuitError("buyer_authority.documents must be a list")
    seen: set[str] = set()
    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            raise PursuitError(f"buyer_authority.documents[{index}] must be an object")
        name = document.get("name")
        if not isinstance(name, str) or not name:
            raise PursuitError("buyer document name must be non-empty")
        if name in seen:
            raise PursuitError(f"duplicate buyer document name: {name}")
        seen.add(name)
        _sha256(document.get("sha256"), f"buyer document {name}.sha256")
        if document.get("authority") != "controlling":
            raise PursuitError(f"buyer document {name} must be controlling")
        if document.get("source_kind") != "buyer_or_buyer_portal":
            raise PursuitError(f"buyer document {name} source_kind is not buyer authority")
        url = document.get("source_url")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise PursuitError(f"buyer document {name} source_url must be HTTPS")
        _parse_utc(document.get("captured_at_utc"), f"buyer document {name}.captured_at_utc")
    missing = [name for name in REQUIRED_PACKAGE_FILES if name not in seen]
    declared = authority.get("package_complete")
    if not isinstance(declared, bool):
        raise PursuitError("buyer_authority.package_complete must be boolean")
    complete = declared and not missing
    if declared and missing:
        raise PursuitError(f"buyer package declared complete but missing: {missing}")
    return complete, missing


def _prime_evidence_ok(state: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    prime = state.get("prime_qualification")
    if not isinstance(prime, dict):
        raise PursuitError("prime_qualification must be an object")
    years = prime.get("verified_relevant_experience_years")
    if not _is_int(years) or years < 0:
        raise PursuitError("verified_relevant_experience_years must be a non-negative integer")
    refs = prime.get("verified_higher_education_references")
    if not isinstance(refs, list):
        raise PursuitError("verified_higher_education_references must be a list")
    valid_refs = 0
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict):
            raise PursuitError(f"reference[{index}] must be an object")
        if ref.get("verified_higher_education") is True:
            _sha256(ref.get("evidence_sha256"), f"reference[{index}].evidence_sha256")
            institution = ref.get("institution")
            if not isinstance(institution, str) or not institution:
                raise PursuitError(f"reference[{index}].institution must be non-empty")
            valid_refs += 1
    return years >= 5 and valid_refs >= 3, {
        "verified_relevant_experience_years": years,
        "verified_higher_education_reference_count": valid_refs,
        "minimum_years_gate_satisfied": years >= 5,
        "minimum_reference_gate_satisfied": valid_refs >= 3,
    }


def compile_pursuit(state: dict[str, Any], *, now_utc: dt.datetime) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise PursuitError("state must be an object")
    if state.get("schema") != SCHEMA:
        raise PursuitError(f"schema must be {SCHEMA!r}")
    opportunity = state.get("opportunity")
    if not isinstance(opportunity, dict) or opportunity.get("solicitation_id") != "1017-27":
        raise PursuitError("opportunity must bind solicitation 1017-27")
    if opportunity.get("buyer") != "Metropolitan Community College-Kansas City":
        raise PursuitError("buyer identity mismatch")
    if now_utc.tzinfo is None or now_utc.utcoffset() is None:
        raise PursuitError("now_utc must be timezone-aware")
    now_utc = now_utc.astimezone(dt.timezone.utc)

    _require_false_external_authority(state)
    _validate_secondary(state)

    authority = state.get("buyer_authority")
    if not isinstance(authority, dict):
        raise PursuitError("buyer_authority must be an object")
    package_complete, missing_files = _validate_documents(authority)

    controlling_dates = authority.get("controlling_dates")
    if not isinstance(controlling_dates, dict):
        raise PursuitError("buyer_authority.controlling_dates must be an object")

    prime_ok, prime_summary = _prime_evidence_ok(state)

    if not package_complete:
        decision = "HOLD_BUYER_PACKAGE"
    else:
        proposal_due = _parse_utc(
            controlling_dates.get("proposal_due_utc"),
            "buyer_authority.controlling_dates.proposal_due_utc",
        )
        _parse_utc(
            controlling_dates.get("questions_due_utc"),
            "buyer_authority.controlling_dates.questions_due_utc",
        )
        if now_utc >= proposal_due:
            decision = "HOLD_PROPOSAL_DEADLINE_PASSED"
        elif not prime_ok:
            decision = "HOLD_PRIME_QUALIFICATION"
        else:
            decision = "READY_FOR_OWNER_PRIME_DECISION"

    commercial = state.get("commercial")
    if not isinstance(commercial, dict):
        raise PursuitError("commercial must be an object")
    fee = commercial.get("proposed_fixed_fee_usd")
    if not _is_int(fee) or fee <= 0:
        raise PursuitError("commercial.proposed_fixed_fee_usd must be a positive integer")
    if commercial.get("status") != "PROPOSED_NOT_ACCEPTED":
        raise PursuitError("commercial status must remain PROPOSED_NOT_ACCEPTED")

    body = {
        "schema": SCHEMA,
        "solicitation_id": "1017-27",
        "buyer": opportunity["buyer"],
        "decision": decision,
        "buyer_package_complete": package_complete,
        "missing_required_package_files": missing_files,
        "prime_qualification": prime_summary,
        "partner_public_fit_is_qualification": False,
        "source_recheck_required_before_external_action": True,
        "external_authority": {key: False for key in EXTERNAL_AUTHORITY_KEYS},
        "commercial": {
            "proposed_fixed_fee_usd": fee,
            "status": "PROPOSED_NOT_ACCEPTED",
            "booked_usd": 0,
            "cash_usd": 0,
        },
    }
    receipt = hashlib.sha256(_canonical(body)).hexdigest()
    return {**body, "semantic_receipt_sha256": receipt}


def load_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PursuitError(f"unable to load state: {exc}") from exc
    if not isinstance(value, dict):
        raise PursuitError("state root must be an object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile fail-closed MCC 1017-27 pursuit state")
    parser.add_argument("state", type=Path)
    parser.add_argument("--now", required=True, help="verifier-owned RFC3339 UTC timestamp")
    args = parser.parse_args(argv)
    now = _parse_utc(args.now, "--now")
    compiled = compile_pursuit(load_state(args.state), now_utc=now)
    print(json.dumps(compiled, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
