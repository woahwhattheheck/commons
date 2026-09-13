from __future__ import annotations

from typing import Any

from . import _gate_base as _base

SOURCE_SCHEMA = _base.SOURCE_SCHEMA
SNAPSHOT_SCHEMA = _base.SNAPSHOT_SCHEMA
RECEIPT_SCHEMA = _base.RECEIPT_SCHEMA
PRIME_READY = _base.PRIME_READY
COLLABORATIVE_READY = _base.COLLABORATIVE_READY
HOLD = _base.HOLD
NO_BID = _base.NO_BID
AUTHORITY = _base.AUTHORITY
QualificationInputError = _base.QualificationInputError
SOURCE_MAX_AGE_SECONDS = _base.SOURCE_MAX_AGE_SECONDS
RECEIPT_MAX_AGE_SECONDS = _base.RECEIPT_MAX_AGE_SECONDS
_AUTHORITY_FALSE_FIELDS = _base._AUTHORITY_FALSE_FIELDS
_HEX64 = _base._HEX64

EXPECTED_SOURCE_CONTRACT_SHA256 = "428825eb140b6a645233f94ca390c9e4e8deaa6a9e05f2ff5895ad856c51e545"


def _bind_base() -> None:
    _base.EXPECTED_SOURCE_CONTRACT_SHA256 = EXPECTED_SOURCE_CONTRACT_SHA256


def digest(value: Any) -> str:
    return _base.digest(value)


def _load_source_contract() -> dict[str, Any]:
    _bind_base()
    return _base._load_source_contract()


def _project_snapshot(snapshot: Any, *, evaluated_at: str) -> tuple[dict[str, Any], bool]:
    snap = _base._object(snapshot, "snapshot")
    _base._keys(snap, {"schema", "source_capture", "bidder", "partners", "capability_evidence"}, "snapshot")
    source = _base._object(snap["source_capture"], "source_capture")
    _base._keys(
        source,
        {
            "bid_id",
            "document_url",
            "document_sha256",
            "captured_at",
            "updates_checked_at",
            "addenda_complete",
            "questions_answers_complete",
        },
        "source_capture",
    )
    qa_complete = _base._bool(
        source["questions_answers_complete"],
        "source_capture.questions_answers_complete",
    )
    projected_source = dict(source)
    projected_source.pop("questions_answers_complete")
    projected = dict(snap)
    projected["source_capture"] = projected_source
    _base._instant(evaluated_at, "evaluated_at")
    return projected, qa_complete


def _partner_hold_is_load_bearing(
    partner_id: str,
    *,
    snapshot: dict[str, Any],
    missing_capabilities: set[str],
    evaluated_at: str,
) -> bool:
    if not missing_capabilities:
        return False
    evaluated = _base._instant(evaluated_at, "evaluated_at")
    evidence_rows = snapshot["capability_evidence"]
    if type(evidence_rows) is not list:
        return True
    for idx, raw in enumerate(evidence_rows):
        if type(raw) is not dict or raw.get("provider_id") != partner_id:
            continue
        if raw.get("status") != "VERIFIED":
            continue
        covers = raw.get("covers")
        if type(covers) is not list or not missing_capabilities.intersection(covers):
            continue
        expires_at = raw.get("expires_at")
        if expires_at is None:
            return True
        try:
            if _base._instant(expires_at, f"capability_evidence[{idx}].expires_at") > evaluated:
                return True
        except QualificationInputError:
            return True
    return False


def _rehash_and_redecide(receipt: dict[str, Any]) -> None:
    if receipt["hard_constraints"]:
        receipt["decision"] = NO_BID
    elif receipt["holds"]:
        receipt["decision"] = HOLD
    elif receipt["partner_coverage"]:
        receipt["decision"] = COLLABORATIVE_READY
    else:
        receipt["decision"] = PRIME_READY
    receipt.pop("receipt_sha256", None)
    receipt["receipt_sha256"] = digest(receipt)


def evaluate(snapshot: Any, *, evaluated_at: str, expected_rfp_sha256: str) -> dict[str, Any]:
    _bind_base()
    projected, qa_complete = _project_snapshot(snapshot, evaluated_at=evaluated_at)
    result = _base.evaluate(
        projected,
        evaluated_at=evaluated_at,
        expected_rfp_sha256=expected_rfp_sha256,
    )
    receipt = result["receipt"]
    contract = _load_source_contract()
    evaluated = _base._instant(evaluated_at, "evaluated_at")
    qa_due = _base._instant(contract["qa_posted_by_at"], "source contract qa_posted_by_at")

    holds = set(receipt["holds"])
    if evaluated >= qa_due and not qa_complete:
        holds.add("RFP_QA_NOT_CONFIRMED_COMPLETE")

    missing = set(receipt["missing_capabilities"])
    for code in tuple(holds):
        if not code.startswith("PARTNER_NOT_COMMITTED:"):
            continue
        partner_id = code.split(":", 1)[1]
        if not _partner_hold_is_load_bearing(
            partner_id,
            snapshot=_base._object(snapshot, "snapshot"),
            missing_capabilities=missing,
            evaluated_at=evaluated_at,
        ):
            holds.remove(code)

    receipt["holds"] = sorted(holds)
    receipt["source_contract_sha256"] = EXPECTED_SOURCE_CONTRACT_SHA256
    receipt["snapshot_sha256"] = digest(snapshot)
    receipt["source_questions_answers_complete"] = qa_complete
    _rehash_and_redecide(receipt)
    return result


def verify(
    result: Any,
    *,
    snapshot: Any,
    expected_rfp_sha256: str,
    verified_at: str,
) -> bool:
    try:
        _bind_base()
        obj = _base._object(result, "result")
        _base._keys(obj, {"receipt"}, "result")
        receipt = _base._object(obj["receipt"], "receipt")
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
        expected_sha = _base._hex64(expected_rfp_sha256, "expected_rfp_sha256")
        if receipt.get("rfp_document_sha256") != expected_sha:
            return False
        if type(receipt.get("source_questions_answers_complete")) is not bool:
            return False

        verified = _base._instant(verified_at, "verified_at")
        evaluated = _base._instant(receipt["evaluated_at"], "receipt.evaluated_at")
        if verified < evaluated or (verified - evaluated).total_seconds() > RECEIPT_MAX_AGE_SECONDS:
            return False

        contract = _load_source_contract()
        deadline = _base._instant(contract["proposal_due_at"], "source contract proposal_due_at")
        if verified >= deadline:
            return False
        updates_checked = _base._instant(
            receipt["source_updates_checked_at"],
            "receipt.source_updates_checked_at",
        )
        if verified < updates_checked or (verified - updates_checked).total_seconds() > SOURCE_MAX_AGE_SECONDS:
            return False

        expected = evaluate(
            snapshot,
            evaluated_at=receipt["evaluated_at"],
            expected_rfp_sha256=expected_sha,
        )
        return _base._canonical_bytes(expected) == _base._canonical_bytes(obj)
    except (QualificationInputError, KeyError, TypeError, ValueError):
        return False
