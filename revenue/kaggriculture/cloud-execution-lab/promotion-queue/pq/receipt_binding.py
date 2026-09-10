# SPDX-License-Identifier: Apache-2.0
"""Fail-closed binding from an Attempt outcome back to its queue pin."""
from __future__ import annotations

from collections.abc import Mapping

from .executable_pins import ExecutablePinError, slot_input_name


def _mapping(value, label: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise ExecutablePinError(f"{label}: expected object")
    return value


def _digest(inputs: Mapping, name: str) -> str:
    record = _mapping(inputs.get(name), f"submission input {name}")
    digest = record.get("sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ExecutablePinError(
            f"submission input {name}: expected 64-character sha256"
        )
    try:
        int(digest, 16)
    except ValueError as exc:
        raise ExecutablePinError(
            f"submission input {name}: sha256 is not hexadecimal"
        ) from exc
    return digest


def _comparison_index(value) -> dict[str, Mapping]:
    if not isinstance(value, list):
        raise ExecutablePinError("attempt comparisons: expected list")
    indexed: dict[str, Mapping] = {}
    for position, item in enumerate(value):
        comparison = _mapping(item, f"attempt comparison {position}")
        slot = comparison.get("slot")
        if not isinstance(slot, str) or not slot:
            raise ExecutablePinError(
                f"attempt comparison {position}: slot must be a nonempty string"
            )
        if slot in indexed:
            raise ExecutablePinError(f"attempt comparisons duplicate slot: {slot}")
        indexed[slot] = comparison
    return indexed


def require_outcome_input_binding(
    *,
    pin_manifest: Mapping,
    config: Mapping,
    outcome: Mapping,
) -> None:
    """Require every sealable predecessor digest to equal submitted bytes.

    This is deliberately checked after the inherited ``Attempt.execute`` and
    before receipt construction. It protects the receipt boundary from a
    future parent-runner regression that reads the right blobs but reports the
    wrong slot identity.
    """
    pin_manifest = _mapping(pin_manifest, "pin manifest")
    inputs = _mapping(pin_manifest.get("inputs"), "pin manifest inputs")
    config = _mapping(config, "predecessor config")
    slots = _mapping(config.get("slots"), "predecessor config slots")
    outcome = _mapping(outcome, "attempt outcome")
    predecessors = _mapping(
        outcome.get("predecessor_identity"),
        "attempt predecessor_identity",
    )
    comparisons = _comparison_index(outcome.get("comparisons"))

    expected_slots = set(slots)
    predecessor_slots = set(predecessors)
    comparison_slots = set(comparisons)
    if predecessor_slots != expected_slots:
        raise ExecutablePinError(
            "attempt predecessor slot set differs from submitted config: "
            f"expected={sorted(expected_slots)!r} "
            f"observed={sorted(predecessor_slots)!r}"
        )
    if comparison_slots != expected_slots:
        raise ExecutablePinError(
            "attempt comparison slot set differs from submitted config: "
            f"expected={sorted(expected_slots)!r} "
            f"observed={sorted(comparison_slots)!r}"
        )

    candidate_games = _digest(inputs, "candidate_games")
    for slot_key in sorted(expected_slots):
        slot_config = _mapping(slots[slot_key], f"predecessor config slot {slot_key!r}")
        predecessor = _mapping(
            predecessors[slot_key],
            f"attempt predecessor_identity {slot_key!r}",
        )
        comparison = comparisons[slot_key]

        expected_name = slot_config.get("name")
        if predecessor.get("name") != expected_name:
            raise ExecutablePinError(
                f"predecessor slot {slot_key!r} name differs from submitted config"
            )

        expected_games = _digest(inputs, slot_input_name(slot_key, "games"))
        expected_artifact = _digest(
            inputs,
            slot_input_name(slot_key, "artifact_file"),
        )
        observed_games = predecessor.get("games_sha256")
        observed_artifact = predecessor.get("artifact_sha256")
        if observed_games != expected_games:
            raise ExecutablePinError(
                f"predecessor slot {slot_key!r} receipt games digest differs "
                f"from submission: expected={expected_games} observed={observed_games}"
            )
        if observed_artifact != expected_artifact:
            raise ExecutablePinError(
                f"predecessor slot {slot_key!r} receipt artifact digest differs "
                f"from submission: expected={expected_artifact} "
                f"observed={observed_artifact}"
            )
        if comparison.get("panel_id") not in (None, predecessor.get("panel_id")):
            raise ExecutablePinError(
                f"predecessor slot {slot_key!r} comparison panel differs from receipt"
            )

        # Paired comparisons expose their direct input hashes. The dual gate
        # binds these values in its custody receipts but does not copy the map
        # into the parent summary, so absence is accepted only for that shape.
        comparison_inputs = comparison.get("input_sha256")
        if comparison_inputs is not None:
            comparison_inputs = _mapping(
                comparison_inputs,
                f"attempt comparison {slot_key!r} input_sha256",
            )
            if comparison_inputs.get("baseline_games") != expected_games:
                raise ExecutablePinError(
                    f"predecessor slot {slot_key!r} comparison games digest "
                    "differs from submission"
                )
            if comparison_inputs.get("candidate_games") != candidate_games:
                raise ExecutablePinError(
                    f"predecessor slot {slot_key!r} comparison candidate digest "
                    "differs from submission"
                )
            if comparison_inputs.get("contract") != predecessor.get("contract_sha256"):
                raise ExecutablePinError(
                    f"predecessor slot {slot_key!r} comparison contract digest "
                    "differs from receipt"
                )
            if comparison_inputs.get("evidence") != predecessor.get("evidence_sha256"):
                raise ExecutablePinError(
                    f"predecessor slot {slot_key!r} comparison evidence digest "
                    "differs from receipt"
                )
