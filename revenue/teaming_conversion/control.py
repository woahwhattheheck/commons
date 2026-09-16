from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from .assets import evaluate_assets
from .common import (
    ControlError,
    canonical_bytes,
    digest_object,
    format_timestamp,
    parse_json_bytes,
    require_exact_keys,
    require_object,
    require_string,
    require_timestamp,
    sha256_bytes,
    sorted_unique,
)
from .evidence import (
    evaluate_evidence,
    select_and_validate_root,
    summarize_interpretation,
    summarize_observation,
)
from .parse import (
    RECEIPT_SCHEMA,
    ParsedRoot,
    parse_candidate,
    parse_evidence,
    parse_roots,
)
from .policy import POLICY_SHA256, policy_dict
from .qualification import evaluate_qualification
from .trusted_roots import load_current_roots_bytes

CURRENT_MODE = "CURRENT_EVIDENCE"
HISTORICAL_MODE = "HISTORICAL_INTEGRITY_ONLY"

_EXTERNAL_AUTHORITY = {
    "contact_or_send": False,
    "portal_or_provider_mutation": False,
    "proposal_or_submission": False,
    "pricing_staffing_reference_or_other_commitment": False,
    "contract_or_signature": False,
    "spend_or_payment": False,
    "award_or_acceptance_claim": False,
    "cash_or_revenue_recognition": False,
}


def _utc_now() -> datetime:
    return datetime.fromtimestamp(time.time(), tz=timezone.utc).replace(microsecond=0)


def _root_summary(root: ParsedRoot | None) -> dict[str, Any] | None:
    if root is None:
        return None
    return {
        "root_id": root.root_id,
        "opportunity_id": root.opportunity_id,
        "counterparty_ref": root.counterparty_ref,
        "thread_id": root.thread_id,
        "generation": root.generation,
        "active_from": format_timestamp(root.active_from),
        "expires_at": format_timestamp(root.expires_at),
    }


def _decision_core(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "policy_sha256": receipt["policy"]["sha256"],
        "root": receipt["trusted_root"],
        "opportunity": receipt["opportunity"],
        "current_observation": receipt["current_observation"],
        "owner_interpretation": receipt["owner_interpretation"],
        "disposition": receipt["disposition"],
        "trust_blockers": receipt["trust_blockers"],
        "qualification_blockers": receipt["qualification_blockers"],
        "asset_blockers": receipt["asset_blockers"],
        "owner_actions": receipt["owner_actions"],
        "safe_assets": receipt["safe_assets"],
        "safe_commercial_facts": receipt["safe_commercial_facts"],
        "external_authority": receipt["external_authority"],
    }


