from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any

OPPORTUNITY_ID = "NYSDEC-HALE-CREEK-LIMS-RFI-2138876"
PARTNER_COMPANY = "Khemia Software, Inc."
PARTNER_PRODUCT = "Omega LIMS"
PARTNER_ROUTE = "info@khemia.com"
SOURCE_SCHEMA = "nysdec_hcfs_lims.partner_candidate_source.v1"
RECEIPT_SCHEMA = "nysdec_hcfs_lims.partner_workshare_receipt.v1"
SOURCE_SHA256 = "4422d738d25f50304d3b3650f7b414a3c2903b859f555676533a1c96b18ed008"
MAX_SOURCE_BYTES = 128 * 1024
MAX_RECEIPT_BYTES = 256 * 1024

AUTHORITY_KEYS = (
    "buyer_contact_authorized",
    "partner_contact_authorized",
    "rfi_submission_authorized",
    "partner_representation_authorized",
    "contract_acceptance_authorized",
    "award_asserted",
    "payment_authorized",
    "revenue_asserted",
)

UNRESOLVED_PARTNER_GATES = (
    "NYS OGS or GSA procurement-vehicle status",
    "hybrid on-premises/cloud production architecture for this requirement",
    "24x7x365 maintenance and support commitment",
    "NYS/DEC/ITS security posture for this requirement",
    "disaster-recovery commitment for this requirement",
    "warranty and equipment-replacement terms",
    "comparable NYS government environmental-lab deployments",
    "exact fit to every retained Hale Creek RFI question",
    "current implementation capacity and delivery runway",
    "willingness to pursue or respond to Hale Creek",
    "willingness to use TJLabs as a paid specialist workshare",
)

WORKSHARE_MODULES = (
    "MIGRATION_EVIDENCE",
    "INTEGRATION_CONFORMANCE",
    "UAT_ACCEPTANCE_EVIDENCE",
    "CUTOVER_REPLAY",
)


class PartnerGuardError(ValueError):
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
        raise PartnerGuardError(f"cannot canonicalize: {exc}") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        if key in out:
            raise PartnerGuardError(f"duplicate JSON key: {key!r}")
        out[key] = value
    return out


def parse_json_bytes(raw: bytes, *, where: str) -> Any:
    try:
        text = raw.decode("utf-8", "strict")
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                PartnerGuardError(f"{where}: invalid JSON constant {token}")
            ),
        )
        canonical_json(value)
        return value
    except PartnerGuardError:
        raise
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError, OverflowError) as exc:
        raise PartnerGuardError(f"{where}: invalid JSON: {exc}") from exc


def read_regular(path: Path, *, max_bytes: int, where: str) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise PartnerGuardError(f"{where}: cannot stat input: {exc}") from exc
    if not stat.S_ISREG(before.st_mode):
        raise PartnerGuardError(f"{where}: input must be a regular file")
    if before.st_size > max_bytes:
        raise PartnerGuardError(f"{where}: input exceeds {max_bytes} bytes")

    flags = os.O_RDONLY
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise PartnerGuardError(f"{where}: cannot open input: {exc}") from exc
    try:
        after = os.fstat(fd)
        if not stat.S_ISREG(after.st_mode):
            raise PartnerGuardError(f"{where}: opened input is not a regular file")
        if (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino):
            raise PartnerGuardError(f"{where}: input identity changed during open")
        if after.st_size > max_bytes:
            raise PartnerGuardError(f"{where}: input exceeds {max_bytes} bytes")
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
            raise PartnerGuardError(f"{where}: input exceeds {max_bytes} bytes")
        end = os.fstat(fd)
        if (
            (end.st_dev, end.st_ino) != (after.st_dev, after.st_ino)
            or end.st_size != after.st_size
            or end.st_mtime_ns != after.st_mtime_ns
        ):
            raise PartnerGuardError(f"{where}: input changed while reading")
        return raw
    finally:
        os.close(fd)


