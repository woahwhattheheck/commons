from __future__ import annotations

from typing import Any

from .common import (
    COMMITMENT_KINDS, GATE_STATES, INPUT_SCHEMA, INTERPRETATIONS, MAX_SAFE_SNIPPETS_PER_ASSET,
    MAX_SECONDS, MAX_SNIPPET, POLICY_SCHEMA, PREP_STATES, RELEASE_CLASSES, SENDER_ROLES, SOURCE_CLASSES,
    ControlError, _optional_text, _parse_ref_list, _parse_time, _reject_unknown, _require_bool,
    _require_dict, _require_enum, _require_int, _require_list, _require_ref, _require_sha256, _require_text,
)

def _parse_policy(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "schema_version",
        "max_reply_age_seconds",
        "max_source_age_seconds",
        "max_future_skew_seconds",
        "required_asset_ids",
        "required_clear_gate_ids",
    }
    _reject_unknown(raw, allowed, "policy")
    if raw.get("schema_version") != POLICY_SCHEMA:
        raise ControlError(f"policy.schema_version must equal {POLICY_SCHEMA!r}")
    return {
        "schema_version": POLICY_SCHEMA,
        "max_reply_age_seconds": _require_int(
            raw.get("max_reply_age_seconds"),
            "policy.max_reply_age_seconds",
            minimum=0,
            maximum=MAX_SECONDS,
        ),
        "max_source_age_seconds": _require_int(
            raw.get("max_source_age_seconds"),
            "policy.max_source_age_seconds",
            minimum=0,
            maximum=MAX_SECONDS,
        ),
        "max_future_skew_seconds": _require_int(
            raw.get("max_future_skew_seconds"),
            "policy.max_future_skew_seconds",
            minimum=0,
            maximum=86_400,
        ),
        "required_asset_ids": _parse_ref_list(raw.get("required_asset_ids", []), "policy.required_asset_ids"),
        "required_clear_gate_ids": _parse_ref_list(
            raw.get("required_clear_gate_ids", []), "policy.required_clear_gate_ids"
        ),
    }


def _parse_opportunity(raw: Any) -> dict[str, Any]:
    obj = _require_dict(raw, "input.opportunity")
    allowed = {
        "opportunity_id",
        "counterparty_ref",
        "thread_id",
        "source_digest",
        "source_checked_at",
    }
    _reject_unknown(obj, allowed, "input.opportunity")
    return {
        "opportunity_id": _require_ref(obj.get("opportunity_id"), "input.opportunity.opportunity_id"),
        "counterparty_ref": _require_ref(obj.get("counterparty_ref"), "input.opportunity.counterparty_ref"),
        "thread_id": _require_ref(obj.get("thread_id"), "input.opportunity.thread_id"),
        "source_digest": _require_sha256(obj.get("source_digest"), "input.opportunity.source_digest"),
        "source_checked_at": _parse_time(obj.get("source_checked_at"), "input.opportunity.source_checked_at"),
    }


def _parse_observation(raw: Any, index: int) -> dict[str, Any]:
    label = f"input.observations[{index}]"
    obj = _require_dict(raw, label)
    allowed = {
        "observation_id",
        "thread_id",
        "message_id",
        "sender_ref",
        "sender_role",
        "received_at",
        "content_sha256",
        "source_class",
        "interpretation",
        "supersedes_observation_id",
        "clarification_codes",
    }
    _reject_unknown(obj, allowed, label)
    supersedes = obj.get("supersedes_observation_id")
    if supersedes is not None:
        supersedes = _require_ref(supersedes, f"{label}.supersedes_observation_id")
    return {
        "observation_id": _require_ref(obj.get("observation_id"), f"{label}.observation_id"),
        "thread_id": _require_ref(obj.get("thread_id"), f"{label}.thread_id"),
        "message_id": _require_ref(obj.get("message_id"), f"{label}.message_id"),
        "sender_ref": _require_ref(obj.get("sender_ref"), f"{label}.sender_ref"),
        "sender_role": _require_enum(obj.get("sender_role"), f"{label}.sender_role", SENDER_ROLES),
        "received_at": _parse_time(obj.get("received_at"), f"{label}.received_at"),
        "content_sha256": _require_sha256(obj.get("content_sha256"), f"{label}.content_sha256"),
        "source_class": _require_enum(obj.get("source_class"), f"{label}.source_class", SOURCE_CLASSES),
        "interpretation": _require_enum(obj.get("interpretation"), f"{label}.interpretation", INTERPRETATIONS),
        "supersedes_observation_id": supersedes,
        "clarification_codes": _parse_ref_list(obj.get("clarification_codes", []), f"{label}.clarification_codes"),
    }


def _parse_asset(raw: Any, index: int) -> dict[str, Any]:
    label = f"input.assets[{index}]"
    obj = _require_dict(raw, label)
    allowed = {
        "asset_id",
        "title",
        "version",
        "sha256",
        "prep_state",
        "release_class",
        "required_for_followup",
        "safe_snippets",
    }
    _reject_unknown(obj, allowed, label)
    snippets_raw = _require_list(
        obj.get("safe_snippets", []), f"{label}.safe_snippets", maximum=MAX_SAFE_SNIPPETS_PER_ASSET
    )
    snippets = [
        _require_text(v, f"{label}.safe_snippets[{i}]", max_len=MAX_SNIPPET)
        for i, v in enumerate(snippets_raw)
    ]
    return {
        "asset_id": _require_ref(obj.get("asset_id"), f"{label}.asset_id"),
        "title": _require_text(obj.get("title"), f"{label}.title", max_len=160),
        "version": _require_ref(obj.get("version"), f"{label}.version"),
        "sha256": _require_sha256(obj.get("sha256"), f"{label}.sha256"),
        "prep_state": _require_enum(obj.get("prep_state"), f"{label}.prep_state", PREP_STATES),
        "release_class": _require_enum(obj.get("release_class"), f"{label}.release_class", RELEASE_CLASSES),
        "required_for_followup": _require_bool(
            obj.get("required_for_followup"), f"{label}.required_for_followup"
        ),
        "safe_snippets": snippets,
    }


