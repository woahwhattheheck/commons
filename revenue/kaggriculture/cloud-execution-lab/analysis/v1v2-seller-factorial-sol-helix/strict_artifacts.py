# SPDX-License-Identifier: Apache-2.0
"""Retained arm-bundle, game, and entrypoint admission."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from strict_types import (
    EXPECTED_ACTION_COUNT, EXPECTED_EPISODE_STEPS, EXPECTED_INTERVENTIONS,
    EXPECTED_OPPONENTS, EXPECTED_SEEDS, EXPECTED_STEPS, HEX64, OPERATION,
    AdmissionError, _is_int, _is_number, _require_hex, load_json, sha256_file,
    tree_receipt,
)
from strict_entry import verify_entry_runtime


def _game_key(raw: Mapping[str, Any], arm: str) -> tuple[str, int, int]:
    opponent = raw.get("opponent")
    seed = raw.get("seed")
    seat = raw.get("candidate_seat")
    if not isinstance(opponent, str) or opponent not in EXPECTED_OPPONENTS:
        raise AdmissionError(f"{arm}: invalid opponent {opponent!r}")
    if not _is_int(seed) or seed not in EXPECTED_SEEDS:
        raise AdmissionError(f"{arm}: seed must be a literal expected integer: {seed!r}")
    if not _is_int(seat) or seat not in (0, 1):
        raise AdmissionError(f"{arm}: seat must be literal integer 0/1: {seat!r}")
    return opponent, seed, seat


def _validate_game(raw: Mapping[str, Any], arm: str) -> tuple[str, int, int]:
    key = _game_key(raw, arm)
    if raw.get("status") != "complete" or raw.get("failure") is not None:
        raise AdmissionError(f"{arm}: incomplete game {key}")
    scores = raw.get("scores")
    if not isinstance(scores, list) or len(scores) != 2 or not all(_is_number(x) for x in scores):
        raise AdmissionError(f"{arm}: invalid scores {key}")
    _require_hex(raw.get("trace_sha256"), HEX64, f"{arm} {key} whole trace")
    _require_hex(raw.get("candidate_action_sha256"), HEX64, f"{arm} {key} candidate action")
    for field, expected in (
        ("candidate_action_count", EXPECTED_ACTION_COUNT),
        ("steps", EXPECTED_STEPS),
        ("episode_steps", EXPECTED_EPISODE_STEPS),
    ):
        value = raw.get(field)
        if not _is_int(value) or value != expected:
            raise AdmissionError(f"{arm}: {field} mismatch at {key}: {value!r}")
    actors = raw.get("actors")
    if not isinstance(actors, list) or len(actors) != 2:
        raise AdmissionError(f"{arm}: missing two actor receipts at {key}")
    for index, actor in enumerate(actors):
        if not isinstance(actor, Mapping) or not _is_int(actor.get("calls")) or actor.get("calls") != EXPECTED_ACTION_COUNT:
            raise AdmissionError(f"{arm}: actor {index} call count mismatch at {key}")
    return key


def _artifact_paths(report_path: Path, arm: str) -> dict[str, Path]:
    report_path = Path(report_path).resolve(strict=True)
    evidence_arm = report_path.parent
    if evidence_arm.name != arm or evidence_arm.parent.name != "evidence":
        raise AdmissionError(f"{arm}: report is not under evidence/{arm}/ARM.json")
    artifact_root = evidence_arm.parents[1]
    return {
        "report": report_path,
        "evidence_arm": evidence_arm,
        "artifact_root": artifact_root,
        "bundle": artifact_root / "arms" / arm,
        "entry": artifact_root / "arms" / arm / "bound_entry.py",
        "receipt": evidence_arm / "MATERIALIZATION.json",
        "shards": evidence_arm / f"{arm}-shards",
    }


def _same_receipt(actual: Mapping[str, Any], expected: Mapping[str, Any], label: str) -> None:
    for field in ("schema_version", "files", "bytes", "sha256", "entries"):
        if actual.get(field) != expected.get(field):
            raise AdmissionError(f"{label} mismatch in {field}")


def _validate_materialization(paths: Mapping[str, Path], arm: str, identity: Mapping[str, Any]) -> dict[str, Any]:
    bundle = paths["bundle"].resolve(strict=True)
    entry = paths["entry"].resolve(strict=True)
    receipt_path = paths["receipt"].resolve(strict=True)
    receipt = load_json(receipt_path)
    if not isinstance(receipt, Mapping):
        raise AdmissionError(f"{arm}: materialization receipt must be an object")
    if receipt.get("schema_version") != 1 or receipt.get("operation") != OPERATION or receipt.get("arm") != arm:
        raise AdmissionError(f"{arm}: materialization receipt identity mismatch")
    source = receipt.get("source") or {}
    if (source.get("scheduler_git_blob") != "7c068b7078c3d7c09bb3836590ad42b0af934cdf"
            or source.get("scheduler_sha256") != "72865b83e66d0c1ed27ddc35e5ab428f8212872e8e8e918f2826eb7665fbe7f8"):
        raise AdmissionError(f"{arm}: frozen V2 scheduler identity mismatch")
    patch = receipt.get("patch") or {}
    carry, force_end = EXPECTED_INTERVENTIONS[arm]
    if (patch.get("arm") != arm or patch.get("carry_discount") != carry
            or patch.get("force_residual_reference_at_horizon") is not force_end):
        raise AdmissionError(f"{arm}: intervention receipt mismatch")
    entry_record = receipt.get("entrypoint") or {}
    if entry_record.get("import_ownership") != "candidate+scheduler-under-bound-root-v1":
        raise AdmissionError(f"{arm}: entry receipt lacks import-root ownership")
    entry_sha = sha256_file(entry)
    _require_hex(entry_sha, HEX64, f"{arm} entry sha")
    if entry_record.get("sha256") != entry_sha or identity.get("entry_sha256") != entry_sha:
        raise AdmissionError(f"{arm}: entry digest is not bound to retained bytes")
    receipt_sha = sha256_file(receipt_path)
    if identity.get("materialization_receipt_sha256") != receipt_sha:
        raise AdmissionError(f"{arm}: materialization receipt digest mismatch")
    closure = tree_receipt(bundle, exclude=frozenset({"bound_entry.py"}))
    final_bundle = tree_receipt(bundle)
    _same_receipt(closure, receipt.get("closure_bound_at_entry") or {}, f"{arm} entry closure")
    _same_receipt(final_bundle, receipt.get("materialized_bundle") or {}, f"{arm} final bundle")
    identity_closure = identity.get("closure") or {}
    if identity_closure != receipt.get("closure_bound_at_entry"):
        raise AdmissionError(f"{arm}: report closure differs from materialization receipt")
    arm_record = load_json(bundle / "ARM.json")
    if (not isinstance(arm_record, Mapping) or arm_record.get("operation") != OPERATION
            or arm_record.get("arm") != arm):
        raise AdmissionError(f"{arm}: retained ARM.json identity mismatch")
    interventions = arm_record.get("interventions") or {}
    if (interventions.get("carry_discount") != carry
            or interventions.get("force_residual_reference_at_horizon") is not force_end):
        raise AdmissionError(f"{arm}: retained ARM.json intervention mismatch")
    origins = verify_entry_runtime(entry)
    return {
        "entry_sha256": entry_sha,
        "receipt_sha256": receipt_sha,
        "closure_sha256": closure["sha256"],
        "bundle_sha256": final_bundle["sha256"],
        "module_origins": origins,
    }