def _compile_at(
    candidate_bytes: bytes,
    evidence_bytes: bytes,
    roots_bytes: bytes,
    *,
    evaluated_at: datetime,
    mode: str,
) -> dict[str, Any]:
    if mode not in {CURRENT_MODE, HISTORICAL_MODE}:
        raise ControlError("unknown compile mode")
    now = evaluated_at.astimezone(timezone.utc).replace(microsecond=0)
    policy = policy_dict()
    candidate_value = parse_json_bytes(candidate_bytes, label="candidate")
    evidence_value = parse_json_bytes(evidence_bytes, label="retained evidence")
    roots_value = parse_json_bytes(roots_bytes, label="trusted roots")
    candidate = parse_candidate(candidate_value)
    evidence = parse_evidence(evidence_value)
    normalized_roots, roots = parse_roots(roots_value)

    root, root_blockers = select_and_validate_root(
        candidate,
        evidence,
        roots,
        evidence_bytes=evidence_bytes,
        now=now,
    )
    evidence_result = evaluate_evidence(candidate, evidence, now=now)
    asset_result = evaluate_assets(candidate, evidence, now=now)
    qualification_result = evaluate_qualification(candidate, evidence, now=now)

    asset_trust_blockers = [
        item for item in asset_result["blockers"] if item.startswith("asset_release_")
    ]
    asset_state_blockers = [
        item for item in asset_result["blockers"] if item not in asset_trust_blockers
    ]
    qualification_trust_prefixes = (
        "qualification_decision_",
        "commitment_decision_",
    )
    qualification_trust_blockers = [
        item
        for item in qualification_result["blockers"]
        if item.startswith(qualification_trust_prefixes)
    ]
    qualification_state_blockers = [
        item
        for item in qualification_result["blockers"]
        if item not in qualification_trust_blockers
    ]
    trust_blockers = sorted_unique(
        root_blockers
        + evidence_result["blockers"]
        + asset_trust_blockers
        + qualification_trust_blockers
    )
    qualification_blockers = sorted_unique(qualification_state_blockers)
    asset_blockers = sorted_unique(asset_state_blockers)

    interpretation = evidence_result["current_interpretation"]
    decision = interpretation["decision"] if interpretation is not None else None
    if trust_blockers:
        disposition = "HOLD"
    elif decision == "DECLINED":
        disposition = "DECLINED"
    elif decision in {"REQUESTED_MORE_INFO", "AMBIGUOUS"}:
        disposition = "NEEDS_CLARIFICATION"
    elif qualification_blockers:
        disposition = "QUALIFICATION_BLOCKED"
    elif asset_blockers:
        disposition = "ASSET_PREP_REQUIRED"
    elif decision in {"POSITIVE_CONTINUE", "CONDITIONAL_INTEREST"}:
        disposition = "FOLLOWUP_READY"
    else:
        disposition = "HOLD"
        trust_blockers = sorted_unique(trust_blockers + ["positive_interpretation_missing"])

    valid_until_candidates = [
        evidence_result["reply_valid_until"],
        evidence_result["source_valid_until"],
        now + timedelta(seconds=policy["max_current_receipt_age_seconds"]),
    ]
    if root is not None:
        valid_until_candidates.append(root.expires_at)
    current_valid_until = min(valid_until_candidates)

    trusted = not root_blockers
    safe_assets = asset_result["safe_assets"] if trusted else []
    safe_facts = qualification_result["safe_facts"] if trusted else []
    owner_actions = sorted_unique(
        evidence_result["owner_actions"]
        + asset_result["owner_actions"]
        + qualification_result["owner_actions"]
    )
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "mode": mode,
        "historical_integrity_only": mode == HISTORICAL_MODE,
        "evaluated_at": format_timestamp(now),
        "current_valid_until": format_timestamp(current_valid_until),
        "policy": {
            "policy_id": policy["policy_id"],
            "policy_version": policy["policy_version"],
            "sha256": POLICY_SHA256,
            "source": "repository_owned_constant",
        },
        "custody": {
            "mode": "exact_json_bytes",
            "candidate_sha256": sha256_bytes(candidate_bytes),
            "evidence_sha256": sha256_bytes(evidence_bytes),
            "trusted_roots_sha256": sha256_bytes(roots_bytes),
            "normalized_roots_sha256": digest_object(normalized_roots),
        },
        "trusted_root": _root_summary(root),
        "opportunity": {
            "opportunity_id": candidate.opportunity_id,
            "counterparty_ref": candidate.counterparty_ref,
            "thread_id": candidate.thread_id,
        },
        "current_observation": summarize_observation(evidence_result["current_observation"]),
        "owner_interpretation": summarize_interpretation(interpretation),
        "disposition": disposition,
        "trust_blockers": trust_blockers,
        "qualification_blockers": qualification_blockers,
        "asset_blockers": asset_blockers,
        "owner_actions": owner_actions,
        "safe_assets": safe_assets,
        "safe_commercial_facts": safe_facts,
        "owner_review_only": True,
        "external_authority": dict(_EXTERNAL_AUTHORITY),
    }
    receipt["decision_sha256"] = digest_object(_decision_core(receipt))
    return receipt


def compile_current_bytes(candidate_bytes: bytes, evidence_bytes: bytes) -> dict[str, Any]:
    roots_bytes = load_current_roots_bytes()
    return _compile_at(
        candidate_bytes,
        evidence_bytes,
        roots_bytes,
        evaluated_at=_utc_now(),
        mode=CURRENT_MODE,
    )


def compile_historical_bytes(
    candidate_bytes: bytes,
    evidence_bytes: bytes,
    roots_bytes: bytes,
    *,
    evaluated_at: datetime,
) -> dict[str, Any]:
    return _compile_at(
        candidate_bytes,
        evidence_bytes,
        roots_bytes,
        evaluated_at=evaluated_at,
        mode=HISTORICAL_MODE,
    )


def parse_receipt_bytes(receipt_bytes: bytes) -> dict[str, Any]:
    value = parse_json_bytes(receipt_bytes, label="receipt")
    receipt = require_object(value, "receipt")
    required = {
        "schema",
        "mode",
        "historical_integrity_only",
        "evaluated_at",
        "current_valid_until",
        "policy",
        "custody",
        "trusted_root",
        "opportunity",
        "current_observation",
        "owner_interpretation",
        "disposition",
        "trust_blockers",
        "qualification_blockers",
        "asset_blockers",
        "owner_actions",
        "safe_assets",
        "safe_commercial_facts",
        "owner_review_only",
        "external_authority",
        "decision_sha256",
    }
    require_exact_keys(receipt, required=required, label="receipt")
    if require_string(receipt["schema"], "receipt.schema", maximum=128) != RECEIPT_SCHEMA:
        raise ControlError(f"receipt.schema must be {RECEIPT_SCHEMA}")
    if require_string(receipt["mode"], "receipt.mode", maximum=64) not in {
        CURRENT_MODE,
        HISTORICAL_MODE,
    }:
        raise ControlError("receipt.mode is unknown")
    require_timestamp(receipt["evaluated_at"], "receipt.evaluated_at")
    require_timestamp(receipt["current_valid_until"], "receipt.current_valid_until")
    return receipt


