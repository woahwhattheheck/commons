from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any
from zoneinfo import ZoneInfo

SOURCE_SCHEMA = "nhdes_lims_2026_093.source.v1"
CANDIDATE_SCHEMA = "nhdes_lims_2026_093.partner_candidate.v1"
RECEIPT_SCHEMA = "nhdes_lims_2026_093.teaming_receipt.v1"
OPPORTUNITY_ID = "RFP NHDES/DoIT 2026-093"
MAX_INPUT_BYTES = 256 * 1024
MAX_RECEIPT_BYTES = 512 * 1024
MAX_STATE_AGE_SECONDS = 24 * 60 * 60
MAX_CLOCK_SKEW_SECONDS = 5 * 60
BUYER_TIMEZONE = "America/New_York"

AUTHORITY = {
    "buyer_contact_authorized": False,
    "vendor_conference_registration_authorized": False,
    "partner_contact_authorized_by_carrier": False,
    "prime_qualification_asserted": False,
    "bid_submission_authorized": False,
    "contract_acceptance_authorized": False,
    "payment_authorized": False,
    "revenue_asserted": False,
}

EXPECTED_OPPORTUNITY = {
    "id": OPPORTUNITY_ID,
    "buyer": "New Hampshire Department of Environmental Services / Department of Information Technology",
    "title": "Laboratory Information Management System (LIMS) Implementation and Integration with Environmental Monitoring Database",
    "posted_date": "2026-09-10",
    "response_due": "2026-10-23",
    "vendor_conference": "2026-10-05T14:00:00-04:00",
    "contact_email": "kirsten.a.hugger@des.nh.gov",
    "contract_through": "2032-03-31",
    "possible_extension_years": 5,
    "all_data_handling_conus": True,
}

EXPECTED_BUYER_NEED = {
    "current_tracker": "Microsoft Access sample tracking database",
    "target": "industry-standard LIMS or similar technological approach",
    "environmental_monitoring_database": "Oracle-based EMD",
    "two_way_emd_integration": True,
    "automatic_completed_record_flow_to_emd": True,
    "role_based_security": True,
    "user_maintainable_picklists": True,
    "labels_and_chain_of_custody": True,
    "remote_access": True,
    "training": True,
    "physical_chemical_biological_and_continuous_profile_data": True,
}

EXPECTED_REPORTED_GATES = {
    "nist_sp_800_171": "REQUIRES_RAW_PACKET_CONFIRMATION",
    "govramp_authorization": "REQUIRES_RAW_PACKET_CONFIRMATION",
    "personnel_background_checks": "REQUIRES_RAW_PACKET_CONFIRMATION",
    "insurance": "REQUIRES_RAW_PACKET_CONFIRMATION",
}

EXPECTED_CANDIDATE = {
    "name": "LabLynx, Inc.",
    "domain": "lablynx.com",
    "route": "sales@lablynx.com",
    "status": "CANDIDATE_ONLY_NOT_PARTNER",
    "official_contact_url": "https://www.lablynx.com/contact-us/",
}

EXPECTED_COLLISION_OPERATION = "ALBERTA-AB-2026-06140-LABLYNX-PARTNER-CONVERSION-ZSOL-20260917"
REQUIRED_CANDIDATE_URLS = frozenset(
    {
        "https://www.lablynx.com/resources/case-studies/lims-vendor-security-audit/",
        "https://www.lablynx.com/services/",
        "https://www.lablynx.com/resources/articles/types-of-lims/",
        "https://www.lablynx.com/contact-us/",
    }
)
REQUIRED_GAPS = frozenset(
    {
        "pursuing_nhdes_2026_093",
        "govramp_authorization",
        "nist_sp_800_171",
        "conus_hosting_for_this_offer",
        "required_insurance",
        "personnel_background_checks",
        "nh_public_sector_references",
        "willing_to_prime_or_team",
        "implementation_bandwidth",
    }
)


class CarrierError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError) as exc:
        raise CarrierError(f"cannot canonicalize: {exc}") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        if key in out:
            raise CarrierError(f"duplicate JSON key: {key!r}")
        out[key] = value
    return out


def _reject_constant(token: str) -> Any:
    raise CarrierError(f"invalid JSON constant: {token}")