def _parse_release(raw: Any, index: int) -> dict[str, Any]:
    label = f"input.release_records[{index}]"
    obj = _require_dict(raw, label)
    allowed = {
        "release_id",
        "asset_id",
        "asset_version",
        "asset_sha256",
        "approved_at",
        "approved_by_ref",
    }
    _reject_unknown(obj, allowed, label)
    return {
        "release_id": _require_ref(obj.get("release_id"), f"{label}.release_id"),
        "asset_id": _require_ref(obj.get("asset_id"), f"{label}.asset_id"),
        "asset_version": _require_ref(obj.get("asset_version"), f"{label}.asset_version"),
        "asset_sha256": _require_sha256(obj.get("asset_sha256"), f"{label}.asset_sha256"),
        "approved_at": _parse_time(obj.get("approved_at"), f"{label}.approved_at"),
        "approved_by_ref": _require_ref(obj.get("approved_by_ref"), f"{label}.approved_by_ref"),
    }


def _parse_gate(raw: Any, index: int) -> dict[str, Any]:
    label = f"input.qualification_gates[{index}]"
    obj = _require_dict(raw, label)
    allowed = {"gate_id", "mandatory", "state", "owner_action"}
    _reject_unknown(obj, allowed, label)
    owner_action = _optional_text(obj.get("owner_action"), f"{label}.owner_action", max_len=500)
    return {
        "gate_id": _require_ref(obj.get("gate_id"), f"{label}.gate_id"),
        "mandatory": _require_bool(obj.get("mandatory"), f"{label}.mandatory"),
        "state": _require_enum(obj.get("state"), f"{label}.state", GATE_STATES),
        "owner_action": owner_action,
    }


def _parse_commitment(raw: Any, index: int) -> dict[str, Any]:
    label = f"input.commitments[{index}]"
    obj = _require_dict(raw, label)
    allowed = {
        "commitment_id",
        "kind",
        "required_for_followup",
        "approved",
        "safe_fact",
        "approval_ref",
    }
    _reject_unknown(obj, allowed, label)
    approved = _require_bool(obj.get("approved"), f"{label}.approved")
    safe_fact = _optional_text(obj.get("safe_fact"), f"{label}.safe_fact", max_len=MAX_SNIPPET)
    approval_ref = obj.get("approval_ref")
    if approval_ref is not None:
        approval_ref = _require_ref(approval_ref, f"{label}.approval_ref")
    if approved and (safe_fact is None or approval_ref is None):
        raise ControlError(f"{label} approved commitment requires safe_fact and approval_ref")
    if not approved and (safe_fact is not None or approval_ref is not None):
        raise ControlError(f"{label} unapproved commitment cannot carry safe_fact or approval_ref")
    return {
        "commitment_id": _require_ref(obj.get("commitment_id"), f"{label}.commitment_id"),
        "kind": _require_enum(obj.get("kind"), f"{label}.kind", COMMITMENT_KINDS),
        "required_for_followup": _require_bool(
            obj.get("required_for_followup"), f"{label}.required_for_followup"
        ),
        "approved": approved,
        "safe_fact": safe_fact,
        "approval_ref": approval_ref,
    }


def _parse_input(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "schema_version",
        "opportunity",
        "observations",
        "assets",
        "release_records",
        "qualification_gates",
        "commitments",
        "requested_asset_ids",
    }
    _reject_unknown(raw, allowed, "input")
    if raw.get("schema_version") != INPUT_SCHEMA:
        raise ControlError(f"input.schema_version must equal {INPUT_SCHEMA!r}")
    observations = [
        _parse_observation(v, i)
        for i, v in enumerate(_require_list(raw.get("observations"), "input.observations"))
    ]
    if not observations:
        raise ControlError("input.observations must not be empty")
    assets = [
        _parse_asset(v, i)
        for i, v in enumerate(_require_list(raw.get("assets", []), "input.assets"))
    ]
    releases = [
        _parse_release(v, i)
        for i, v in enumerate(_require_list(raw.get("release_records", []), "input.release_records"))
    ]
    gates = [
        _parse_gate(v, i)
        for i, v in enumerate(_require_list(raw.get("qualification_gates", []), "input.qualification_gates"))
    ]
    commitments = [
        _parse_commitment(v, i)
        for i, v in enumerate(_require_list(raw.get("commitments", []), "input.commitments"))
    ]
    return {
        "schema_version": INPUT_SCHEMA,
        "opportunity": _parse_opportunity(raw.get("opportunity")),
        "observations": observations,
        "assets": assets,
        "release_records": releases,
        "qualification_gates": gates,
        "commitments": commitments,
        "requested_asset_ids": _parse_ref_list(
            raw.get("requested_asset_ids", []), "input.requested_asset_ids"
        ),
    }