def verify_integrity_bytes(
    candidate_bytes: bytes,
    evidence_bytes: bytes,
    roots_bytes: bytes,
    receipt_bytes: bytes,
) -> bool:
    receipt = parse_receipt_bytes(receipt_bytes)
    evaluated_at = require_timestamp(receipt["evaluated_at"], "receipt.evaluated_at")
    rebuilt = _compile_at(
        candidate_bytes,
        evidence_bytes,
        roots_bytes,
        evaluated_at=evaluated_at,
        mode=receipt["mode"],
    )
    return canonical_bytes(rebuilt) == receipt_bytes


def verify_current_bytes(
    candidate_bytes: bytes,
    evidence_bytes: bytes,
    receipt_bytes: bytes,
) -> dict[str, Any]:
    receipt = parse_receipt_bytes(receipt_bytes)
    now = _utc_now()
    roots_bytes = load_current_roots_bytes()
    integrity_valid = False
    if receipt["mode"] == CURRENT_MODE:
        evaluated_at = require_timestamp(receipt["evaluated_at"], "receipt.evaluated_at")
        rebuilt = _compile_at(
            candidate_bytes,
            evidence_bytes,
            roots_bytes,
            evaluated_at=evaluated_at,
            mode=CURRENT_MODE,
        )
        integrity_valid = canonical_bytes(rebuilt) == receipt_bytes
    current = _compile_at(
        candidate_bytes,
        evidence_bytes,
        roots_bytes,
        evaluated_at=now,
        mode=CURRENT_MODE,
    )
    receipt_valid_until = require_timestamp(
        receipt["current_valid_until"], "receipt.current_valid_until"
    )
    current_valid = (
        integrity_valid
        and now <= receipt_valid_until
        and current["decision_sha256"] == receipt["decision_sha256"]
    )
    return {
        "schema": "teaming-conversion-current-verification/v2",
        "verified_at": format_timestamp(now),
        "integrity_valid": integrity_valid,
        "current_valid": current_valid,
        "receipt_disposition": receipt["disposition"],
        "current_disposition": current["disposition"],
        "current_decision_sha256": current["decision_sha256"],
        "receipt_decision_sha256": receipt["decision_sha256"],
        "current_valid_until": current["current_valid_until"],
    }


def render_markdown(receipt: dict[str, Any]) -> str:
    parse_receipt_bytes(canonical_bytes(receipt))

    def literal(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    lines = [
        "# Teaming Conversion Control",
        "",
        f"- Mode: `{receipt['mode']}`",
        f"- Evaluated at: `{receipt['evaluated_at']}`",
        f"- Current-valid until: `{receipt['current_valid_until']}`",
        f"- Disposition: **{receipt['disposition']}**",
        f"- Opportunity: `{receipt['opportunity']['opportunity_id']}`",
        f"- Counterparty: `{receipt['opportunity']['counterparty_ref']}`",
        f"- Thread: `{receipt['opportunity']['thread_id']}`",
        f"- Decision SHA-256: `{receipt['decision_sha256']}`",
        "",
    ]
    if receipt["historical_integrity_only"]:
        lines.extend(
            [
                "> Historical integrity only. This output is not a current-readiness claim.",
                "",
            ]
        )
    lines.extend(["## Trust blockers", ""])
    lines.extend(
        [f"- {literal(item)}" for item in receipt["trust_blockers"]]
        or ["- None"]
    )
    lines.extend(["", "## Qualification blockers", ""])
    lines.extend(
        [f"- {literal(item)}" for item in receipt["qualification_blockers"]]
        or ["- None"]
    )
    lines.extend(["", "## Asset blockers", ""])
    lines.extend(
        [f"- {literal(item)}" for item in receipt["asset_blockers"]]
        or ["- None"]
    )
    lines.extend(["", "## Owner actions", ""])
    lines.extend([f"- {literal(item)}" for item in receipt["owner_actions"]] or ["- None"])
    lines.extend(["", "## Prospect-safe assets", ""])
    lines.extend(
        [f"- `{item['asset_id']}` — {literal(item['title'])}" for item in receipt["safe_assets"]]
        or ["- None"]
    )
    lines.extend(["", "## Safe commercial facts", ""])
    lines.extend(
        [f"- `{item['commitment_id']}` — {literal(item['safe_fact'])}" for item in receipt["safe_commercial_facts"]]
        or ["- None"]
    )
    lines.extend(
        [
            "",
            "## Authority ceiling",
            "",
            "This receipt is owner-review support only. It grants no contact, send, provider mutation, submission, commercial commitment, signature, spend, payment, award claim, cash, or revenue-recognition authority.",
            "",
        ]
    )
    return "\n".join(lines)
