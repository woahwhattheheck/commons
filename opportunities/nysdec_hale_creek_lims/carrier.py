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
SOURCE_SHA256 = "5728d8de6c3a66d03cbc7b29a67f19cf3d42348542ced2e4965ee5846f5052e5"
SOURCE_SCHEMA = "nysdec_hcfs_lims.source.v1"
RECEIPT_SCHEMA = "nysdec_hcfs_lims.response_receipt.v1"
MAX_SOURCE_BYTES = 128 * 1024
MAX_RECEIPT_BYTES = 512 * 1024

AUTHORITY_KEYS = (
    "external_contact_authorized",
    "rfi_submission_authorized",
    "partner_representation_authorized",
    "contract_acceptance_authorized",
    "award_asserted",
    "payment_authorized",
    "revenue_asserted",
)

STATUS_BY_QUESTION = (
    "PARTNER_REQUIRED",  # 1
    "PARTNER_REQUIRED",
    "PARTNER_REQUIRED",
    "PARTNER_REQUIRED",
    "PARTNER_REQUIRED",
    "PARTNER_REQUIRED",
    "PARTNER_REQUIRED",
    "PARTNER_REQUIRED",
    "PARTNER_REQUIRED",
    "EVIDENCE_REQUIRED",  # 10
    "EVIDENCE_REQUIRED",
    "PARTNER_REQUIRED",
    "PARTNER_REQUIRED",
    "EVIDENCE_REQUIRED",
    "EVIDENCE_REQUIRED",
    "PARTNER_REQUIRED",
    "PARTNER_REQUIRED",
    "PARTNER_REQUIRED",
    "PARTNER_REQUIRED",
    "PARTNER_REQUIRED",  # 20
    "PARTNER_REQUIRED",
    "PARTNER_REQUIRED",
    "EVIDENCE_REQUIRED",
    "PARTNER_REQUIRED",
    "PARTNER_REQUIRED",
    "EVIDENCE_REQUIRED",
    "SUPPORTED_INTERNAL",
    "EVIDENCE_REQUIRED",  # 28
)

ALLOWED_STATUSES = frozenset((
    "SUPPORTED_INTERNAL",
    "PARTNER_REQUIRED",
    "EVIDENCE_REQUIRED",
    "NOT_CLAIMED",
))

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


def parse_json_bytes(raw: bytes, *, where: str) -> Any:
    try:
        text = raw.decode("utf-8", "strict")
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                CarrierError(f"{where}: invalid JSON constant {token}")
            ),
        )
        # Reject lone-surrogate strings anywhere while allowing valid non-BMP.
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

    # O_NONBLOCK is part of the pre-fstat trust boundary: if an attacker swaps
    # the lstat-proven regular path to a FIFO before open(), a blocking
    # O_RDONLY open could otherwise hang forever before we can reject its type.
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
        after = os.fstat(fd)
        if not stat.S_ISREG(after.st_mode):
            raise CarrierError(f"{where}: opened input is not a regular file")
        if (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino):
            raise CarrierError(f"{where}: input identity changed during open")
        if after.st_size > max_bytes:
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
            (end.st_dev, end.st_ino) != (after.st_dev, after.st_ino)
            or end.st_size != after.st_size
            or end.st_mtime_ns != after.st_mtime_ns
        ):
            raise CarrierError(f"{where}: input changed while reading")
        return raw
    finally:
        os.close(fd)


