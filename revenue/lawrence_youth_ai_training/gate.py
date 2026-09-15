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

EXPECTED_SOURCE_CONTRACT_SHA256 = "9f9176b1747389c2c5a982e3fe459f6db2465b0244099fc8e625239236d7116e"
GOOD_STANDING_DOCUMENT = "certificate_good_standing"
AUDIT_DOCUMENT = "audit_assurance_certification"
_SEMANTIC_DOCUMENTS = frozenset({GOOD_STANDING_DOCUMENT, AUDIT_DOCUMENT})


def _bind_base() -> None:
    _base.EXPECTED_SOURCE_CONTRACT_SHA256 = EXPECTED_SOURCE_CONTRACT_SHA256


def digest(value: Any) -> str:
    return _base.digest(value)


def _load_source_contract() -> dict[str, Any]:
    _bind_base()
    return _base._load_source_contract()


def _project_snapshot(
    snapshot: Any,
    *,
    evaluated_at: str,
) -> tuple[dict[str, Any], bool, dict[str, Any | None]]:
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

    bidder = _base._object(snap["bidder"], "bidder")
    documents = _base._object(bidder.get("documents"), "bidder.documents")
    projected_documents: dict[str, Any] = {}
    semantic_authority: dict[str, Any | None] = {doc_id: None for doc_id in _SEMANTIC_DOCUMENTS}
    for doc_id, raw in documents.items():
        item = _base._object(raw, f"bidder.documents.{doc_id}")
        projected_item = dict(item)
        supplied = projected_item.pop("semantic_authority", None)
        if supplied is not None:
            if doc_id not in _SEMANTIC_DOCUMENTS:
                raise QualificationInputError(
                    f"bidder.documents.{doc_id}.semantic_authority is not compiled for this document"
                )
            semantic_authority[doc_id] = supplied
        projected_documents[doc_id] = projected_item

    projected_bidder = dict(bidder)
    projected_bidder["documents"] = projected_documents
    projected = dict(snap)
    projected["source_capture"] = projected_source
    projected["bidder"] = projected_bidder
    _base._instant(evaluated_at, "evaluated_at")
    return projected, qa_complete, semantic_authority


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


