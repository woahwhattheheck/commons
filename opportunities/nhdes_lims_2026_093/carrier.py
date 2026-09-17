from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from types import MappingProxyType
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

# Public/readable compatibility view only. Production semantics do not read this
# global after import; the runtime generation below owns a private immutable
# all-false authority template.
AUTHORITY = MappingProxyType(
    {
        "buyer_contact_authorized": False,
        "vendor_conference_registration_authorized": False,
        "partner_contact_authorized_by_carrier": False,
        "prime_qualification_asserted": False,
        "bid_submission_authorized": False,
        "contract_acceptance_authorized": False,
        "payment_authorized": False,
        "revenue_asserted": False,
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


def _now_utc() -> datetime:
    """Compatibility helper only; production build/verify do not late-resolve it."""
    return datetime.now(timezone.utc)


def _make_runtime_generation():
    """Freeze one semantic generation against ordinary module-global rebinding."""

    source_schema = "nhdes_lims_2026_093.source.v1"
    candidate_schema = "nhdes_lims_2026_093.partner_candidate.v1"
    receipt_schema = "nhdes_lims_2026_093.teaming_receipt.v1"
    opportunity_id = "RFP NHDES/DoIT 2026-093"
    max_state_age_seconds = 24 * 60 * 60
    max_clock_skew_seconds = 5 * 60
    buyer_timezone_name = "America/New_York"
    buyer_zone = ZoneInfo(buyer_timezone_name)
    utc = timezone.utc
    datetime_now = datetime.now
    datetime_fromisoformat = datetime.fromisoformat
    date_fromisoformat = date.fromisoformat
    timedelta_type = timedelta
    json_dumps = json.dumps
    sha256 = hashlib.sha256

    expected_opportunity = {
        "id": opportunity_id,
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
    expected_buyer_need = {
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
    expected_reported_gates = {
        "nist_sp_800_171": "REQUIRES_RAW_PACKET_CONFIRMATION",
        "govramp_authorization": "REQUIRES_RAW_PACKET_CONFIRMATION",
        "personnel_background_checks": "REQUIRES_RAW_PACKET_CONFIRMATION",
        "insurance": "REQUIRES_RAW_PACKET_CONFIRMATION",
    }
    expected_candidate = {
        "name": "LabLynx, Inc.",
        "domain": "lablynx.com",
        "route": "sales@lablynx.com",
        "status": "CANDIDATE_ONLY_NOT_PARTNER",
        "official_contact_url": "https://www.lablynx.com/contact-us/",
    }
    expected_collision_operation = "ALBERTA-AB-2026-06140-LABLYNX-PARTNER-CONVERSION-ZSOL-20260917"
    required_candidate_urls = frozenset(
        {
            "https://www.lablynx.com/resources/case-studies/lims-vendor-security-audit/",
            "https://www.lablynx.com/services/",
            "https://www.lablynx.com/resources/articles/types-of-lims/",
            "https://www.lablynx.com/contact-us/",
        }
    )
    required_gaps = frozenset(
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
    authority_keys = (
        "buyer_contact_authorized",
        "vendor_conference_registration_authorized",
        "partner_contact_authorized_by_carrier",
        "prime_qualification_asserted",
        "bid_submission_authorized",
        "contract_acceptance_authorized",
        "payment_authorized",
        "revenue_asserted",
    )

    def canon(value: Any) -> bytes:
        try:
            return json_dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8", "strict")
        except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError) as exc:
            raise CarrierError(f"cannot canonicalize: {exc}") from exc

    def dgst(value: Any) -> str:
        return sha256(canon(value)).hexdigest()

    def exact_dict(value: Any, keys: set[str], where: str) -> dict[str, Any]:
        if type(value) is not dict:
            raise CarrierError(f"{where} must be an object")
        if set(value) != keys:
            raise CarrierError(f"{where} keys mismatch")
        return value

    def all_false(value: Any, expected_keys: set[str], where: str) -> None:
        data = exact_dict(value, expected_keys, where)
        if any(item is not False for item in data.values()):
            raise CarrierError(f"{where} must remain all false")

    def aware_timestamp(value: Any, where: str) -> datetime:
        if type(value) is not str or not value or len(value) > 40:
            raise CarrierError(f"{where} must be an offset-aware ISO timestamp")
        try:
            parsed = datetime_fromisoformat(value)
        except ValueError as exc:
            raise CarrierError(f"{where} must be an offset-aware ISO timestamp") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise CarrierError(f"{where} must include a UTC offset")
        return parsed.astimezone(utc)

    def response_due_date(value: Any) -> date:
        if type(value) is not str:
            raise CarrierError("opportunity.response_due must be YYYY-MM-DD")
        try:
            return date_fromisoformat(value)
        except ValueError as exc:
            raise CarrierError("opportunity.response_due must be YYYY-MM-DD") from exc

    def authority_false() -> dict[str, bool]:
        return {key: False for key in authority_keys}

    def validate_source_fn(value: Any) -> dict[str, Any]:
        source = exact_dict(
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
        if source["schema"] != source_schema:
            raise CarrierError("source schema mismatch")
        if source["source_state"] != "RAW_PACKET_NOT_ACQUIRED":
            raise CarrierError("source state must remain RAW_PACKET_NOT_ACQUIRED")
        aware_timestamp(source["checked_at"], "source.checked_at")
        if source["opportunity"] != expected_opportunity:
            raise CarrierError("opportunity binding mismatch")
        response_due_date(source["opportunity"]["response_due"])
        if source["buyer_need"] != expected_buyer_need:
            raise CarrierError("buyer need binding mismatch")
        if source["reported_bidder_requirements"] != expected_reported_gates:
            raise CarrierError("reported bidder gate binding mismatch")
        notes = source["source_notes"]
        if type(notes) is not list or len(notes) < 3 or any(type(item) is not str or not item for item in notes):
            raise CarrierError("source notes malformed")
        all_false(
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

    def validate_candidate_fn(value: Any) -> dict[str, Any]:
        candidate = exact_dict(
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
        if candidate["schema"] != candidate_schema:
            raise CarrierError("candidate schema mismatch")
        evidence_before = aware_timestamp(candidate["evidence_checked_before"], "candidate.evidence_checked_before")
        if candidate["candidate"] != expected_candidate:
            raise CarrierError("candidate identity binding mismatch")

        evidence = candidate["first_party_evidence"]
        if type(evidence) is not list or not evidence:
            raise CarrierError("first-party evidence missing")
        urls: set[str] = set()
        for row in evidence:
            row = exact_dict(row, {"url", "supports"}, "candidate evidence row")
            if type(row["url"]) is not str or type(row["supports"]) is not list:
                raise CarrierError("candidate evidence row types invalid")
            if any(type(item) is not str or not item for item in row["supports"]):
                raise CarrierError("candidate evidence support text invalid")
            urls.add(row["url"])
        if urls != set(required_candidate_urls):
            raise CarrierError("candidate evidence URL set mismatch")

        gaps = exact_dict(candidate["qualification_gaps"], set(required_gaps), "qualification_gaps")
        if any(item != "UNVERIFIED" for item in gaps.values()):
            raise CarrierError("candidate qualification gaps must remain UNVERIFIED")

        collision = exact_dict(
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

        current = exact_dict(
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
        observed = aware_timestamp(current["observed_at"], "current_collision.observed_at")
        if evidence_before > observed:
            raise CarrierError("historical preflight must precede the observed collision")
        if current["same_org"] is not True or current["same_route"] is not True:
            raise CarrierError("current collision must bind same organization and route")
        if current["competing_operation"] != expected_collision_operation:
            raise CarrierError("current collision competing operation mismatch")
        if type(current["muse_arbitration_ts"]) is not str or not current["muse_arbitration_ts"]:
            raise CarrierError("current collision Muse arbitration receipt missing")
        if current["muse_resolution"] != "PENDING":
            raise CarrierError("current collision Muse resolution must remain PENDING in this generation")

        all_false(
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

    def evaluate_runtime_state_fn(source: dict[str, Any], candidate: dict[str, Any], *, now: datetime) -> list[str]:
        validate_source_fn(source)
        validate_candidate_fn(candidate)
        if now.tzinfo is None or now.utcoffset() is None:
            raise CarrierError("runtime now must be timezone-aware")
        now_utc = now.astimezone(utc)
        future_limit = now_utc + timedelta_type(seconds=max_clock_skew_seconds)
        source_checked = aware_timestamp(source["checked_at"], "source.checked_at")
        evidence_before = aware_timestamp(candidate["evidence_checked_before"], "candidate.evidence_checked_before")
        collision_observed = aware_timestamp(candidate["current_collision"]["observed_at"], "current_collision.observed_at")

        holds: list[str] = []
        if source_checked > future_limit:
            holds.append("SOURCE_STATE_FUTURE")
        elif now_utc - source_checked > timedelta_type(seconds=max_state_age_seconds):
            holds.append("SOURCE_STATE_STALE")

        if evidence_before > future_limit:
            holds.append("CANDIDATE_EVIDENCE_FUTURE")
        elif now_utc - evidence_before > timedelta_type(seconds=max_state_age_seconds):
            holds.append("CANDIDATE_EVIDENCE_STALE")

        if collision_observed > future_limit:
            holds.append("COLLISION_STATE_FUTURE")
        elif now_utc - collision_observed > timedelta_type(seconds=max_state_age_seconds):
            holds.append("COLLISION_STATE_STALE")

        due = response_due_date(source["opportunity"]["response_due"])
        buyer_day = now_utc.astimezone(buyer_zone).date()
        if buyer_day > due:
            holds.append("RESPONSE_DEADLINE_PASSED")

        current = candidate["current_collision"]
        if current["status"] == "ACTIVE_ORG_ROUTE_COLLISION_HOLD" or current["muse_resolution"] == "PENDING":
            holds.append("ACTIVE_ORG_ROUTE_COLLISION_PENDING_MUSE")
        return sorted(set(holds))

    def posture_for_fn(holds: list[str]) -> str:
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

    def build_receipt_fn(source: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        validate_source_fn(source)
        validate_candidate_fn(candidate)
        runtime_holds = evaluate_runtime_state_fn(source, candidate, now=datetime_now(utc))

        body: dict[str, Any] = {
            "schema": receipt_schema,
            "opportunity_id": opportunity_id,
            "source_digest": dgst(source),
            "candidate_digest": dgst(candidate),
            "source_currentness": {
                "retained_checked_at": source["checked_at"],
                "raw_packet_state": source["source_state"],
                "canonical_packet_required_before_bid_or_registration": True,
                "fresh_official_source_recensus_required_before_external_action": True,
            },
            "runtime_gate": {
                "buyer_timezone": buyer_timezone_name,
                "response_due_date": source["opportunity"]["response_due"],
                "max_state_age_seconds": max_state_age_seconds,
                "max_clock_skew_seconds": max_clock_skew_seconds,
                "holds": runtime_holds,
            },
            "prime_posture": "HOLD_RAW_PACKET_AND_EXTERNAL_PRIME_EVIDENCE",
            "partner_conversion_posture": posture_for_fn(runtime_holds),
            "candidate": {
                "name": expected_candidate["name"],
                "route": expected_candidate["route"],
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
            "authority": authority_false(),
        }
        receipt = dict(body)
        receipt["receipt_hash"] = dgst(body)
        return receipt

    def verify_receipt_fn(receipt: Any, source: dict[str, Any], candidate: dict[str, Any]) -> None:
        if type(receipt) is not dict:
            raise CarrierError("receipt must be an object")
        expected = build_receipt_fn(source, candidate)
        if canon(receipt) != canon(expected):
            raise CarrierError("receipt mismatch or runtime gate changed")

    return (
        validate_source_fn,
        validate_candidate_fn,
        evaluate_runtime_state_fn,
        posture_for_fn,
        build_receipt_fn,
        verify_receipt_fn,
    )


(
    validate_source,
    validate_candidate,
    evaluate_runtime_state,
    _posture_for,
    build_receipt,
    verify_receipt,
) = _make_runtime_generation()
del _make_runtime_generation


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


def _make_main(build_fn, verify_fn, load_source_fn, load_candidate_fn, load_receipt_fn, write_fn):
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
            source = load_source_fn(args.source)
            candidate = load_candidate_fn(args.candidate)
            if args.command == "compile":
                write_fn(args.output, build_fn(source, candidate))
                return 0
            verify_fn(load_receipt_fn(args.receipt), source, candidate)
            print("VERIFIED")
            return 0
        except CarrierError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    return main


main = _make_main(build_receipt, verify_receipt, _load_source, _load_candidate, _load_receipt, write_exclusive)
del _make_main


if __name__ == "__main__":
    raise SystemExit(main())
