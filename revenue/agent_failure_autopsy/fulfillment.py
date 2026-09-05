#!/usr/bin/env python3
"""Validate one Agent Failure Autopsy intake/report bundle.

This validator is standard-library only. It enforces the cross-document rules
that JSON Schema cannot express: clock derivation, evidence-anchor integrity,
diagnosis/refund branching, final review, and per-delivery operator-time truth.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

INTAKE_VERSION = "commons-agent-failure-autopsy-intake/v1"
REPORT_VERSION = "commons-agent-failure-autopsy-report/v1"
OFFER_ID = "agent-failure-autopsy-29"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$")
BUYER_RE = re.compile(r"^buyer_[a-f0-9]{16,64}$")
REVIEWER_RE = re.compile(r"^reviewer_[a-f0-9]{16,64}$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
REF_RE = re.compile(
    r"^(?P<evidence>[A-Za-z0-9][A-Za-z0-9._-]{2,79})#"
    r"(?P<anchor>[A-Za-z0-9][A-Za-z0-9._-]{2,79})$"
)
ACCESS_KEYS = {
    "secrets_requested",
    "unredacted_credentials_requested",
    "production_access_requested",
    "repository_access_requested",
}


class AutopsyValidationError(ValueError):
    """The bundle is internally inconsistent or outside the offer contract."""


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise AutopsyValidationError(f"{path}: top level must be an object")
    return value


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise AutopsyValidationError(f"{label} must be an object")
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise AutopsyValidationError(
            f"{label} keys differ: missing={missing} extra={extra}"
        )
    return value


def _text(value: Any, label: str, *, minimum: int = 1, maximum: int = 1000) -> str:
    if type(value) is not str or not minimum <= len(value) <= maximum:
        raise AutopsyValidationError(
            f"{label} must be text with length {minimum}..{maximum}"
        )
    return value


def _nullable_text(value: Any, label: str, *, maximum: int = 1000) -> str | None:
    if value is None:
        return None
    return _text(value, label, maximum=maximum)


def _id(value: Any, label: str) -> str:
    if type(value) is not str or not ID_RE.fullmatch(value):
        raise AutopsyValidationError(f"{label} is not a valid opaque id")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or not SHA_RE.fullmatch(value):
        raise AutopsyValidationError(f"{label} is not a lowercase SHA-256")
    return value


def _time(value: Any, label: str) -> datetime:
    if type(value) is not str or not re.search(r"(?:Z|[+-]\d{2}:\d{2})$", value):
        raise AutopsyValidationError(f"{label} must be an offset-aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AutopsyValidationError(f"{label} is not a valid timestamp") from exc
    if parsed.tzinfo is None:
        raise AutopsyValidationError(f"{label} must carry a UTC offset")
    return parsed


def _nullable_time(value: Any, label: str) -> datetime | None:
    if value is None:
        return None
    return _time(value, label)


def _number(value: Any, label: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise AutopsyValidationError(f"{label} must be a number")
    if not 0 <= float(value) <= 1440:
        raise AutopsyValidationError(f"{label} must be between 0 and 1440")
    return float(value)


def _string_list(
    value: Any,
    label: str,
    *,
    allow_empty: bool,
    maximum_items: int = 100,
) -> list[str]:
    if type(value) is not list or len(value) > maximum_items:
        raise AutopsyValidationError(f"{label} must be a bounded list")
    if not allow_empty and not value:
        raise AutopsyValidationError(f"{label} must not be empty")
    for index, item in enumerate(value):
        _text(item, f"{label}[{index}]")
    return value


def next_business_day(timestamp: str) -> str:
    """Return the same wall-clock time on the next Monday through Friday."""
    current = _time(timestamp, "timestamp")
    candidate = current + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate.isoformat()


def validate_intake(intake: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(
        intake,
        {
            "schema_version",
            "kind",
            "record_classification",
            "case_id",
            "buyer_ref",
            "failure_sentence",
            "harness_stack",
            "submitted_at",
            "evidence",
            "evidence_assessment",
            "clarification",
            "access_boundary",
        },
        "intake",
    )
    if intake["schema_version"] != INTAKE_VERSION:
        raise AutopsyValidationError("intake schema_version is invalid")
    if intake["kind"] != "AGENT_FAILURE_AUTOPSY_INTAKE":
        raise AutopsyValidationError("intake kind is invalid")
    classification = intake["record_classification"]
    if classification not in {"BUYER_CASE", "SYNTHETIC_EXAMPLE"}:
        raise AutopsyValidationError("intake record_classification is invalid")
    case_id = _id(intake["case_id"], "intake.case_id")
    if type(intake["buyer_ref"]) is not str or not BUYER_RE.fullmatch(
        intake["buyer_ref"]
    ):
        raise AutopsyValidationError("intake.buyer_ref is not opaque")
    _text(intake["failure_sentence"], "intake.failure_sentence", minimum=10)
    submitted_at = _time(intake["submitted_at"], "intake.submitted_at")

    stack = _exact_keys(
        intake["harness_stack"],
        {
            "harness",
            "harness_version",
            "model",
            "operating_system",
            "runtime",
            "tooling",
        },
        "intake.harness_stack",
    )
    if stack["harness"] not in {"codex", "claude-code", "other-coding-agent"}:
        raise AutopsyValidationError("intake harness is outside the coding-agent offer")
    for key in ("harness_version", "model", "operating_system", "runtime"):
        _nullable_text(stack[key], f"intake.harness_stack.{key}", maximum=500)
    tooling = _string_list(
        stack["tooling"], "intake.harness_stack.tooling", allow_empty=True, maximum_items=20
    )
    if len(set(tooling)) != len(tooling):
        raise AutopsyValidationError("intake tooling entries must be unique")

    evidence = intake["evidence"]
    if type(evidence) is not list or not 1 <= len(evidence) <= 20:
        raise AutopsyValidationError("intake.evidence must contain 1..20 artifacts")
    received_by_id: dict[str, datetime] = {}
    locations_by_id: dict[str, str] = {}
    hashes_by_id: dict[str, str] = {}
    anchor_refs: set[str] = set()
    for index, item in enumerate(evidence):
        item = _exact_keys(
            item,
            {
                "evidence_id",
                "kind",
                "location_ref",
                "sha256",
                "redacted",
                "received_at",
                "anchors",
            },
            f"intake.evidence[{index}]",
        )
        evidence_id = _id(item["evidence_id"], f"intake.evidence[{index}].evidence_id")
        if evidence_id in received_by_id:
            raise AutopsyValidationError(f"duplicate evidence id: {evidence_id}")
        if item["kind"] not in {"transcript", "log", "screenshot"}:
            raise AutopsyValidationError(f"{evidence_id}: unsupported evidence kind")
        location = _text(
            item["location_ref"], f"{evidence_id}.location_ref", maximum=240
        )
        expected_prefix = "private:" if classification == "BUYER_CASE" else "example:"
        if not location.startswith(expected_prefix):
            raise AutopsyValidationError(
                f"{evidence_id}: {classification} evidence must use {expected_prefix}"
            )
        relative = location.split(":", 1)[1]
        if (
            not relative
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
            or "\\" in relative
        ):
            raise AutopsyValidationError(f"{evidence_id}: unsafe evidence location")
        if item["redacted"] is not True:
            raise AutopsyValidationError(f"{evidence_id}: evidence must be redacted")
        hashes_by_id[evidence_id] = _sha(item["sha256"], f"{evidence_id}.sha256")
        received = _time(item["received_at"], f"{evidence_id}.received_at")
        if received < submitted_at:
            raise AutopsyValidationError(
                f"{evidence_id}: received_at precedes submitted_at"
            )
        received_by_id[evidence_id] = received
        locations_by_id[evidence_id] = location

        anchors = item["anchors"]
        if type(anchors) is not list or not 1 <= len(anchors) <= 100:
            raise AutopsyValidationError(f"{evidence_id}: anchors must contain 1..100 items")
        local_ids: set[str] = set()
        for anchor_index, anchor in enumerate(anchors):
            anchor = _exact_keys(
                anchor,
                {"anchor_id", "description"},
                f"{evidence_id}.anchors[{anchor_index}]",
            )
            anchor_id = _id(anchor["anchor_id"], f"{evidence_id}.anchor_id")
            if anchor_id in local_ids:
                raise AutopsyValidationError(
                    f"{evidence_id}: duplicate anchor id {anchor_id}"
                )
            local_ids.add(anchor_id)
            _text(anchor["description"], f"{evidence_id}#{anchor_id}.description")
            anchor_refs.add(f"{evidence_id}#{anchor_id}")

    assessment = _exact_keys(
        intake["evidence_assessment"],
        {
            "state",
            "assessed_at",
            "clock_basis_evidence_ids",
            "usable_evidence_at",
            "delivery_due_at",
            "reasons",
        },
        "intake.evidence_assessment",
    )
    state = assessment["state"]
    if state not in {
        "USABLE",
        "CLARIFICATION_REQUESTED",
        "INSUFFICIENT_AFTER_CLARIFICATION",
    }:
        raise AutopsyValidationError("intake evidence assessment state is invalid")
    assessed_at = _time(assessment["assessed_at"], "intake.evidence_assessment.assessed_at")
    if assessed_at < max(received_by_id.values()):
        raise AutopsyValidationError("intake was assessed before its latest evidence arrived")
    basis = assessment["clock_basis_evidence_ids"]
    if type(basis) is not list or len(set(basis)) != len(basis):
        raise AutopsyValidationError("clock basis evidence ids must be a unique list")
    for evidence_id in basis:
        if evidence_id not in received_by_id:
            raise AutopsyValidationError(f"unknown clock-basis evidence id: {evidence_id}")
    reasons = _string_list(
        assessment["reasons"],
        "intake.evidence_assessment.reasons",
        allow_empty=state == "USABLE",
        maximum_items=20,
    )
    usable_at = _nullable_time(
        assessment["usable_evidence_at"],
        "intake.evidence_assessment.usable_evidence_at",
    )
    due_at = _nullable_time(
        assessment["delivery_due_at"],
        "intake.evidence_assessment.delivery_due_at",
    )

    clarification = _exact_keys(
        intake["clarification"],
        {"rounds_used", "question", "response_received_at", "response_evidence_ids"},
        "intake.clarification",
    )
    rounds = clarification["rounds_used"]
    if type(rounds) is not int or isinstance(rounds, bool) or rounds not in {0, 1}:
        raise AutopsyValidationError("exactly zero or one clarification round is allowed")
    question = _nullable_text(
        clarification["question"], "intake.clarification.question"
    )
    response_at = _nullable_time(
        clarification["response_received_at"],
        "intake.clarification.response_received_at",
    )
    response_ids = clarification["response_evidence_ids"]
    if type(response_ids) is not list or len(set(response_ids)) != len(response_ids):
        raise AutopsyValidationError("clarification response evidence ids must be unique")
    for evidence_id in response_ids:
        if evidence_id not in received_by_id:
            raise AutopsyValidationError(
                f"unknown clarification response evidence id: {evidence_id}"
            )
    if rounds == 0 and (question is not None or response_at is not None or response_ids):
        raise AutopsyValidationError("unused clarification round must have no question or response")
    if rounds == 1:
        if question is None:
            raise AutopsyValidationError("used clarification round requires the bundled question")
        if state == "CLARIFICATION_REQUESTED":
            if response_at is not None or response_ids:
                raise AutopsyValidationError(
                    "pending clarification cannot claim a received response"
                )
        else:
            if response_at is None or not response_ids:
                raise AutopsyValidationError(
                    "completed clarification requires response time and evidence"
                )
            if response_at != max(received_by_id[item] for item in response_ids):
                raise AutopsyValidationError(
                    "clarification response time must equal its latest evidence arrival"
                )

    boundary = _exact_keys(intake["access_boundary"], ACCESS_KEYS, "intake.access_boundary")
    if any(boundary[key] is not False for key in ACCESS_KEYS):
        raise AutopsyValidationError(
            "this offer never requests secrets, unredacted credentials, production, or repo access"
        )

    if state == "USABLE":
        if not basis or usable_at is None or due_at is None:
            raise AutopsyValidationError("usable evidence must start and bound the delivery clock")
        expected_usable = max(received_by_id[item] for item in basis)
        if usable_at != expected_usable:
            raise AutopsyValidationError(
                "usable_evidence_at must equal the latest clock-basis artifact arrival"
            )
        expected_due = _time(
            next_business_day(assessment["usable_evidence_at"]), "expected delivery due"
        )
        if due_at != expected_due:
            raise AutopsyValidationError(
                "delivery_due_at must be the next weekday at the same local wall-clock time"
            )
    else:
        if basis or usable_at is not None or due_at is not None:
            raise AutopsyValidationError(
                "the delivery clock cannot start before evidence is usable"
            )
        if state == "CLARIFICATION_REQUESTED" and rounds != 1:
            raise AutopsyValidationError(
                "clarification-requested state must consume the one included round"
            )
        if state == "INSUFFICIENT_AFTER_CLARIFICATION" and rounds != 1:
            raise AutopsyValidationError(
                "insufficient-after-clarification requires the included round"
            )
    return {
        "classification": classification,
        "case_id": case_id,
        "state": state,
        "rounds": rounds,
        "anchor_refs": anchor_refs,
        "evidence_ids": set(received_by_id),
        "locations_by_id": locations_by_id,
        "hashes_by_id": hashes_by_id,
        "usable_at": usable_at,
        "due_at": due_at,
        "reasons": reasons,
    }


def _validate_refs(value: Any, allowed: set[str], label: str) -> list[str]:
    if type(value) is not list or not value:
        raise AutopsyValidationError(f"{label} must contain evidence anchors")
    if len(set(value)) != len(value):
        raise AutopsyValidationError(f"{label} contains duplicate evidence anchors")
    for ref in value:
        if type(ref) is not str or not REF_RE.fullmatch(ref):
            raise AutopsyValidationError(f"{label}: malformed evidence reference {ref!r}")
        if ref not in allowed:
            raise AutopsyValidationError(f"{label}: unknown evidence reference {ref}")
    return value


def _observed_items(value: Any, allowed: set[str], label: str) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise AutopsyValidationError(f"{label} must be a list")
    expected_sequence = 1
    for index, item in enumerate(value):
        item = _exact_keys(
            item,
            {"sequence", "claim_type", "statement", "evidence_refs"},
            f"{label}[{index}]",
        )
        if item["sequence"] != expected_sequence:
            raise AutopsyValidationError(f"{label} sequence must be contiguous from 1")
        expected_sequence += 1
        if item["claim_type"] != "OBSERVED":
            raise AutopsyValidationError(f"{label} facts must be marked OBSERVED")
        _text(item["statement"], f"{label}[{index}].statement")
        _validate_refs(item["evidence_refs"], allowed, f"{label}[{index}].evidence_refs")
    return value


def _cause_list(
    value: Any,
    allowed: set[str],
    label: str,
    seen_ids: set[str],
) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise AutopsyValidationError(f"{label} must be a list")
    for index, cause in enumerate(value):
        cause = _exact_keys(
            cause,
            {
                "cause_id",
                "claim_type",
                "statement",
                "confidence",
                "confidence_rationale",
                "evidence_refs",
                "alternatives",
            },
            f"{label}[{index}]",
        )
        cause_id = _id(cause["cause_id"], f"{label}[{index}].cause_id")
        if cause_id in seen_ids:
            raise AutopsyValidationError(f"duplicate cause id: {cause_id}")
        seen_ids.add(cause_id)
        if cause["claim_type"] != "CAUSAL_INFERENCE":
            raise AutopsyValidationError("causes must be marked CAUSAL_INFERENCE")
        _text(cause["statement"], f"{cause_id}.statement")
        if cause["confidence"] not in {"HIGH", "MEDIUM", "LOW"}:
            raise AutopsyValidationError(f"{cause_id}: confidence is invalid")
        _text(cause["confidence_rationale"], f"{cause_id}.confidence_rationale")
        _validate_refs(cause["evidence_refs"], allowed, f"{cause_id}.evidence_refs")
        alternatives = cause["alternatives"]
        if type(alternatives) is not list or not 1 <= len(alternatives) <= 20:
            raise AutopsyValidationError(
                f"{cause_id}: adversarial challenge requires at least one alternative"
            )
        for alternative_index, alternative in enumerate(alternatives):
            alternative = _exact_keys(
                alternative,
                {"explanation", "status", "assessment", "evidence_refs"},
                f"{cause_id}.alternatives[{alternative_index}]",
            )
            _text(
                alternative["explanation"],
                f"{cause_id}.alternatives[{alternative_index}].explanation",
            )
            if alternative["status"] not in {
                "WEAKENED_BY_EVIDENCE",
                "STILL_PLAUSIBLE",
                "NOT_TESTED",
            }:
                raise AutopsyValidationError(
                    f"{cause_id}: adversarial alternative status is invalid"
                )
            _text(
                alternative["assessment"],
                f"{cause_id}.alternatives[{alternative_index}].assessment",
            )
            _validate_refs(
                alternative["evidence_refs"],
                allowed,
                f"{cause_id}.alternatives[{alternative_index}].evidence_refs",
            )
    return value


def validate_report(
    report: dict[str, Any],
    intake: dict[str, Any],
    intake_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = intake_context or validate_intake(intake)
    _exact_keys(
        report,
        {
            "schema_version",
            "kind",
            "record_classification",
            "offer_id",
            "case_id",
            "intake_sha256",
            "failure_sentence",
            "harness_summary",
            "disposition",
            "artifact_state",
            "quality",
            "delivery",
            "timeline",
            "first_meaningful_divergence",
            "failure_chain",
            "causes",
            "fixes",
            "prevention_check",
            "clarification",
            "limitations",
            "operator_time",
            "final_review",
            "refund",
        },
        "report",
    )
    if report["schema_version"] != REPORT_VERSION:
        raise AutopsyValidationError("report schema_version is invalid")
    if report["kind"] != "AGENT_FAILURE_AUTOPSY_REPORT":
        raise AutopsyValidationError("report kind is invalid")
    if report["offer_id"] != OFFER_ID:
        raise AutopsyValidationError("report offer_id is invalid")
    if report["record_classification"] != context["classification"]:
        raise AutopsyValidationError("report classification does not match intake")
    if report["case_id"] != context["case_id"]:
        raise AutopsyValidationError("report case_id does not match intake")
    if report["failure_sentence"] != intake["failure_sentence"]:
        raise AutopsyValidationError("report must reproduce the failure sentence exactly")
    if report["intake_sha256"] != canonical_sha256(intake):
        raise AutopsyValidationError("report intake_sha256 does not bind the supplied intake")
    _text(report["harness_summary"], "report.harness_summary")

    disposition = report["disposition"]
    if disposition not in {"DIAGNOSIS_DELIVERED", "REFUND_REQUIRED"}:
        raise AutopsyValidationError("report disposition is invalid")
    artifact_state = report["artifact_state"]
    if artifact_state not in {"PEER_DRAFT", "READY_FOR_BUYER", "REFUND_REQUIRED"}:
        raise AutopsyValidationError("report artifact_state is invalid")

    quality = _exact_keys(
        report["quality"],
        {
            "bounded_unit",
            "analysis_level",
            "evidence_vs_inference_separated",
            "adversarial_challenge_completed",
            "time_measurement_truncated_analysis",
        },
        "report.quality",
    )
    expected_quality = {
        "bounded_unit": "ONE_FAILED_RUN",
        "analysis_level": "FULL_STRENGTH",
        "evidence_vs_inference_separated": True,
        "adversarial_challenge_completed": True,
        "time_measurement_truncated_analysis": False,
    }
    if quality != expected_quality:
        raise AutopsyValidationError(
            "report quality must be full-strength, adversarial, and never time-truncated"
        )

    delivery = _exact_keys(
        report["delivery"],
        {"clock_started_at", "delivery_due_at", "delivered_at", "within_one_business_day"},
        "report.delivery",
    )
    started = _nullable_time(delivery["clock_started_at"], "report.delivery.clock_started_at")
    due = _nullable_time(delivery["delivery_due_at"], "report.delivery.delivery_due_at")
    delivered = _time(delivery["delivered_at"], "report.delivery.delivered_at")
    if type(delivery["within_one_business_day"]) is not bool:
        raise AutopsyValidationError("within_one_business_day must be boolean")
    if context["state"] == "USABLE":
        if started != context["usable_at"] or due != context["due_at"]:
            raise AutopsyValidationError("report delivery clock does not match usable intake")
        derived_within = delivered <= due
        if delivery["within_one_business_day"] is not derived_within:
            raise AutopsyValidationError(
                "within_one_business_day does not match delivered_at and deadline"
            )
    else:
        if started is not None or due is not None or delivery["within_one_business_day"]:
            raise AutopsyValidationError(
                "a non-usable intake cannot claim a delivery clock"
            )

    allowed_refs: set[str] = context["anchor_refs"]
    timeline = _observed_items(report["timeline"], allowed_refs, "report.timeline")
    failure_chain = _observed_items(
        report["failure_chain"], allowed_refs, "report.failure_chain"
    )

    divergence = report["first_meaningful_divergence"]
    if divergence is not None:
        divergence = _exact_keys(
            divergence,
            {"timeline_sequence", "claim_type", "statement", "evidence_refs"},
            "report.first_meaningful_divergence",
        )
        if (
            type(divergence["timeline_sequence"]) is not int
            or divergence["timeline_sequence"] not in {item["sequence"] for item in timeline}
        ):
            raise AutopsyValidationError(
                "first meaningful divergence must point to a timeline sequence"
            )
        if divergence["claim_type"] != "OBSERVED":
            raise AutopsyValidationError(
                "first meaningful divergence must be marked OBSERVED"
            )
        _text(divergence["statement"], "report.first_meaningful_divergence.statement")
        _validate_refs(
            divergence["evidence_refs"],
            allowed_refs,
            "report.first_meaningful_divergence.evidence_refs",
        )

    causes = _exact_keys(report["causes"], {"primary", "contributing"}, "report.causes")
    cause_ids: set[str] = set()
    primary = _cause_list(causes["primary"], allowed_refs, "report.causes.primary", cause_ids)
    contributing = _cause_list(
        causes["contributing"], allowed_refs, "report.causes.contributing", cause_ids
    )

    fixes = report["fixes"]
    if type(fixes) is not list:
        raise AutopsyValidationError("report.fixes must be a list")
    fix_ids: set[str] = set()
    for index, fix in enumerate(fixes):
        fix = _exact_keys(
            fix,
            {
                "fix_id",
                "recommendation_type",
                "target",
                "addresses_cause_ids",
                "steps",
                "evidence_refs",
                "limits",
            },
            f"report.fixes[{index}]",
        )
        fix_id = _id(fix["fix_id"], f"report.fixes[{index}].fix_id")
        if fix_id in fix_ids:
            raise AutopsyValidationError(f"duplicate fix id: {fix_id}")
        fix_ids.add(fix_id)
        if fix["recommendation_type"] != "EVIDENCE_SUPPORTED_RECOMMENDATION":
            raise AutopsyValidationError(
                f"{fix_id}: fix must be marked EVIDENCE_SUPPORTED_RECOMMENDATION"
            )
        if fix["target"] not in {"PROMPT", "CONFIG", "CODE"}:
            raise AutopsyValidationError(f"{fix_id}: target is outside the offer")
        addressed = fix["addresses_cause_ids"]
        if type(addressed) is not list or not addressed or len(set(addressed)) != len(addressed):
            raise AutopsyValidationError(f"{fix_id}: addresses_cause_ids must be unique")
        unknown_causes = sorted(set(addressed) - cause_ids)
        if unknown_causes:
            raise AutopsyValidationError(
                f"{fix_id}: addresses unknown causes {unknown_causes}"
            )
        _string_list(fix["steps"], f"{fix_id}.steps", allow_empty=False, maximum_items=20)
        _validate_refs(fix["evidence_refs"], allowed_refs, f"{fix_id}.evidence_refs")
        _text(fix["limits"], f"{fix_id}.limits")

    prevention = report["prevention_check"]
    if prevention is not None:
        prevention = _exact_keys(
            prevention,
            {
                "recommendation_type",
                "setup",
                "replay_steps",
                "expected_result",
                "failure_signal",
                "evidence_refs",
                "execution_state",
            },
            "report.prevention_check",
        )
        if (
            prevention["recommendation_type"]
            != "EVIDENCE_SUPPORTED_RECOMMENDATION"
        ):
            raise AutopsyValidationError(
                "prevention check must be marked EVIDENCE_SUPPORTED_RECOMMENDATION"
            )
        _text(prevention["setup"], "report.prevention_check.setup")
        _string_list(
            prevention["replay_steps"],
            "report.prevention_check.replay_steps",
            allow_empty=False,
            maximum_items=20,
        )
        _text(prevention["expected_result"], "report.prevention_check.expected_result")
        _text(prevention["failure_signal"], "report.prevention_check.failure_signal")
        _validate_refs(
            prevention["evidence_refs"],
            allowed_refs,
            "report.prevention_check.evidence_refs",
        )
        if prevention["execution_state"] not in {
            "PROPOSED_NOT_RUN",
            "BUYER_REPORTED_PASS",
            "BUYER_REPORTED_FAIL",
        }:
            raise AutopsyValidationError("prevention check execution_state is invalid")

    clarification = _exact_keys(
        report["clarification"],
        {"rounds_used", "question", "response_evidence_refs"},
        "report.clarification",
    )
    if clarification["rounds_used"] != context["rounds"]:
        raise AutopsyValidationError("report clarification count does not match intake")
    if clarification["question"] != intake["clarification"]["question"]:
        raise AutopsyValidationError("report clarification question does not match intake")
    response_refs = clarification["response_evidence_refs"]
    if type(response_refs) is not list:
        raise AutopsyValidationError("report clarification response refs must be a list")
    for ref in response_refs:
        if ref not in allowed_refs:
            raise AutopsyValidationError(
                f"report clarification uses unknown evidence reference {ref}"
            )
        evidence_id = ref.split("#", 1)[0]
        if evidence_id not in intake["clarification"]["response_evidence_ids"]:
            raise AutopsyValidationError(
                f"report clarification reference {ref} is not from clarification evidence"
            )

    _string_list(report["limitations"], "report.limitations", allow_empty=False, maximum_items=20)

    operator = _exact_keys(
        report["operator_time"],
        {
            "measurement_status",
            "human_review_minutes",
            "automated_draft_minutes",
            "measurement_purpose",
            "time_truncated_analysis",
        },
        "report.operator_time",
    )
    if operator["measurement_purpose"] != "DESCRIPTIVE_ECONOMICS_ONLY":
        raise AutopsyValidationError(
            "operator time may be recorded only as descriptive economics"
        )
    if operator["time_truncated_analysis"] is not False:
        raise AutopsyValidationError(
            "elapsed time must never truncate Agent Failure Autopsy quality"
        )
    automated_minutes = operator["automated_draft_minutes"]
    if automated_minutes is not None:
        _number(automated_minutes, "operator_time.automated_draft_minutes")

    review = _exact_keys(
        report["final_review"],
        {"state", "reviewer_ref", "reviewed_at", "evidence_link_check"},
        "report.final_review",
    )
    if review["state"] not in {"PEER_DRAFT", "HUMAN_REVIEWED"}:
        raise AutopsyValidationError("final review state is invalid")
    reviewer_ref = review["reviewer_ref"]
    reviewed_at = _nullable_time(review["reviewed_at"], "report.final_review.reviewed_at")
    if type(review["evidence_link_check"]) is not bool:
        raise AutopsyValidationError("final review evidence_link_check must be boolean")

    refund = _exact_keys(
        report["refund"],
        {"required", "reason", "provider_state", "provider_reference_public"},
        "report.refund",
    )
    if type(refund["required"]) is not bool or refund["provider_reference_public"] is not None:
        raise AutopsyValidationError("refund truth fields are invalid")
    refund_reason = _nullable_text(refund["reason"], "report.refund.reason")
    if refund["provider_state"] not in {
        "NOT_APPLICABLE",
        "REQUIRED_PRIVATE_ACTION",
        "COMPLETED_PRIVATE",
    }:
        raise AutopsyValidationError("refund provider_state is invalid")

    classification = context["classification"]
    if classification == "SYNTHETIC_EXAMPLE":
        if (
            artifact_state != "PEER_DRAFT"
            or review["state"] != "PEER_DRAFT"
            or reviewer_ref is not None
            or reviewed_at is not None
            or review["evidence_link_check"]
        ):
            raise AutopsyValidationError(
                "synthetic example must remain an unreviewed PEER_DRAFT"
            )
        if (
            operator["measurement_status"] != "NOT_MEASURED"
            or operator["human_review_minutes"] is not None
        ):
            raise AutopsyValidationError(
                "synthetic example cannot claim measured human-review performance"
            )
    else:
        if (
            review["state"] != "HUMAN_REVIEWED"
            or type(reviewer_ref) is not str
            or not REVIEWER_RE.fullmatch(reviewer_ref)
            or reviewed_at is None
            or review["evidence_link_check"] is not True
        ):
            raise AutopsyValidationError(
                "buyer-ready or refund records require exact human evidence review"
            )
        if operator["measurement_status"] != "MEASURED":
            raise AutopsyValidationError(
                "buyer records must measure active human-review minutes"
            )
        _number(
            operator["human_review_minutes"], "operator_time.human_review_minutes"
        )
        if reviewed_at > delivered:
            raise AutopsyValidationError("report cannot be delivered before final review")

    if disposition == "DIAGNOSIS_DELIVERED":
        if context["state"] != "USABLE":
            raise AutopsyValidationError("diagnosis requires usable evidence")
        if (
            not timeline
            or divergence is None
            or not failure_chain
            or not primary
            or not fixes
            or prevention is None
        ):
            raise AutopsyValidationError(
                "diagnosis requires sequence, first divergence, failure chain, "
                "primary cause, supported fix, and replay check"
            )
        if delivery["within_one_business_day"] is not True:
            raise AutopsyValidationError(
                "diagnosis delivery missed the one-business-day contract"
            )
        if refund["required"] or refund_reason is not None or refund["provider_state"] != "NOT_APPLICABLE":
            raise AutopsyValidationError("delivered diagnosis cannot claim a refund")
        expected_artifact = (
            "PEER_DRAFT" if classification == "SYNTHETIC_EXAMPLE" else "READY_FOR_BUYER"
        )
        if artifact_state != expected_artifact:
            raise AutopsyValidationError("diagnosis artifact state is inconsistent")
    else:
        if context["state"] != "INSUFFICIENT_AFTER_CLARIFICATION":
            raise AutopsyValidationError(
                "refund is available only after evidence remains insufficient after clarification"
            )
        if timeline or divergence is not None or failure_chain or primary or contributing or fixes or prevention is not None:
            raise AutopsyValidationError(
                "refund report must not invent timeline, causes, fixes, or replay claims"
            )
        if (
            artifact_state != "REFUND_REQUIRED"
            or refund["required"] is not True
            or refund_reason is None
            or refund["provider_state"] not in {"REQUIRED_PRIVATE_ACTION", "COMPLETED_PRIVATE"}
        ):
            raise AutopsyValidationError("refund disposition is incomplete")

    warnings: list[str] = []
    if classification == "SYNTHETIC_EXAMPLE":
        warnings.append(
            "synthetic peer draft: no buyer delivery, human-review time, sale, or revenue is established"
        )
    return {
        "ok": True,
        "case_id": context["case_id"],
        "disposition": disposition,
        "artifact_state": artifact_state,
        "intake_sha256": canonical_sha256(intake),
        "clock_started_at": delivery["clock_started_at"],
        "delivery_due_at": delivery["delivery_due_at"],
        "human_review_minutes": operator["human_review_minutes"],
        "automated_draft_minutes": operator["automated_draft_minutes"],
        "time_measurement_purpose": operator["measurement_purpose"],
        "warnings": warnings,
    }


def verify_example_evidence(
    context: dict[str, Any], evidence_root: str | Path | None
) -> None:
    if context["classification"] != "SYNTHETIC_EXAMPLE":
        return
    if evidence_root is None:
        raise AutopsyValidationError(
            "synthetic example validation requires --evidence-root"
        )
    root = Path(evidence_root).resolve(strict=True)
    if not root.is_dir():
        raise AutopsyValidationError("evidence root must be a directory")
    for evidence_id, location in context["locations_by_id"].items():
        relative = location.split(":", 1)[1]
        target = (root / relative).resolve(strict=True)
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise AutopsyValidationError(
                f"{evidence_id}: evidence escapes the example root"
            ) from exc
        if not target.is_file() or target.is_symlink():
            raise AutopsyValidationError(
                f"{evidence_id}: example evidence is not a regular file"
            )
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != context["hashes_by_id"][evidence_id]:
            raise AutopsyValidationError(
                f"{evidence_id}: example evidence SHA-256 does not match"
            )


def validate_bundle(
    intake: dict[str, Any],
    report: dict[str, Any],
    evidence_root: str | Path | None = None,
) -> dict[str, Any]:
    context = validate_intake(intake)
    verify_example_evidence(context, evidence_root)
    return validate_report(report, intake, context)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--intake", required=True)
    validate.add_argument("--report", required=True)
    validate.add_argument("--evidence-root")
    deadline = subparsers.add_parser("deadline")
    deadline.add_argument("--usable-evidence-at", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "deadline":
            result = {
                "usable_evidence_at": args.usable_evidence_at,
                "delivery_due_at": next_business_day(args.usable_evidence_at),
            }
        else:
            intake = load_json(args.intake)
            report = load_json(args.report)
            result = validate_bundle(intake, report, args.evidence_root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (AutopsyValidationError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
