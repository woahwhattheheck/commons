"""Sealed receipt and atomic-output layer for the Titan cardinality gate."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from gate_common import (
    CANONICAL_MARKET_NO_ORDER,
    GATE_ID,
    SCHEMA_VERSION,
    GateInputError,
    _exact_int,
    _exact_string,
    _load_replay,
    _opcode,
    _read_replay_bytes,
    _tool_sha256,
    canonical_json_bytes,
    sha256_bytes,
)
from gate_core import analyze_replay


def seal_receipt(body: Mapping[str, Any]) -> dict[str, Any]:
    sealed = dict(body)
    sealed.pop("receipt_sha256", None)
    sealed["receipt_sha256"] = sha256_bytes(canonical_json_bytes(sealed))
    return sealed


def verify_receipt(receipt: Any) -> tuple[bool, str]:
    if not isinstance(receipt, dict):
        return False, "receipt must be an object"
    observed = receipt.get("receipt_sha256")
    if (
        not isinstance(observed, str)
        or len(observed) != 64
        or any(char not in "0123456789abcdef" for char in observed)
    ):
        return False, "receipt_sha256 must be lowercase hexadecimal SHA-256"
    body = dict(receipt)
    body.pop("receipt_sha256", None)
    expected = sha256_bytes(canonical_json_bytes(body))
    if observed != expected:
        return False, f"receipt hash mismatch: observed {observed}, expected {expected}"
    return True, "receipt hash verified"


def _invalid_receipt(
    *,
    replay_path: Path,
    error: str,
    expected_sha256: str | None,
    expected_episode_id: int | None,
    expected_agent_name: str | None,
    seat: int,
    raw_sha256: str | None = None,
    raw_bytes: int | None = None,
    encoding: str | None = None,
    decoded_sha256: str | None = None,
    decoded_bytes: int | None = None,
) -> dict[str, Any]:
    return seal_receipt(
        {
            "schema_version": SCHEMA_VERSION,
            "gate_id": GATE_ID,
            "verdict": "INVALID",
            "reason": error,
            "tool_sha256": _tool_sha256(),
            "policy": {
                "rule": "submitted_hand_rows <= observable_hands",
                "alignment": "action[k] uses observation[k-1]; k=0 uses observation[0]",
                "missing_or_ambiguous_evidence": "INVALID",
                "canonical_market_no_order": CANONICAL_MARKET_NO_ORDER,
            },
            "input": {
                "basename": replay_path.name,
                "seat": seat,
                "expected_sha256": expected_sha256,
                "expected_episode_id": expected_episode_id,
                "expected_agent_name": expected_agent_name,
                "raw_sha256": raw_sha256,
                "raw_bytes": raw_bytes,
                "encoding": encoding,
                "decoded_sha256": decoded_sha256,
                "decoded_bytes": decoded_bytes,
            },
        }
    )


def _compact_analysis_for_receipt(analysis: Mapping[str, Any]) -> dict[str, Any]:
    """Keep every violation witness while avoiding repetitive receipt bloat."""
    compact = dict(analysis)
    violations = compact.pop("violations")
    compact["full_violation_ledger_sha256"] = sha256_bytes(
        canonical_json_bytes(violations)
    )
    compact["violation_witness_columns"] = [
        "step",
        "pre_observation_step",
        "alignment",
        "day",
        "hour",
        "observable_hands",
        "submitted_hand_rows",
        "trailing_opcodes",
        "trailing_rows_sha256",
    ]
    compact["violation_witnesses"] = [
        [
            violation["step"],
            violation["pre_observation_step"],
            violation["alignment"],
            violation["day"],
            violation["hour"],
            violation["observable_hands"],
            violation["submitted_hand_rows"],
            [_opcode(row) for row in violation["trailing_rows"]],
            violation["trailing_rows_sha256"],
        ]
        for violation in violations
    ]
    return compact


def run_gate(
    replay_path: str | os.PathLike[str],
    *,
    seat: int,
    expected_sha256: str | None = None,
    expected_episode_id: int | None = None,
    expected_agent_name: str | None = None,
) -> dict[str, Any]:
    """Run the gate and always return a sealed PASS/REJECT/INVALID receipt."""

    path = Path(replay_path)
    raw: bytes | None = None
    decoded: bytes | None = None
    encoding: str | None = None
    raw_sha256: str | None = None
    try:
        seat = _exact_int(seat, "seat", minimum=0)
        if expected_sha256 is not None:
            expected_sha256 = _exact_string(expected_sha256, "expected_sha256")
            if len(expected_sha256) != 64 or any(
                char not in "0123456789abcdef" for char in expected_sha256
            ):
                raise GateInputError("expected_sha256 must be lowercase hexadecimal SHA-256")
        raw, decoded, encoding = _read_replay_bytes(path)
        raw_sha256 = sha256_bytes(raw)
        if expected_sha256 is not None and raw_sha256 != expected_sha256:
            raise GateInputError(
                f"input SHA-256 mismatch: observed {raw_sha256}, expected {expected_sha256}"
            )
        replay = _load_replay(decoded)
        analysis = analyze_replay(
            replay,
            seat=seat,
            expected_episode_id=expected_episode_id,
            expected_agent_name=expected_agent_name,
        )
        verdict = (
            "REJECT"
            if analysis["over_cardinality_transition_count"] > 0
            else "PASS"
        )
        reason = (
            "submitted hand-action rows exceeded the exact observable hand count"
            if verdict == "REJECT"
            else "every submitted hand-action list fit the exact observable hand count"
        )
        return seal_receipt(
            {
                "schema_version": SCHEMA_VERSION,
                "gate_id": GATE_ID,
                "verdict": verdict,
                "reason": reason,
                "tool_sha256": _tool_sha256(),
                "policy": {
                    "rule": "submitted_hand_rows <= observable_hands",
                    "alignment": "action[k] uses observation[k-1]; k=0 uses observation[0]",
                    "missing_or_ambiguous_evidence": "INVALID",
                    "canonical_market_no_order": CANONICAL_MARKET_NO_ORDER,
                    "empty_market_row": "present-but-not-canonical; counted only",
                },
                "input": {
                    "basename": path.name,
                    "raw_sha256": raw_sha256,
                    "raw_bytes": len(raw),
                    "encoding": encoding,
                    "decoded_sha256": sha256_bytes(decoded),
                    "decoded_bytes": len(decoded),
                    "expected_sha256": expected_sha256,
                    "expected_episode_id": expected_episode_id,
                    "expected_agent_name": expected_agent_name,
                },
                "analysis": _compact_analysis_for_receipt(analysis),
            }
        )
    except GateInputError as exc:
        return _invalid_receipt(
            replay_path=path,
            error=str(exc),
            expected_sha256=expected_sha256,
            expected_episode_id=expected_episode_id,
            expected_agent_name=expected_agent_name,
            seat=seat if type(seat) is int else -1,
            raw_sha256=raw_sha256,
            raw_bytes=len(raw) if raw is not None else None,
            encoding=encoding,
            decoded_sha256=sha256_bytes(decoded) if decoded is not None else None,
            decoded_bytes=len(decoded) if decoded is not None else None,
        )


def atomic_write_json(path: str | os.PathLike[str], value: Any) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(value) + b"\n"
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=str(destination.parent)
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