def parse_json_bytes(raw: bytes, *, where: str) -> Any:
    try:
        text = raw.decode("utf-8", "strict")
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_reject_constant)
        canonical_json(value)
        return value
    except CarrierError:
        raise
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError, OverflowError) as exc:
        raise CarrierError(f"{where}: invalid JSON: {exc}") from exc


def read_regular(path: Path, *, max_bytes: int, where: str) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise CarrierError(f"{where}: cannot stat input: {exc}") from exc
    if not stat.S_ISREG(before.st_mode):
        raise CarrierError(f"{where}: input must be a regular file")
    if before.st_size > max_bytes:
        raise CarrierError(f"{where}: input exceeds {max_bytes} bytes")

    flags = os.O_RDONLY
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise CarrierError(f"{where}: cannot open input: {exc}") from exc
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise CarrierError(f"{where}: opened input is not a regular file")
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise CarrierError(f"{where}: input identity changed during open")
        if opened.st_size > max_bytes:
            raise CarrierError(f"{where}: input exceeds {max_bytes} bytes")

        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining > 0:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > max_bytes:
            raise CarrierError(f"{where}: input exceeds {max_bytes} bytes")

        end = os.fstat(fd)
        if (
            (end.st_dev, end.st_ino) != (opened.st_dev, opened.st_ino)
            or end.st_size != opened.st_size
            or end.st_mtime_ns != opened.st_mtime_ns
        ):
            raise CarrierError(f"{where}: input changed while reading")
        return raw
    finally:
        os.close(fd)


def load_json(path: Path, *, max_bytes: int, where: str) -> Any:
    return parse_json_bytes(read_regular(path, max_bytes=max_bytes, where=where), where=where)