def _semantic_document_holds(
    *,
    snapshot: dict[str, Any],
    semantic_authority: dict[str, Any | None],
    contract: dict[str, Any],
    evaluated_at: str,
) -> tuple[set[str], dict[str, str]]:
    evaluated = _base._instant(evaluated_at, "evaluated_at")
    bidder = _base._object(snapshot["bidder"], "bidder")
    documents = _base._object(bidder["documents"], "bidder.documents")
    policies = _base._object(
        contract.get("document_semantic_requirements"),
        "source contract document_semantic_requirements",
    )
    if set(policies) != set(_SEMANTIC_DOCUMENTS):
        raise QualificationInputError("compiled document semantic requirement set mismatch")

    holds: set[str] = set()
    states: dict[str, str] = {}
    for doc_id in sorted(_SEMANTIC_DOCUMENTS):
        document = _base._object(documents[doc_id], f"bidder.documents.{doc_id}")
        if document.get("status") != "READY":
            states[doc_id] = "NOT_READY"
            continue
        authority = semantic_authority.get(doc_id)
        if authority is None:
            holds.add(f"DOCUMENT_SEMANTICS_UNVERIFIED:{doc_id}")
            states[doc_id] = "UNVERIFIED"
            continue
        authority = _base._object(authority, f"bidder.documents.{doc_id}.semantic_authority")
        document_sha = _base._hex64(
            authority.get("document_evidence_sha256"),
            f"bidder.documents.{doc_id}.semantic_authority.document_evidence_sha256",
        )
        proof_sha = _base._hex64(
            authority.get("verification_evidence_sha256"),
            f"bidder.documents.{doc_id}.semantic_authority.verification_evidence_sha256",
        )
        del proof_sha  # Validation/binding only; receipt stores the derived state, snapshot hash binds the proof.
        if document_sha != document.get("evidence_sha256"):
            holds.add(f"DOCUMENT_SEMANTICS_EVIDENCE_MISMATCH:{doc_id}")
            states[doc_id] = "EVIDENCE_MISMATCH"
            continue

        policy = _base._object(policies[doc_id], f"source contract semantic policy {doc_id}")
        if doc_id == GOOD_STANDING_DOCUMENT:
            _base._keys(
                authority,
                {
                    "semantic_kind",
                    "document_evidence_sha256",
                    "issuer",
                    "issued_at",
                    "verified_at",
                    "verification_evidence_sha256",
                },
                f"bidder.documents.{doc_id}.semantic_authority",
            )
            _base._keys(
                policy,
                {"semantic_kind", "issuer", "max_issue_age_days", "max_verification_age_hours"},
                f"source contract semantic policy {doc_id}",
            )
            kind = _base._string(authority["semantic_kind"], f"bidder.documents.{doc_id}.semantic_authority.semantic_kind")
            issuer = _base._string(authority["issuer"], f"bidder.documents.{doc_id}.semantic_authority.issuer")
            issued = _base._instant(authority["issued_at"], f"bidder.documents.{doc_id}.semantic_authority.issued_at")
            verified = _base._instant(authority["verified_at"], f"bidder.documents.{doc_id}.semantic_authority.verified_at")
            if issued > verified or verified > evaluated:
                raise QualificationInputError("Good Standing semantic authority timestamps are future/inverted")
            if kind != policy["semantic_kind"]:
                holds.add(f"DOCUMENT_SEMANTIC_KIND_MISMATCH:{doc_id}")
                states[doc_id] = "KIND_MISMATCH"
            elif issuer != policy["issuer"]:
                holds.add(f"DOCUMENT_ISSUER_MISMATCH:{doc_id}")
                states[doc_id] = "ISSUER_MISMATCH"
            elif (evaluated - issued).total_seconds() > policy["max_issue_age_days"] * 86400:
                holds.add(f"DOCUMENT_NOT_CURRENT:{doc_id}")
                states[doc_id] = "STALE_ISSUANCE"
            elif (evaluated - verified).total_seconds() > policy["max_verification_age_hours"] * 3600:
                holds.add(f"DOCUMENT_SEMANTIC_VERIFICATION_STALE:{doc_id}")
                states[doc_id] = "STALE_VERIFICATION"
            else:
                states[doc_id] = "VERIFIED_CURRENT"
        else:
            _base._keys(
                authority,
                {
                    "semantic_kind",
                    "document_evidence_sha256",
                    "period_end_at",
                    "most_recent",
                    "verified_at",
                    "verification_evidence_sha256",
                },
                f"bidder.documents.{doc_id}.semantic_authority",
            )
            _base._keys(
                policy,
                {"semantic_kind", "max_verification_age_hours"},
                f"source contract semantic policy {doc_id}",
            )
            kind = _base._string(authority["semantic_kind"], f"bidder.documents.{doc_id}.semantic_authority.semantic_kind")
            period_end = _base._instant(authority["period_end_at"], f"bidder.documents.{doc_id}.semantic_authority.period_end_at")
            most_recent = _base._bool(authority["most_recent"], f"bidder.documents.{doc_id}.semantic_authority.most_recent")
            verified = _base._instant(authority["verified_at"], f"bidder.documents.{doc_id}.semantic_authority.verified_at")
            if period_end > verified or verified > evaluated:
                raise QualificationInputError("audit semantic authority timestamps are future/inverted")
            if kind != policy["semantic_kind"]:
                holds.add(f"DOCUMENT_SEMANTIC_KIND_MISMATCH:{doc_id}")
                states[doc_id] = "KIND_MISMATCH"
            elif not most_recent:
                holds.add(f"DOCUMENT_NOT_MOST_RECENT:{doc_id}")
                states[doc_id] = "NOT_MOST_RECENT"
            elif (evaluated - verified).total_seconds() > policy["max_verification_age_hours"] * 3600:
                holds.add(f"DOCUMENT_SEMANTIC_VERIFICATION_STALE:{doc_id}")
                states[doc_id] = "STALE_VERIFICATION"
            else:
                states[doc_id] = "VERIFIED_MOST_RECENT"
    return holds, states


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
    contract = _load_source_contract()
    projected, qa_complete, semantic_authority = _project_snapshot(snapshot, evaluated_at=evaluated_at)
    result = _base.evaluate(
        projected,
        evaluated_at=evaluated_at,
        expected_rfp_sha256=expected_rfp_sha256,
    )
    receipt = result["receipt"]
    evaluated = _base._instant(evaluated_at, "evaluated_at")
    qa_due = _base._instant(contract["qa_posted_by_at"], "source contract qa_posted_by_at")

    holds = set(receipt["holds"])
    if evaluated >= qa_due and not qa_complete:
        holds.add("RFP_QA_NOT_CONFIRMED_COMPLETE")

    semantic_holds, semantic_states = _semantic_document_holds(
        snapshot=_base._object(snapshot, "snapshot"),
        semantic_authority=semantic_authority,
        contract=contract,
        evaluated_at=evaluated_at,
    )
    holds.update(semantic_holds)

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
    receipt["document_semantic_states"] = semantic_states
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
        semantic_states = receipt.get("document_semantic_states")
        if type(semantic_states) is not dict or set(semantic_states) != set(_SEMANTIC_DOCUMENTS):
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
