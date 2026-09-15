from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_SCHEMA = "lawrence-youth-ai-rfp-source-contract/v1"
SNAPSHOT_SCHEMA = "lawrence-youth-ai-qualification-snapshot/v1"
RECEIPT_SCHEMA = "lawrence-youth-ai-qualification-receipt/v1"

PRIME_READY = "PRIME_READY"
COLLABORATIVE_READY = "COLLABORATIVE_READY"
HOLD = "HOLD"
NO_BID = "NO_BID"

AUTHORITY = "INTERNAL_QUALIFICATION_EVIDENCE_ONLY"
EXPECTED_SOURCE_CONTRACT_SHA256 = "9f8a9b1129c0c0479a18f323b47147b65a5b63a1804a4a62bf3993287b514a0f"
SOURCE_MAX_AGE_SECONDS = 24 * 60 * 60
RECEIPT_MAX_AGE_SECONDS = 60 * 60
MAX_JSON_BYTES = 1_048_576
MAX_ITEMS = 128
MAX_STRING_BYTES = 2048

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_EXPLICIT_TZ = re.compile(r"(?:Z|[+-][0-9]{2}:[0-9]{2})$")

_AUTHORITY_FALSE_FIELDS = (
    "proposal_submission_authorized",
    "external_contact_authorized",
    "pricing_authorized",
    "certification_signature_authorized",
    "participant_data_authorized",
    "employer_commitment_inferred",
    "contract_awarded_inferred",
    "payment_received_inferred",
    "revenue_recognized_inferred",
)


class QualificationInputError(ValueError):
    """Malformed qualification evidence."""


def _canonical_bytes(value: Any) -> bytes:
    try:
        raw = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise QualificationInputError("input must be canonical JSON data") from exc
    if len(raw) > MAX_JSON_BYTES:
        raise QualificationInputError("canonical JSON exceeds 1 MiB")
    return raw


def digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _object(value: Any, name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise QualificationInputError(f"{name} must be an object")
    return value


def _keys(value: dict[str, Any], expected: set[str], name: str) -> None:
    got = set(value)
    if got != expected:
        missing = sorted(expected - got)
        extra = sorted(got - expected)
        raise QualificationInputError(f"{name} fields mismatch; missing={missing}, extra={extra}")


def _string(value: Any, name: str, *, max_bytes: int = MAX_STRING_BYTES) -> str:
    if type(value) is not str or not value or len(value.encode("utf-8")) > max_bytes:
        raise QualificationInputError(f"{name} must be a non-empty bounded string")
    return value


def _identifier(value: Any, name: str) -> str:
    value = _string(value, name, max_bytes=128)
    if _ID.fullmatch(value) is None:
        raise QualificationInputError(f"{name} must be a canonical identifier")
    return value


def _bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise QualificationInputError(f"{name} must be boolean")
    return value


def _hex64(value: Any, name: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise QualificationInputError(f"{name} must be lowercase 64-hex SHA-256")
    return value


def _instant(value: Any, name: str) -> datetime:
    value = _string(value, name, max_bytes=64)
    if _EXPLICIT_TZ.search(value) is None:
        raise QualificationInputError(f"{name} must include an explicit UTC offset or Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise QualificationInputError(f"{name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise QualificationInputError(f"{name} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _optional_expiry(value: Any, name: str) -> datetime | None:
    return None if value is None else _instant(value, name)


def _id_list(value: Any, name: str, *, allow_empty: bool = True) -> list[str]:
    if type(value) is not list or len(value) > MAX_ITEMS or (not allow_empty and not value):
        raise QualificationInputError(f"{name} must be a bounded array")
    parsed = [_identifier(item, f"{name}[]") for item in value]
    if len(parsed) != len(set(parsed)):
        raise QualificationInputError(f"{name} contains duplicates")
    return sorted(parsed)


def _load_source_contract() -> dict[str, Any]:
    path = Path(__file__).with_name("source_contract.json")
    if path.is_symlink():
        raise QualificationInputError("source_contract.json must not be a symlink")
    raw = path.read_bytes()
    if len(raw) > MAX_JSON_BYTES:
        raise QualificationInputError("source_contract.json exceeds size limit")
    try:
        contract = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QualificationInputError("source_contract.json is malformed") from exc
    contract = _object(contract, "source contract")
    if digest(contract) != EXPECTED_SOURCE_CONTRACT_SHA256:
        raise QualificationInputError("source contract digest mismatch")
    if contract.get("schema") != SOURCE_SCHEMA:
        raise QualificationInputError("source contract schema mismatch")
    return contract


def _parse_source_capture(
    raw: Any,
    *,
    contract: dict[str, Any],
    evaluated: datetime,
    expected_rfp_sha256: str,
) -> tuple[dict[str, Any], list[str]]:
    source = _object(raw, "source_capture")
    _keys(
        source,
        {
            "bid_id",
            "document_url",
            "document_sha256",
            "captured_at",
            "updates_checked_at",
            "addenda_complete",
        },
        "source_capture",
    )
    if source["bid_id"] != contract["bid_id"]:
        raise QualificationInputError("source_capture.bid_id does not match compiled RFP")
    if source["document_url"] != contract["official_rfp_url"]:
        raise QualificationInputError("source_capture.document_url does not match compiled RFP")
    document_sha = _hex64(source["document_sha256"], "source_capture.document_sha256")
    expected_sha = _hex64(expected_rfp_sha256, "expected_rfp_sha256")
    captured = _instant(source["captured_at"], "source_capture.captured_at")
    checked = _instant(source["updates_checked_at"], "source_capture.updates_checked_at")
    if captured > evaluated or checked > evaluated:
        raise QualificationInputError("source capture/update check cannot be in the future")
    if checked < captured:
        raise QualificationInputError("updates_checked_at cannot predate captured_at")
    holds: list[str] = []
    if document_sha != expected_sha:
        holds.append("RFP_SHA256_MISMATCH")
    if not _bool(source["addenda_complete"], "source_capture.addenda_complete"):
        holds.append("RFP_UPDATES_NOT_CONFIRMED_COMPLETE")
    if (evaluated - checked).total_seconds() > SOURCE_MAX_AGE_SECONDS:
        holds.append("RFP_UPDATE_CHECK_STALE")
    return {
        "document_sha256": document_sha,
        "captured_at": source["captured_at"],
        "updates_checked_at": source["updates_checked_at"],
        "addenda_complete": source["addenda_complete"],
    }, holds


def _parse_documents(raw: Any, *, contract: dict[str, Any], evaluated: datetime) -> tuple[list[str], dict[str, str]]:
    docs = _object(raw, "bidder.documents")
    expected = set(contract["mandatory_document_requirements"])
    if set(docs) != expected:
        raise QualificationInputError(
            f"bidder.documents must cover exact mandatory document set; "
            f"missing={sorted(expected-set(docs))}, extra={sorted(set(docs)-expected)}"
        )
    missing: list[str] = []
    states: dict[str, str] = {}
    for doc_id in sorted(expected):
        item = _object(docs[doc_id], f"bidder.documents.{doc_id}")
        _keys(item, {"status", "evidence_sha256", "observed_at", "expires_at"}, f"bidder.documents.{doc_id}")
        status = _identifier(item["status"], f"bidder.documents.{doc_id}.status")
        if status not in {"READY", "PENDING", "MISSING"}:
            raise QualificationInputError(f"bidder.documents.{doc_id}.status invalid")
        evidence_sha = item["evidence_sha256"]
        if status == "READY":
            _hex64(evidence_sha, f"bidder.documents.{doc_id}.evidence_sha256")
        elif evidence_sha is not None:
            raise QualificationInputError(f"bidder.documents.{doc_id}.evidence_sha256 must be null unless READY")
        observed = _instant(item["observed_at"], f"bidder.documents.{doc_id}.observed_at")
        if observed > evaluated:
            raise QualificationInputError(f"bidder.documents.{doc_id}.observed_at is in the future")
        expires = _optional_expiry(item["expires_at"], f"bidder.documents.{doc_id}.expires_at")
        if expires is not None and expires <= observed:
            raise QualificationInputError(f"bidder.documents.{doc_id}.expires_at must be after observed_at")
        if status != "READY" or (expires is not None and expires <= evaluated):
            missing.append(doc_id)
            if status == "READY":
                states[doc_id] = "EXPIRED"
            else:
                states[doc_id] = status
        else:
            states[doc_id] = "READY"
    return sorted(missing), states


def _parse_partners(raw: Any, *, evaluated: datetime) -> dict[str, dict[str, Any]]:
    if type(raw) is not list or len(raw) > 64:
        raise QualificationInputError("partners must be a bounded array")
    partners: dict[str, dict[str, Any]] = {}
    for idx, value in enumerate(raw):
        partner = _object(value, f"partners[{idx}]")
        _keys(
            partner,
            {"partner_id", "commitment_status", "commitment_evidence_sha256", "observed_at", "expires_at"},
            f"partners[{idx}]",
        )
        partner_id = _identifier(partner["partner_id"], f"partners[{idx}].partner_id")
        if partner_id in partners:
            raise QualificationInputError("partners contains duplicate partner_id")
        status = _identifier(partner["commitment_status"], f"partners[{idx}].commitment_status")
        if status not in {"COMMITTED", "PROSPECTIVE", "DECLINED"}:
            raise QualificationInputError("partner commitment status invalid")
        commitment_sha = partner["commitment_evidence_sha256"]
        if status == "COMMITTED":
            _hex64(commitment_sha, f"partners[{idx}].commitment_evidence_sha256")
        elif commitment_sha is not None:
            raise QualificationInputError("non-committed partner must not carry commitment evidence SHA")
        observed = _instant(partner["observed_at"], f"partners[{idx}].observed_at")
        if observed > evaluated:
            raise QualificationInputError("partner commitment evidence cannot be in the future")
        expires = _optional_expiry(partner["expires_at"], f"partners[{idx}].expires_at")
        if expires is not None and expires <= observed:
            raise QualificationInputError("partner commitment expiry must be after observation")
        effective = status
        if status == "COMMITTED" and expires is not None and expires <= evaluated:
            effective = "EXPIRED"
        partners[partner_id] = {
            "status": effective,
            "commitment_status": status,
            "observed_at": partner["observed_at"],
            "expires_at": partner["expires_at"],
        }
    return partners


def _parse_capability_evidence(
    raw: Any,
    *,
    bidder_id: str,
    partners: dict[str, dict[str, Any]],
    contract: dict[str, Any],
    evaluated: datetime,
) -> tuple[dict[str, list[str]], list[str], list[str]]:
    if type(raw) is not list or not raw or len(raw) > MAX_ITEMS:
        raise QualificationInputError("capability_evidence must be a non-empty bounded array")
    allowed = set(contract["capability_requirements"])
    evidence_ids: set[str] = set()
    providers = {bidder_id, *partners}
    coverage: dict[str, list[str]] = {cap: [] for cap in sorted(allowed)}
    pending_partner_holds: set[str] = set()
    stale_caps: set[str] = set()
    for idx, value in enumerate(raw):
        evidence = _object(value, f"capability_evidence[{idx}]")
        _keys(
            evidence,
            {"evidence_id", "provider_id", "covers", "status", "evidence_sha256", "observed_at", "expires_at"},
            f"capability_evidence[{idx}]",
        )
        evidence_id = _identifier(evidence["evidence_id"], f"capability_evidence[{idx}].evidence_id")
        if evidence_id in evidence_ids:
            raise QualificationInputError("capability_evidence contains duplicate evidence_id")
        evidence_ids.add(evidence_id)
        provider_id = _identifier(evidence["provider_id"], f"capability_evidence[{idx}].provider_id")
        if provider_id not in providers:
            raise QualificationInputError("capability evidence provider is not bidder or declared partner")
        covers = _id_list(evidence["covers"], f"capability_evidence[{idx}].covers", allow_empty=False)
        unknown = set(covers) - allowed
        if unknown:
            raise QualificationInputError(f"capability evidence covers unknown requirements: {sorted(unknown)}")
        status = _identifier(evidence["status"], f"capability_evidence[{idx}].status")
        if status not in {"VERIFIED", "PENDING", "UNAVAILABLE"}:
            raise QualificationInputError("capability evidence status invalid")
        evidence_sha = evidence["evidence_sha256"]
        if status == "VERIFIED":
            _hex64(evidence_sha, f"capability_evidence[{idx}].evidence_sha256")
        elif evidence_sha is not None:
            raise QualificationInputError("non-VERIFIED capability evidence must not carry evidence SHA")
        observed = _instant(evidence["observed_at"], f"capability_evidence[{idx}].observed_at")
        if observed > evaluated:
            raise QualificationInputError("capability evidence cannot be observed in the future")
        expires = _optional_expiry(evidence["expires_at"], f"capability_evidence[{idx}].expires_at")
        if expires is not None and expires <= observed:
            raise QualificationInputError("capability evidence expiry must be after observation")
        active = status == "VERIFIED" and (expires is None or expires > evaluated)
        if status == "VERIFIED" and not active:
            stale_caps.update(covers)
        if not active:
            continue
        if provider_id != bidder_id:
            partner_status = partners[provider_id]["status"]
            if partner_status != "COMMITTED":
                pending_partner_holds.add(provider_id)
                continue
        for cap in covers:
            coverage[cap].append(provider_id)
    for cap in coverage:
        coverage[cap] = sorted(set(coverage[cap]))
    return coverage, sorted(pending_partner_holds), sorted(stale_caps)


def _parse_snapshot(
    raw: Any,
    *,
    contract: dict[str, Any],
    evaluated: datetime,
    expected_rfp_sha256: str,
) -> dict[str, Any]:
    snap = _object(raw, "snapshot")
    _keys(snap, {"schema", "source_capture", "bidder", "partners", "capability_evidence"}, "snapshot")
    if snap["schema"] != SNAPSHOT_SCHEMA:
        raise QualificationInputError("unsupported snapshot schema")

    source, source_holds = _parse_source_capture(
        snap["source_capture"],
        contract=contract,
        evaluated=evaluated,
        expected_rfp_sha256=expected_rfp_sha256,
    )

    bidder = _object(snap["bidder"], "bidder")
    _keys(bidder, {"bidder_id", "organization_type", "hard_constraints", "documents"}, "bidder")
    bidder_id = _identifier(bidder["bidder_id"], "bidder.bidder_id")
    organization_type = _identifier(bidder["organization_type"], "bidder.organization_type")
    if organization_type not in {"CORPORATE", "NON_CORPORATE"}:
        raise QualificationInputError("bidder.organization_type must be CORPORATE or NON_CORPORATE")
    hard_constraints = _id_list(bidder["hard_constraints"], "bidder.hard_constraints")
    missing_documents, document_states = _parse_documents(
        bidder["documents"], contract=contract, evaluated=evaluated
    )
    partners = _parse_partners(snap["partners"], evaluated=evaluated)
    if bidder_id in partners:
        raise QualificationInputError("bidder_id cannot also be a partner_id")
    coverage, partner_holds, stale_caps = _parse_capability_evidence(
        snap["capability_evidence"],
        bidder_id=bidder_id,
        partners=partners,
        contract=contract,
        evaluated=evaluated,
    )
    return {
        "source": source,
        "source_holds": source_holds,
        "bidder_id": bidder_id,
        "organization_type": organization_type,
        "hard_constraints": hard_constraints,
        "missing_documents": missing_documents,
        "document_states": document_states,
        "partners": partners,
        "coverage": coverage,
        "partner_holds": partner_holds,
        "stale_caps": stale_caps,
    }


def evaluate(snapshot: Any, *, evaluated_at: str, expected_rfp_sha256: str) -> dict[str, Any]:
    contract = _load_source_contract()
    evaluated = _instant(evaluated_at, "evaluated_at")
    released = _instant(contract["released_at"], "source contract released_at")
    deadline = _instant(contract["proposal_due_at"], "source contract proposal_due_at")
    if evaluated < released:
        raise QualificationInputError("evaluated_at cannot predate RFP release")

    parsed = _parse_snapshot(
        snapshot,
        contract=contract,
        evaluated=evaluated,
        expected_rfp_sha256=expected_rfp_sha256,
    )

    holds: set[str] = set(parsed["source_holds"])
    for doc_id in parsed["missing_documents"]:
        holds.add(f"DOCUMENT_NOT_READY:{doc_id}")
    for partner_id in parsed["partner_holds"]:
        holds.add(f"PARTNER_NOT_COMMITTED:{partner_id}")

    missing_caps = [cap for cap, providers in parsed["coverage"].items() if not providers]
    for cap in missing_caps:
        holds.add(f"CAPABILITY_NOT_COVERED:{cap}")
    for cap in parsed["stale_caps"]:
        if cap in missing_caps:
            holds.add(f"CAPABILITY_EVIDENCE_EXPIRED:{cap}")

    hard_constraints = parsed["hard_constraints"]
    if evaluated >= deadline:
        hard_constraints = sorted(set(hard_constraints) | {"PROPOSAL_DEADLINE_PASSED"})

    partner_coverage: dict[str, list[str]] = {}
    bidder_coverage: list[str] = []
    for cap, providers in parsed["coverage"].items():
        if parsed["bidder_id"] in providers:
            bidder_coverage.append(cap)
        for provider in providers:
            if provider != parsed["bidder_id"]:
                partner_coverage.setdefault(provider, []).append(cap)
    bidder_coverage.sort()
    for provider in partner_coverage:
        partner_coverage[provider].sort()

    if hard_constraints:
        decision = NO_BID
    elif holds:
        decision = HOLD
    elif partner_coverage:
        decision = COLLABORATIVE_READY
    else:
        decision = PRIME_READY

    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "decision": decision,
        "authority": AUTHORITY,
        "bid_id": contract["bid_id"],
        "bidder_id": parsed["bidder_id"],
        "organization_type": parsed["organization_type"],
        "evaluated_at": evaluated_at,
        "proposal_due_at": contract["proposal_due_at"],
        "source_contract_sha256": EXPECTED_SOURCE_CONTRACT_SHA256,
        "snapshot_sha256": digest(snapshot),
        "rfp_document_sha256": parsed["source"]["document_sha256"],
        "source_updates_checked_at": parsed["source"]["updates_checked_at"],
        "source_addenda_complete": parsed["source"]["addenda_complete"],
        "holds": sorted(holds),
        "hard_constraints": hard_constraints,
        "missing_documents": parsed["missing_documents"],
        "missing_capabilities": sorted(missing_caps),
        "bidder_coverage": bidder_coverage,
        "partner_coverage": {key: partner_coverage[key] for key in sorted(partner_coverage)},
        "document_states": {key: parsed["document_states"][key] for key in sorted(parsed["document_states"])},
        "scoring_sections": {
            key: contract["scoring_sections"][key] for key in sorted(contract["scoring_sections"])
        },
        "collaborative_proposals_strongly_encouraged": contract["collaborative_proposals_strongly_encouraged"],
        "proposal_submission_authorized": False,
        "external_contact_authorized": False,
        "pricing_authorized": False,
        "certification_signature_authorized": False,
        "participant_data_authorized": False,
        "employer_commitment_inferred": False,
        "contract_awarded_inferred": False,
        "payment_received_inferred": False,
        "revenue_recognized_inferred": False,
    }
    receipt["receipt_sha256"] = digest(receipt)
    return {"receipt": receipt}


def verify(
    result: Any,
    *,
    snapshot: Any,
    expected_rfp_sha256: str,
    verified_at: str,
) -> bool:
    try:
        obj = _object(result, "result")
        _keys(obj, {"receipt"}, "result")
        receipt = _object(obj["receipt"], "receipt")
        if receipt.get("schema") != RECEIPT_SCHEMA or receipt.get("authority") != AUTHORITY:
            return False
        for field in _AUTHORITY_FALSE_FIELDS:
            if receipt.get(field) is not False:
                return False
        supplied_hash = receipt.get("receipt_sha256")
        if type(supplied_hash) is not str or _HEX64.fullmatch(supplied_hash) is None:
            return False
        core = dict(receipt)
        core.pop("receipt_sha256", None)
        if digest(core) != supplied_hash:
            return False
        if receipt.get("source_contract_sha256") != EXPECTED_SOURCE_CONTRACT_SHA256:
            return False
        expected_sha = _hex64(expected_rfp_sha256, "expected_rfp_sha256")
        if receipt.get("rfp_document_sha256") != expected_sha:
            return False

        verified = _instant(verified_at, "verified_at")
        evaluated = _instant(receipt["evaluated_at"], "receipt.evaluated_at")
        if verified < evaluated:
            return False
        if (verified - evaluated).total_seconds() > RECEIPT_MAX_AGE_SECONDS:
            return False

        contract = _load_source_contract()
        deadline = _instant(contract["proposal_due_at"], "source contract proposal_due_at")
        if verified >= deadline:
            return False
        updates_checked = _instant(
            receipt["source_updates_checked_at"], "receipt.source_updates_checked_at"
        )
        if verified < updates_checked:
            return False
        if (verified - updates_checked).total_seconds() > SOURCE_MAX_AGE_SECONDS:
            return False

        expected = evaluate(
            snapshot,
            evaluated_at=receipt["evaluated_at"],
            expected_rfp_sha256=expected_sha,
        )
        return _canonical_bytes(expected) == _canonical_bytes(obj)
    except (QualificationInputError, KeyError, TypeError, ValueError):
        return False