def _exact_dict(value: Any, keys: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise CarrierError(f"{where} must be an object")
    if set(value) != keys:
        raise CarrierError(f"{where} keys mismatch")
    return value


def _all_false(value: Any, expected_keys: set[str], where: str) -> None:
    data = _exact_dict(value, expected_keys, where)
    if any(item is not False for item in data.values()):
        raise CarrierError(f"{where} must remain all false")


def _aware_timestamp(value: Any, where: str) -> datetime:
    if type(value) is not str or not value or len(value) > 40:
        raise CarrierError(f"{where} must be an offset-aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise CarrierError(f"{where} must be an offset-aware ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CarrierError(f"{where} must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _response_due_date(value: Any) -> date:
    if type(value) is not str:
        raise CarrierError("opportunity.response_due must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CarrierError("opportunity.response_due must be YYYY-MM-DD") from exc


def validate_source(value: Any) -> dict[str, Any]:
    source = _exact_dict(
        value,
        {
            "schema",
            "checked_at",
            "source_state",
            "opportunity",
            "buyer_need",
            "reported_bidder_requirements",
            "source_notes",
            "external_authority",
        },
        "source",
    )
    if source["schema"] != SOURCE_SCHEMA:
        raise CarrierError("source schema mismatch")
    if source["source_state"] != "RAW_PACKET_NOT_ACQUIRED":
        raise CarrierError("source state must remain RAW_PACKET_NOT_ACQUIRED")
    _aware_timestamp(source["checked_at"], "source.checked_at")
    if source["opportunity"] != EXPECTED_OPPORTUNITY:
        raise CarrierError("opportunity binding mismatch")
    _response_due_date(source["opportunity"]["response_due"])
    if source["buyer_need"] != EXPECTED_BUYER_NEED:
        raise CarrierError("buyer need binding mismatch")
    if source["reported_bidder_requirements"] != EXPECTED_REPORTED_GATES:
        raise CarrierError("reported bidder gate binding mismatch")
    notes = source["source_notes"]
    if type(notes) is not list or len(notes) < 3 or any(type(item) is not str or not item for item in notes):
        raise CarrierError("source notes malformed")
    _all_false(
        source["external_authority"],
        {
            "buyer_contact",
            "vendor_conference_registration",
            "partner_contact",
            "prime_qualification_assertion",
            "bid_submission",
            "contract_acceptance",
            "payment",
            "revenue",
        },
        "source.external_authority",
    )
    return source


def validate_candidate(value: Any) -> dict[str, Any]:
    candidate = _exact_dict(
        value,
        {
            "schema",
            "evidence_checked_before",
            "candidate",
            "first_party_evidence",
            "qualification_gaps",
            "collision_preflight",
            "current_collision",
            "external_authority",
        },
        "candidate_snapshot",
    )
    if candidate["schema"] != CANDIDATE_SCHEMA:
        raise CarrierError("candidate schema mismatch")
    evidence_before = _aware_timestamp(candidate["evidence_checked_before"], "candidate.evidence_checked_before")
    if candidate["candidate"] != EXPECTED_CANDIDATE:
        raise CarrierError("candidate identity binding mismatch")

    evidence = candidate["first_party_evidence"]
    if type(evidence) is not list or not evidence:
        raise CarrierError("first-party evidence missing")
    urls: set[str] = set()
    for row in evidence:
        row = _exact_dict(row, {"url", "supports"}, "candidate evidence row")
        if type(row["url"]) is not str or type(row["supports"]) is not list:
            raise CarrierError("candidate evidence row types invalid")
        if any(type(item) is not str or not item for item in row["supports"]):
            raise CarrierError("candidate evidence support text invalid")
        urls.add(row["url"])
    if urls != set(REQUIRED_CANDIDATE_URLS):
        raise CarrierError("candidate evidence URL set mismatch")

    gaps = _exact_dict(candidate["qualification_gaps"], set(REQUIRED_GAPS), "qualification_gaps")
    if any(item != "UNVERIFIED" for item in gaps.values()):
        raise CarrierError("candidate qualification gaps must remain UNVERIFIED")

    collision = _exact_dict(
        candidate["collision_preflight"],
        {
            "slack_exact_history",
            "gmail_exact_history",
            "owned_github_exact_history",
            "requires_fresh_last_inch_recensus",
            "requires_muse_single_writer_clearance",
        },
        "collision_preflight",
    )
    for key in ("slack_exact_history", "gmail_exact_history", "owned_github_exact_history"):
        if type(collision[key]) is not int or collision[key] != 0:
            raise CarrierError(f"{key} must be exact zero in the retained historical preflight")
    if collision["requires_fresh_last_inch_recensus"] is not True:
        raise CarrierError("last-inch recensus must be required")
    if collision["requires_muse_single_writer_clearance"] is not True:
        raise CarrierError("Muse clearance must be required")

    current = _exact_dict(
        candidate["current_collision"],
        {
            "status",
            "observed_at",
            "same_org",
            "same_route",
            "competing_operation",
            "muse_arbitration_ts",
            "muse_resolution",
        },
        "current_collision",
    )
    if current["status"] != "ACTIVE_ORG_ROUTE_COLLISION_HOLD":
        raise CarrierError("current collision must remain an active HOLD in this generation")
    observed = _aware_timestamp(current["observed_at"], "current_collision.observed_at")
    if evidence_before > observed:
        raise CarrierError("historical preflight must precede the observed collision")
    if current["same_org"] is not True or current["same_route"] is not True:
        raise CarrierError("current collision must bind same organization and route")
    if current["competing_operation"] != EXPECTED_COLLISION_OPERATION:
        raise CarrierError("current collision competing operation mismatch")
    if type(current["muse_arbitration_ts"]) is not str or not current["muse_arbitration_ts"]:
        raise CarrierError("current collision Muse arbitration receipt missing")
    if current["muse_resolution"] != "PENDING":
        raise CarrierError("current collision Muse resolution must remain PENDING in this generation")

    _all_false(
        candidate["external_authority"],
        {
            "contact_authorized_by_file",
            "partnership_asserted",
            "qualification_asserted",
            "bid_role_asserted",
            "payment_asserted",
            "revenue_asserted",
        },
        "candidate.external_authority",
    )
    return candidate


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def evaluate_runtime_state(source: dict[str, Any], candidate: dict[str, Any], *, now: datetime) -> list[str]:
    """Return fail-closed runtime holds at a supplied trusted clock value.

    Production compile/verify never accept a caller clock; they call _now_utc().
    Tests use this pure helper to pin stale/future/deadline predecessors.
    """
    validate_source(source)
    validate_candidate(candidate)
    if now.tzinfo is None or now.utcoffset() is None:
        raise CarrierError("runtime now must be timezone-aware")
    now_utc = now.astimezone(timezone.utc)
    future_limit = now_utc + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS)
    source_checked = _aware_timestamp(source["checked_at"], "source.checked_at")
    evidence_before = _aware_timestamp(candidate["evidence_checked_before"], "candidate.evidence_checked_before")
    collision_observed = _aware_timestamp(candidate["current_collision"]["observed_at"], "current_collision.observed_at")

    holds: list[str] = []
    if source_checked > future_limit:
        holds.append("SOURCE_STATE_FUTURE")
    elif now_utc - source_checked > timedelta(seconds=MAX_STATE_AGE_SECONDS):
        holds.append("SOURCE_STATE_STALE")

    if evidence_before > future_limit:
        holds.append("CANDIDATE_EVIDENCE_FUTURE")
    elif now_utc - evidence_before > timedelta(seconds=MAX_STATE_AGE_SECONDS):
        holds.append("CANDIDATE_EVIDENCE_STALE")

    if collision_observed > future_limit:
        holds.append("COLLISION_STATE_FUTURE")
    elif now_utc - collision_observed > timedelta(seconds=MAX_STATE_AGE_SECONDS):
        holds.append("COLLISION_STATE_STALE")

    due = _response_due_date(source["opportunity"]["response_due"])
    buyer_day = now_utc.astimezone(ZoneInfo(BUYER_TIMEZONE)).date()
    if buyer_day > due:
        holds.append("RESPONSE_DEADLINE_PASSED")

    current = candidate["current_collision"]
    if current["status"] == "ACTIVE_ORG_ROUTE_COLLISION_HOLD" or current["muse_resolution"] == "PENDING":
        holds.append("ACTIVE_ORG_ROUTE_COLLISION_PENDING_MUSE")
    return sorted(set(holds))


def _posture_for(holds: list[str]) -> str:
    held = set(holds)
    if "RESPONSE_DEADLINE_PASSED" in held:
        return "HOLD_RESPONSE_DEADLINE_PASSED"
    if held & {"SOURCE_STATE_FUTURE", "CANDIDATE_EVIDENCE_FUTURE", "COLLISION_STATE_FUTURE"}:
        return "HOLD_FUTURE_STATE_INVALID"
    if held & {"SOURCE_STATE_STALE", "CANDIDATE_EVIDENCE_STALE", "COLLISION_STATE_STALE"}:
        return "HOLD_STALE_SOURCE_OR_COLLISION_STATE"
    if "ACTIVE_ORG_ROUTE_COLLISION_PENDING_MUSE" in held:
        return "HOLD_ACTIVE_ORG_COLLISION_PENDING_MUSE"
    return "READY_FOR_MUSE_GATED_PARTNER_INQUIRY_ONLY"


def build_receipt(source: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    validate_source(source)
    validate_candidate(candidate)
    runtime_holds = evaluate_runtime_state(source, candidate, now=_now_utc())

    body: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "opportunity_id": OPPORTUNITY_ID,
        "source_digest": digest(source),
        "candidate_digest": digest(candidate),
        "source_currentness": {
            "retained_checked_at": source["checked_at"],
            "raw_packet_state": source["source_state"],
            "canonical_packet_required_before_bid_or_registration": True,
            "fresh_official_source_recensus_required_before_external_action": True,
        },
        "runtime_gate": {
            "buyer_timezone": BUYER_TIMEZONE,
            "response_due_date": source["opportunity"]["response_due"],
            "max_state_age_seconds": MAX_STATE_AGE_SECONDS,
            "max_clock_skew_seconds": MAX_CLOCK_SKEW_SECONDS,
            "holds": runtime_holds,
        },
        "prime_posture": "HOLD_RAW_PACKET_AND_EXTERNAL_PRIME_EVIDENCE",
        "partner_conversion_posture": _posture_for(runtime_holds),
        "candidate": {
            "name": EXPECTED_CANDIDATE["name"],
            "route": EXPECTED_CANDIDATE["route"],
            "status": "CANDIDATE_ONLY_NOT_PARTNER",
            "pursuit_intent": "UNVERIFIED",
            "govramp_authorization": "UNVERIFIED",
            "nist_sp_800_171": "UNVERIFIED",
            "prime_willingness": "UNVERIFIED",
            "current_collision_status": candidate["current_collision"]["status"],
            "muse_resolution": candidate["current_collision"]["muse_resolution"],
        },
        "why_inquiry_is_grounded": [
            "candidate publishes a state-government LIMS security-audit case grounded in NIST CSF / SP 800-53",
            "candidate advertises LIMS implementation, data migration, integration, validation, hosting, support, and training services",
            "candidate publishes LIMS material covering environmental and water testing laboratories",
            "candidate publishes sales@lablynx.com as a sales route",
        ],
        "specialist_offer": {
            "price_usd": 40000,
            "duration_business_days": 15,
            "commercial_status": "PROPOSED_NOT_ACCEPTED",
            "source_repo": "woahwhattheheck/aquatrace-lims",
            "source_pr": 170,
            "source_merge": "18875f099420676d1919a5e143ee4f62dca28e5e",
            "source_truth": "READY_FOR_PRIME_TECHNICAL_REVIEW",
            "scope": [
                "EMD integration and data-conversion engineering",
                "migration reconciliation and replay/idempotency evidence",
                "schema-bound import/export validation",
                "deterministic acceptance and correction evidence",
                "cutover/UAT evidence support",
            ],
            "excludes": [
                "commercial LIMS product or licensing",
                "prime or buyer representation",
                "hosting/security compliance representations",
                "GovRAMP or NIST certification claims",
                "insurance/background-check attestations",
                "proposal submission or contract acceptance",
            ],
        },
        "partner_must_own_or_prove": [
            "commercial LIMS product and licensing",
            "production hosting/security posture",
            "GovRAMP and NIST requirements if required by the canonical packet",
            "required insurance and personnel screening",
            "support/SLA and training commitments",
            "past performance and references",
            "prime proposal, pricing, legal terms, and submission",
        ],
        "single_writer_gate": {
            "fresh_slack_recensus": True,
            "fresh_gmail_recensus": True,
            "fresh_github_recensus": True,
            "muse_clearance_required": True,
            "maximum_messages_if_cleared": 1,
            "provider_sent_creates_hard_dnr_until_genuine_event": True,
        },
        "terminal_money_event": (
            "A qualified LIMS prime accepts the paid TJLabs specialist workshare, carries it into a valid proposal/award path, "
            "and TJLabs is paid for accepted delivery."
        ),
        "money_state": "NO_ACCEPTANCE_NO_RECEIVABLE_NO_REVENUE",
        "authority": dict(AUTHORITY),
    }
    receipt = dict(body)
    receipt["receipt_hash"] = digest(body)
    return receipt


def verify_receipt(receipt: Any, source: dict[str, Any], candidate: dict[str, Any]) -> None:
    if type(receipt) is not dict:
        raise CarrierError("receipt must be an object")
    expected = build_receipt(source, candidate)
    if canonical_json(receipt) != canonical_json(expected):
        raise CarrierError("receipt mismatch or runtime gate changed")


def write_exclusive(path: Path, value: Any) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except FileExistsError as exc:
        raise CarrierError(f"refusing to overwrite existing output: {path}") from exc


def _load_source(path: Path) -> dict[str, Any]:
    return validate_source(load_json(path, max_bytes=MAX_INPUT_BYTES, where="source"))


def _load_candidate(path: Path) -> dict[str, Any]:
    return validate_candidate(load_json(path, max_bytes=MAX_INPUT_BYTES, where="candidate"))


def _load_receipt(path: Path) -> Any:
    return load_json(path, max_bytes=MAX_RECEIPT_BYTES, where="receipt")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile or verify the NHDES 2026-093 teaming carrier")
    sub = parser.add_subparsers(dest="command", required=True)

    compile_parser = sub.add_parser("compile")
    compile_parser.add_argument("--source", required=True, type=Path)
    compile_parser.add_argument("--candidate", required=True, type=Path)
    compile_parser.add_argument("--output", required=True, type=Path)

    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--source", required=True, type=Path)
    verify_parser.add_argument("--candidate", required=True, type=Path)
    verify_parser.add_argument("--receipt", required=True, type=Path)

    args = parser.parse_args(argv)
    try:
        source = _load_source(args.source)
        candidate = _load_candidate(args.candidate)
        if args.command == "compile":
            write_exclusive(args.output, build_receipt(source, candidate))
            return 0
        verify_receipt(_load_receipt(args.receipt), source, candidate)
        print("VERIFIED")
        return 0
    except CarrierError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