def _exact_dict(value: Any, keys: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise PartnerGuardError(f"{where} must be an object")
    if set(value) != keys:
        raise PartnerGuardError(f"{where} keys mismatch")
    return value


def _strict_nonempty_strings(values: Any, *, where: str) -> list[str]:
    if type(values) is not list or not values:
        raise PartnerGuardError(f"{where} must be a non-empty array")
    if any(type(item) is not str or not item.strip() for item in values):
        raise PartnerGuardError(f"{where} must contain non-empty strings")
    return values


def validate_source(value: Any) -> dict[str, Any]:
    source = _exact_dict(
        value,
        {
            "schema",
            "source_checked_utc",
            "opportunity",
            "candidate",
            "first_party_evidence",
            "unresolved_partner_gates",
            "commercial_source",
            "single_partner_rule",
        },
        "source",
    )
    if source["schema"] != SOURCE_SCHEMA:
        raise PartnerGuardError("source schema mismatch")
    if source["source_checked_utc"] != "2026-09-17T03:15:00Z":
        raise PartnerGuardError("source check timestamp mismatch")

    opportunity = _exact_dict(
        source["opportunity"],
        {
            "buyer",
            "carrier_merge_commit",
            "carrier_pull_request",
            "contract_reporter_number",
            "direct_cots_lims_prime_status",
            "market_research_only",
            "official_notice_url",
            "tracking_issue",
        },
        "opportunity",
    )
    if opportunity != {
        "buyer": "New York State Department of Environmental Conservation, Division of Fish & Wildlife",
        "carrier_merge_commit": "49b9ff6da9f3e7d932d4bc92024e1a4c3244fb69",
        "carrier_pull_request": 14867,
        "contract_reporter_number": "2138876",
        "direct_cots_lims_prime_status": "HOLD",
        "market_research_only": True,
        "official_notice_url": "https://www.nyscr.ny.gov/Ads/IFrameDetails/2138876?FromAction=Search",
        "tracking_issue": 14864,
    }:
        raise PartnerGuardError("opportunity binding mismatch")

    candidate = _exact_dict(
        source["candidate"],
        {"company", "product", "public_route", "public_website", "route_purpose"},
        "candidate",
    )
    if candidate != {
        "company": PARTNER_COMPANY,
        "product": PARTNER_PRODUCT,
        "public_route": PARTNER_ROUTE,
        "public_website": "https://khemia.com/",
        "route_purpose": "sales_or_product_inquiry",
    }:
        raise PartnerGuardError("candidate binding mismatch")

    evidence = source["first_party_evidence"]
    if type(evidence) is not list or len(evidence) != 3:
        raise PartnerGuardError("first_party_evidence must contain exactly three retained sources")
    expected_urls = (
        "https://khemia.com/environmental-lims/",
        "https://khemia.com/water-utility-lims/",
        "https://khemia.com/",
    )
    for index, item in enumerate(evidence):
        row = _exact_dict(item, {"url", "claims"}, f"first_party_evidence[{index}]")
        if row["url"] != expected_urls[index]:
            raise PartnerGuardError("first-party evidence URL mismatch")
        _strict_nonempty_strings(row["claims"], where=f"first_party_evidence[{index}].claims")

    unresolved = _strict_nonempty_strings(source["unresolved_partner_gates"], where="unresolved_partner_gates")
    if tuple(unresolved) != UNRESOLVED_PARTNER_GATES:
        raise PartnerGuardError("unresolved partner gates mismatch")

    commercial = _exact_dict(
        source["commercial_source"],
        {"repo", "pull_request", "merge_commit", "offer_id", "price_usd", "duration", "state", "workshare_modules"},
        "commercial_source",
    )
    if commercial != {
        "repo": "woahwhattheheck/commons",
        "pull_request": 14882,
        "merge_commit": "c46aece4fd95d799110f8e62499e3e7cae232a17",
        "offer_id": "PILOT_2_TO_4_WEEK",
        "price_usd": 25000,
        "duration": "2-4 weeks",
        "state": "PROPOSED_NOT_ACCEPTED",
        "workshare_modules": list(WORKSHARE_MODULES),
    }:
        raise PartnerGuardError("commercial source binding mismatch")
    if type(commercial["price_usd"]) is not int:
        raise PartnerGuardError("commercial price must be an integer")

    rule = _exact_dict(
        source["single_partner_rule"],
        {"selected_candidate", "parallel_partner_outreach_forbidden", "alternate_partner_contact_requires_release_or_new_event"},
        "single_partner_rule",
    )
    if rule != {
        "selected_candidate": PARTNER_COMPANY,
        "parallel_partner_outreach_forbidden": True,
        "alternate_partner_contact_requires_release_or_new_event": True,
    }:
        raise PartnerGuardError("single-partner rule mismatch")

    return source


def load_source(path: Path) -> dict[str, Any]:
    raw = read_regular(path, max_bytes=MAX_SOURCE_BYTES, where="source")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != SOURCE_SHA256:
        raise PartnerGuardError(
            f"source bytes do not match retained generation: expected {SOURCE_SHA256}, got {actual}"
        )
    return validate_source(parse_json_bytes(raw, where="source"))


def collision_key(*, company: str = PARTNER_COMPANY, route: str = PARTNER_ROUTE) -> str:
    if type(company) is not str or not company.strip() or type(route) is not str or not route.strip():
        raise PartnerGuardError("collision identity requires non-empty company and route")
    payload = {
        "opportunity_id": OPPORTUNITY_ID,
        "purpose": "paid_specialist_teaming_inquiry",
        "route": route.strip().casefold(),
        "target_company": " ".join(company.split()).casefold(),
    }
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def build_receipt(source: dict[str, Any]) -> dict[str, Any]:
    validate_source(source)
    commercial = source["commercial_source"]
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "opportunity_id": OPPORTUNITY_ID,
        "source_sha256": SOURCE_SHA256,
        "source_checked_utc": source["source_checked_utc"],
        "fresh_source_recensus_required_before_provider_action": True,
        "direct_cots_lims_prime_status": "HOLD",
        "candidate_status": "QUALIFIED_FOR_SINGLE_WRITER_TEAMING_INQUIRY_NOT_PARTNER",
        "partner_candidate": {
            "company": PARTNER_COMPANY,
            "product": PARTNER_PRODUCT,
            "route": PARTNER_ROUTE,
            "first_party_evidence": [
                {"url": item["url"], "claims": list(item["claims"])}
                for item in source["first_party_evidence"]
            ],
            "unresolved_gates": list(UNRESOLVED_PARTNER_GATES),
            "does_not_assert": [
                "Khemia is pursuing Hale Creek",
                "Khemia meets every Hale Creek requirement",
                "Khemia accepts TJLabs as a subcontractor",
                "Khemia has NYS OGS/GSA vehicle access",
                "Khemia has buyer-approved security/hosting/support terms",
            ],
        },
        "commercial_offer": {
            "offer_id": commercial["offer_id"],
            "amount_usd": commercial["price_usd"],
            "duration": commercial["duration"],
            "state": "PROPOSED_NOT_ACCEPTED",
            "source": {
                "repo": commercial["repo"],
                "pull_request": commercial["pull_request"],
                "merge_commit": commercial["merge_commit"],
            },
            "modules": list(WORKSHARE_MODULES),
        },
        "workshare_boundary": {
            "partner_retains": [
                "commercial LIMS product and licensing",
                "product fit against the complete buyer RFI",
                "production hosting and security representations",
                "maintenance/support/warranty and disaster recovery",
                "training and implementation commitments",
                "comparable deployment references",
                "NYS OGS/GSA contract representations if claimed",
                "all buyer response, pricing, submission and prime obligations",
            ],
            "tjlabs_if_separately_contracted": [
                "legacy-data migration reconciliation and rollback evidence",
                "instrument/data-interface conformance and replay evidence",
                "duplicate/idempotency and discrepancy detection",
                "schema-bound import/export acceptance verification",
                "quality-hold, audit, correction and provenance receipts",
                "cutover/UAT acceptance evidence",
            ],
        },
        "single_writer": {
            "selected_candidate": PARTNER_COMPANY,
            "selected_route": PARTNER_ROUTE,
            "collision_key": collision_key(),
            "parallel_partner_outreach_forbidden": True,
            "alternate_partner_contact_requires_release_or_new_event": True,
            "muse_exact_selection_required": True,
            "last_inch_slack_gmail_recensus_required": True,
            "provider_sent_terminal_state": "HARD_DNR_PENDING_GENUINE_EVENT",
            "ambiguous_provider_state": "DNR_RECONCILE_NEVER_RESEND",
        },
        "outbound_intent": {
            "recipient": PARTNER_ROUTE,
            "subject": "NYS DEC Hale Creek LIMS RFI — $25k integration/validation workshare",
            "purpose": (
                "Ask whether Khemia is evaluating Hale Creek and, if so, whether a paid bounded "
                "migration/interface/UAT/cutover evidence workshare is useful alongside Omega LIMS."
            ),
            "one_message_max_after_muse_selection": True,
        },
        "authority": {key: False for key in AUTHORITY_KEYS},
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def compile_from_path(source_path: Path) -> dict[str, Any]:
    return build_receipt(load_source(source_path))


def verify_receipt(source_path: Path, receipt_path: Path) -> dict[str, Any]:
    expected = compile_from_path(source_path)
    raw = read_regular(receipt_path, max_bytes=MAX_RECEIPT_BYTES, where="receipt")
    received = parse_json_bytes(raw, where="receipt")
    if received != expected:
        raise PartnerGuardError("receipt does not match exact recomputed partner-workshare receipt")
    if type(received.get("receipt_sha256")) is not str:
        raise PartnerGuardError("receipt hash missing")
    without_hash = dict(received)
    claimed = without_hash.pop("receipt_sha256")
    if claimed != digest(without_hash):
        raise PartnerGuardError("receipt hash mismatch")
    return {
        "valid": True,
        "collision_key": received["single_writer"]["collision_key"],
        "partner_contact_authorized": received["authority"]["partner_contact_authorized"],
        "commercial_state": received["commercial_offer"]["state"],
    }


def write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, data.encode("utf-8", "strict"))
        os.fsync(fd)
    finally:
        os.close(fd)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compile/verify the Hale Creek Khemia teaming carrier")
    sub = parser.add_subparsers(dest="command", required=True)
    compile_cmd = sub.add_parser("compile")
    compile_cmd.add_argument("--source", required=True, type=Path)
    compile_cmd.add_argument("--output", required=True, type=Path)
    verify_cmd = sub.add_parser("verify")
    verify_cmd.add_argument("--source", required=True, type=Path)
    verify_cmd.add_argument("--receipt", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "compile":
            write_exclusive(args.output, compile_from_path(args.source))
            return 0
        result = verify_receipt(args.source, args.receipt)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (PartnerGuardError, OSError) as exc:
        print(f"partner guard: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
