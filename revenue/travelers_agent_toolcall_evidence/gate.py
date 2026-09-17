from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from revenue.travelers_agent_toolcall_evidence import gate_core as _core


# Preserve the reviewed v1 decision engine byte-for-byte in gate_core.py and
# make this module the canonical v2 evidence surface.  The facade deliberately
# changes only detached-receipt scope/currentness binding and root trust; all
# ingress, policy, lifecycle, approval, effect, budget and idempotency semantics
# continue to execute in the frozen core generation.
GateError = _core.GateError
ROOT = _core.ROOT
EXPECTED_AUTHORITY = deepcopy(_core.EXPECTED_AUTHORITY)
DECISION_SCOPE = "SYNTHETIC_POLICY_EVALUATION_ONLY_NOT_PRODUCTION_EXECUTION"
EVALUATION_TIME_AUTHORITY = "CALLER_SUPPLIED_REPLAY_ONLY_NOT_CURRENT"

loads_strict = _core.loads_strict
canonical_bytes = _core.canonical_bytes
sha256_json = _core.sha256_json
load_policy = _core.load_policy


def _upgrade_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(receipt))
    value.pop("receipt_sha256", None)
    value["schema"] = "agent-toolcall-gate-receipt/v2"
    value["decision_scope"] = DECISION_SCOPE
    value["evaluation_time_authority"] = EVALUATION_TIME_AUTHORITY
    value["current_execution_authority_claimed"] = False
    value["authority"] = deepcopy(EXPECTED_AUTHORITY)
    value["receipt_sha256"] = sha256_json(value)
    return value


def compile_batch(
    envelopes: Iterable[Mapping[str, Any]], policy: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [_upgrade_receipt(item) for item in _core.compile_batch(envelopes, policy)]


def compile_one(
    envelope: Mapping[str, Any], policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return compile_batch([envelope], policy)[0]


def verify_batch(
    envelopes: Iterable[Mapping[str, Any]], receipts: Iterable[Mapping[str, Any]],
    policy: Mapping[str, Any] | None = None,
) -> bool:
    try:
        supplied = [dict(item) for item in receipts]
        expected = compile_batch(envelopes, policy)
    except (GateError, TypeError, ValueError):
        return False
    return canonical_bytes(expected) == canonical_bytes(supplied)


def receipt_markdown(receipt: Mapping[str, Any]) -> str:
    value = dict(receipt)
    rendered = _core.receipt_markdown(value)
    return (
        rendered
        + f"Decision scope: `{value.get('decision_scope')}`\n"
        + f"Evaluation-time authority: `{value.get('evaluation_time_authority')}`\n"
        + "Current execution authority claimed: "
        + f"`{value.get('current_execution_authority_claimed')}`\n"
    )


def build_ledger(receipts: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return _core.build_ledger(receipts)


def verify_ledger(entries: Iterable[Mapping[str, Any]]) -> bool:
    return _core.verify_ledger(entries)


def daily_root_manifest(entries: Iterable[Mapping[str, Any]], day: str) -> dict[str, Any]:
    materialized = [deepcopy(dict(item)) for item in entries]
    if not verify_ledger(materialized):
        raise GateError("ledger must verify before daily root construction")

    manifest = _core.daily_root_manifest(materialized, day)
    manifest.pop("manifest_sha256", None)
    manifest["schema"] = "agent-toolcall-daily-root/v2"
    manifest["ledger_verified_before_root"] = True
    manifest["decision_scope"] = DECISION_SCOPE
    manifest["evaluation_time_authority"] = EVALUATION_TIME_AUTHORITY
    manifest["current_execution_authority_claimed"] = False
    manifest["authority"] = deepcopy(EXPECTED_AUTHORITY)
    manifest["manifest_sha256"] = sha256_json(manifest)
    return manifest


def verify_root(
    manifest: Mapping[str, Any], entries: Iterable[Mapping[str, Any]],
) -> bool:
    try:
        supplied = deepcopy(dict(manifest))
        materialized = [deepcopy(dict(item)) for item in entries]
    except (TypeError, ValueError):
        return False
    if not verify_ledger(materialized):
        return False
    day = supplied.get("day")
    if type(day) is not str:
        return False
    try:
        expected = daily_root_manifest(materialized, day)
    except (GateError, KeyError, TypeError, ValueError):
        return False
    return canonical_bytes(expected) == canonical_bytes(supplied)