def _expect_exact_dict(value: Any, keys: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise CarrierError(f"{where} must be an object")
    if set(value) != keys:
        raise CarrierError(f"{where} keys mismatch")
    return value


def validate_source(value: Any) -> dict[str, Any]:
    source = _expect_exact_dict(
        value,
        {
            "schema",
            "opportunity",
            "current_environment",
            "objectives",
            "questions",
            "response_instructions",
            "general_terms",
        },
        "source",
    )
    if source["schema"] != SOURCE_SCHEMA:
        raise CarrierError("source schema mismatch")

    opportunity = source["opportunity"]
    if type(opportunity) is not dict:
        raise CarrierError("opportunity must be object")
    expected_opportunity = {
        "contract_reporter_number": "2138876",
        "project_name": "Hale Creek Field Station Laboratory Information Management System (LIMS)",
        "buyer": "New York State Department of Environmental Conservation, Division of Fish & Wildlife",
        "official_notice_url": "https://www.nyscr.ny.gov/Ads/IFrameDetails/2138876?FromAction=Search",
        "response_email": "hcfs-lims@dec.ny.gov",
        "response_subject": "Hale Creek Laboratory Information Management System (LIMS)",
        "release_date": "2026-09-15",
        "vendor_inquiries_due": "2026-09-29",
        "department_responses_due": "2026-10-09",
        "rfi_responses_due": "2026-10-20",
        "solicitation_type": "RFI",
        "market_research_only": True,
        "procurement_commitment": False,
        "direct_award_from_response": False,
        "response_format": "Microsoft Office product or Adobe PDF",
        "submission_method": "email",
    }
    if opportunity != expected_opportunity:
        raise CarrierError("opportunity binding mismatch")

    questions = source["questions"]
    if type(questions) is not list or len(questions) != 28:
        raise CarrierError("source must contain exactly 28 numbered questions")
    numbers: list[int] = []
    for item in questions:
        if type(item) is not dict or set(item) != {"number", "section", "text"}:
            raise CarrierError("question shape mismatch")
        if type(item["number"]) is not int or type(item["section"]) is not str or type(item["text"]) is not str:
            raise CarrierError("question field type mismatch")
        if not item["text"] or item["section"] not in {"Desired Requirements", "Information Requested"}:
            raise CarrierError("question content mismatch")
        numbers.append(item["number"])
    if numbers != list(range(1, 29)):
        raise CarrierError("question numbers must be exactly 1..28 in order")

    objectives = source["objectives"]
    if type(objectives) is not dict:
        raise CarrierError("objectives must be object")
    required_objectives = {
        "robust_lims": True,
        "hybrid_storage_requested": True,
        "data_ownership_retained_by_dec_dfw": True,
        "data_sharing_without_consent": False,
        "software_maintenance_support_24x7x365_requested": True,
    }
    if objectives != required_objectives:
        raise CarrierError("objective binding mismatch")

    terms = source["general_terms"]
    if type(terms) is not dict:
        raise CarrierError("general_terms must be object")
    required_terms = {
        "procurement_lobbying_law_restriction_applies": False,
        "questions_via_response_email": True,
        "foil_may_apply": True,
        "confidentiality_not_guaranteed": True,
        "state_may_use_ideas": True,
        "state_may_request_supplemental_information_or_demonstrations": True,
        "state_may_amend_or_cancel": True,
        "cost_figures_non_binding": True,
        "response_preparation_costs_reimbursed": False,
        "failure_to_respond_affects_future_competition": False,
    }
    if terms != required_terms:
        raise CarrierError("general-term binding mismatch")

    return source


def load_source(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = read_regular(path, max_bytes=MAX_SOURCE_BYTES, where="source")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != SOURCE_SHA256:
        raise CarrierError(
            f"source bytes do not match retained generation: expected {SOURCE_SHA256}, got {actual}"
        )
    value = parse_json_bytes(raw, where="source")
    return validate_source(value), raw


def _answer_for(number: int, status: str) -> str:
    if status == "SUPPORTED_INTERNAL":
        if number != 27:
            raise CarrierError("unexpected SUPPORTED_INTERNAL question")
        return (
            "No partner is selected or represented. Desired partner: a qualified commercial LIMS prime "
            "that owns product licensing, production hosting/security, maintenance/support/warranty, "
            "comparable deployment references, and any NYS OGS/GSA contract representations. TJLabs' "
            "bounded desired role is integration, migration/reconciliation, deterministic acceptance, "
            "audit/correction evidence, and cutover/UAT support only."
        )
    if status == "PARTNER_REQUIRED":
        return (
            "HOLD — an authoritative commercial LIMS/product response must come from a qualified product "
            "prime. TJLabs does not claim this product, hosting, support, warranty, training, or deployment fact."
        )
    if status == "EVIDENCE_REQUIRED":
        return (
            "HOLD — retained current evidence is not present for an affirmative response. Do not infer or "
            "self-certify the requested commercial, compliance, customer, staffing, clearance, or contract-vehicle fact."
        )
    if status == "NOT_CLAIMED":
        return "NOT CLAIMED."
    raise CarrierError(f"unknown status: {status}")


def build_receipt(source: dict[str, Any]) -> dict[str, Any]:
    questions = []
    for item in source["questions"]:
        number = item["number"]
        status = STATUS_BY_QUESTION[number - 1]
        if status not in ALLOWED_STATUSES:
            raise CarrierError(f"question {number} has invalid code-owned status")
        questions.append(
            {
                "number": number,
                "section": item["section"],
                "buyer_question": item["text"],
                "status": status,
                "draft_response": _answer_for(number, status),
            }
        )

    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "opportunity_id": OPPORTUNITY_ID,
        "source_sha256": SOURCE_SHA256,
        "official_notice_url": source["opportunity"]["official_notice_url"],
        "response_route": {
            "email": source["opportunity"]["response_email"],
            "subject_must_include": source["opportunity"]["response_subject"],
            "currentness_authoritative": False,
            "fresh_official_source_recensus_required_before_action": True,
        },
        "buyer_timetable": {
            "release_date": source["opportunity"]["release_date"],
            "vendor_inquiries_due": source["opportunity"]["vendor_inquiries_due"],
            "department_responses_due": source["opportunity"]["department_responses_due"],
            "rfi_responses_due": source["opportunity"]["rfi_responses_due"],
            "currentness_authoritative": False,
        },
        "solicitation_truth": {
            "type": "RFI",
            "market_research_only": True,
            "procurement_commitment": False,
            "direct_award_from_response": False,
            "response_cost_reimbursement": False,
            "cost_figures_non_binding": True,
        },
        "direct_cots_lims_prime_status": "HOLD",
        "teaming_status": "TEAMING_ROUTE_OPEN_INTERNAL",
        "rough_order_of_magnitude": {
            "status": "NOT_PRICED",
            "reason": (
                "Commercial LIMS platform/licensing, production hosting, support/warranty, deployment, and "
                "partner-responsibility scope are not retained. Synthetic buyer pricing is forbidden."
            ),
        },
        "internal_engineering_evidence": {
            # Construct a fresh source object on every compilation. Never
            # return an alias to mutable compiler trust state.
            "source": {
                "repo": "woahwhattheheck/aquatrace-lims",
                "pull_request": 159,
                "merge_commit": "3aa038bf56117465a92e4026dda4498932085922",
                "authority": "internal engineering-pattern evidence only; not buyer/customer/product/compliance evidence",
            },
            "supports_only": [
                "stable source-record identity and deterministic source-to-target reconciliation patterns",
                "duplicate-safe replay/idempotency and retained audit/correction evidence patterns",
                "legacy migration reconciliation and cutover/rollback acceptance patterns",
                "schema-bound import/export candidate validation patterns",
                "quality holds and owner-review acceptance evidence patterns",
            ],
            "does_not_prove": [
                "commercially available COTS LIMS product",
                "production customer deployment",
                "NYS or DEC security compliance",
                "hybrid production hosting",
                "24x7x365 support",
                "warranty or equipment replacement",
                "NYS OGS or GSA contract vehicle",
                "staffing headcount or government clearances",
                "buyer references or acceptance",
            ],
        },
        "desired_partner_workshare": {
            "partner_must_own": [
                "commercial LIMS product and licensing",
                "production hosting and security representations",
                "maintenance/support/warranty and disaster recovery",
                "training commitments",
                "comparable deployment references",
                "network/server/equipment requirements",
                "NYS OGS/GSA contract representations if claimed",
            ],
            "tjlabs_bounded_role": [
                "legacy-data migration reconciliation and rollback evidence",
                "instrument/data-interface replay and idempotency verification",
                "source-to-target discrepancy and duplicate detection",
                "schema-bound import/export acceptance verification",
                "quality-hold, audit, correction, and provenance receipts",
                "cutover/UAT acceptance evidence",
            ],
        },
        "recommendations": [
            "Separate baseline product capability assertions from implementation acceptance evidence.",
            "Require stable source identifiers, explicit lineage, and machine-readable export for migration and audit portability.",
            "Stage legacy migration with deterministic reconciliation, discrepancy review, and rollback evidence before cutover.",
            "Bind instrument interfaces to replay/idempotency tests and retained acceptance fixtures.",
            "Keep DEC/DFW-owned canonical data exports and portability evidence independent of any vendor-only runtime.",
        ],
        "response_scaffold": questions,
        "gap_summary": {
            "partner_required_questions": [q["number"] for q in questions if q["status"] == "PARTNER_REQUIRED"],
            "evidence_required_questions": [q["number"] for q in questions if q["status"] == "EVIDENCE_REQUIRED"],
            "supported_internal_questions": [q["number"] for q in questions if q["status"] == "SUPPORTED_INTERNAL"],
        },
        "authority": {key: False for key in AUTHORITY_KEYS},
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def compile_from_path(source_path: Path) -> dict[str, Any]:
    source, _ = load_source(source_path)
    return build_receipt(source)


def verify_receipt(source_path: Path, receipt_path: Path) -> dict[str, Any]:
    expected = compile_from_path(source_path)
    raw = read_regular(receipt_path, max_bytes=MAX_RECEIPT_BYTES, where="receipt")
    actual = parse_json_bytes(raw, where="receipt")
    if canonical_json(actual) != canonical_json(expected):
        raise CarrierError("receipt is not the exact recomputed code-owned result")
    return {
        "valid": True,
        "opportunity_id": OPPORTUNITY_ID,
        "source_sha256": SOURCE_SHA256,
        "receipt_sha256": expected["receipt_sha256"],
        "external_authority": False,
    }


def _emit(value: Any, output: str) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output == "-":
        sys.stdout.write(text)
        return
    target = Path(output)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(target, flags, 0o600)
    try:
        os.write(fd, text.encode("utf-8", "strict"))
        os.fsync(fd)
    finally:
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NYS DEC Hale Creek LIMS RFI truth-gated response carrier")
    sub = parser.add_subparsers(dest="command", required=True)

    c = sub.add_parser("compile")
    c.add_argument("--source", required=True)
    c.add_argument("--output", required=True)

    v = sub.add_parser("verify")
    v.add_argument("--source", required=True)
    v.add_argument("--receipt", required=True)
    v.add_argument("--output", default="-")

    args = parser.parse_args(argv)
    try:
        if args.command == "compile":
            _emit(compile_from_path(Path(args.source)), args.output)
        else:
            _emit(verify_receipt(Path(args.source), Path(args.receipt)), args.output)
        return 0
    except (CarrierError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
