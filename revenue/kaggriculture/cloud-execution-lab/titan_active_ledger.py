#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Canonical ledger parsing for TITAN active-seam admission."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from titan_regression_gate import GateError


_ACTION_FIELDS = (
    "action_fingerprint",
    "action_sha256",
    "decision_fingerprint",
    "trace_sha256",
)
_RAW_ACTION_FIELDS = (
    "actions",
    "action_trace",
    "selected_actions",
    "decisions",
)
_CANDIDATE_CASH_FIELDS = ("candidate_cash", "own_cash", "final_cash")
_OPPONENT_CASH_FIELDS = ("opponent_cash", "rival_cash")
_CAUSAL_TRACE_FIELDS = ("causal_trace", "transition_trace", "world_action_trace")
_PREWORLD_DIGEST_FIELDS = (
    "preworld_sha256",
    "pre_world_sha256",
    "observation_sha256",
)
_PREWORLD_RAW_FIELDS = ("preworld", "pre_world", "observation")
_TESTED_ACTION_DIGEST_FIELDS = (
    "tested_action_sha256",
    "candidate_action_sha256",
    "own_action_sha256",
)
_TESTED_ACTION_RAW_FIELDS = ("tested_action", "candidate_action", "own_action")
_RIVAL_ACTION_DIGEST_FIELDS = ("rival_action_sha256", "opponent_action_sha256")
_RIVAL_ACTION_RAW_FIELDS = ("rival_action", "opponent_action")
_POSTWORLD_DIGEST_FIELDS = (
    "postworld_sha256",
    "post_world_sha256",
    "next_observation_sha256",
)
_POSTWORLD_RAW_FIELDS = ("postworld", "post_world", "next_observation")
_EXECUTION_PROVENANCE_ALIASES = {
    "evaluator_sha256": ("evaluator_sha256", "evaluation_sha256"),
    "loader_sha256": ("loader_sha256", "candidate_loader_sha256"),
}


@dataclass(frozen=True, order=True)
class EvidenceKey:
    """Exact paired-game identity, matching ``CellKey`` in the base gate."""

    engine_sha256: str
    environment_seed: str
    opponent_sha256: str
    seat: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "engine_sha256": self.engine_sha256,
            "environment_seed": self.environment_seed,
            "opponent_sha256": self.opponent_sha256,
            "seat": self.seat,
        }

@dataclass(frozen=True)
class CausalStep:
    """One tested-seat transition from an evaluator-owned trace."""

    step: str
    preworld_sha256: str
    tested_action_sha256: str
    rival_action_sha256: str
    postworld_sha256: str

@dataclass(frozen=True)
class RowEvidence:
    key: EvidenceKey
    action_fingerprint: str | None
    action_source: str | None
    margin: float
    candidate_cash: float | None
    opponent_cash: float | None
    causal_trace: tuple[CausalStep, ...] | None
    causal_source: str | None

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _issue(code: str, message: str, **details: Any) -> dict[str, Any]:
    row: dict[str, Any] = {"code": code, "message": message}
    if details:
        row["details"] = details
    return row

def _finite_optional(row: Mapping[str, Any], fields: Sequence[str], label: str) -> float | None:
    for field in fields:
        if field not in row:
            continue
        value = row[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise GateError(f"{label}.{field} must be numeric")
        result = float(value)
        if not math.isfinite(result):
            raise GateError(f"{label}.{field} must be finite")
        return result
    return None

def _row_margin(row: Mapping[str, Any], label: str) -> float:
    if "margin" in row:
        value = row["margin"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise GateError(f"{label}.margin must be numeric")
        result = float(value)
    elif "candidate_score" in row and "opponent_score" in row:
        left = row["candidate_score"]
        right = row["opponent_score"]
        if (
            isinstance(left, bool)
            or not isinstance(left, (int, float))
            or isinstance(right, bool)
            or not isinstance(right, (int, float))
        ):
            raise GateError(f"{label} score fields must be numeric")
        result = float(left) - float(right)
    else:
        raise GateError(f"{label} requires margin or candidate_score + opponent_score")
    if not math.isfinite(result):
        raise GateError(f"{label}.margin must be finite")
    return result

def _canonical_json_sha(value: Any, label: str) -> str:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise GateError(f"{label} is not canonical JSON: {exc}") from exc
    return _sha256(encoded)

def _normalize_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GateError(f"{label} must be a nonempty string")
    digest = value.strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise GateError(f"{label} must be a 64-character SHA-256 hex digest")
    return digest

def _fingerprint_aliases(
    row: Mapping[str, Any],
    *,
    digest_fields: Sequence[str],
    raw_fields: Sequence[str],
    label: str,
) -> tuple[str, str]:
    found: list[tuple[str, str]] = []
    for field in digest_fields:
        if field in row:
            found.append((_normalize_sha256(row[field], f"{label}.{field}"), field))
    for field in raw_fields:
        if field in row:
            found.append((_canonical_json_sha(row[field], f"{label}.{field}"), field))
    if not found:
        allowed = ", ".join((*digest_fields, *raw_fields))
        raise GateError(f"{label} requires one of: {allowed}")
    digests = {digest for digest, _ in found}
    if len(digests) != 1:
        raise GateError(
            f"{label} contains conflicting aliases: "
            + ", ".join(source for _, source in found)
        )
    return found[0][0], "+".join(source for _, source in found)

def _parse_causal_trace(
    row: Mapping[str, Any],
    label: str,
) -> tuple[tuple[CausalStep, ...] | None, str | None]:
    present = [field for field in _CAUSAL_TRACE_FIELDS if field in row]
    if not present:
        return None, None
    if len(present) != 1:
        raise GateError(f"{label} contains multiple causal trace aliases: {present}")
    source = present[0]
    raw_trace = row[source]
    if not isinstance(raw_trace, list) or not raw_trace:
        raise GateError(f"{label}.{source} must be a nonempty list")
    parsed: list[CausalStep] = []
    seen_steps: set[str] = set()
    for index, value in enumerate(raw_trace):
        if not isinstance(value, Mapping):
            raise GateError(f"{label}.{source}[{index}] must be an object")
        event_label = f"{label}.{source}[{index}]"
        step_value = value.get("step", value.get("turn"))
        if isinstance(step_value, bool) or step_value is None or not str(step_value).strip():
            raise GateError(f"{event_label}.step must be a nonempty scalar")
        step = str(step_value).strip()
        if step in seen_steps:
            raise GateError(f"{label}.{source} contains duplicate step {step!r}")
        seen_steps.add(step)
        preworld, _ = _fingerprint_aliases(
            value,
            digest_fields=_PREWORLD_DIGEST_FIELDS,
            raw_fields=_PREWORLD_RAW_FIELDS,
            label=event_label,
        )
        tested_action, _ = _fingerprint_aliases(
            value,
            digest_fields=_TESTED_ACTION_DIGEST_FIELDS,
            raw_fields=_TESTED_ACTION_RAW_FIELDS,
            label=event_label,
        )
        rival_action, _ = _fingerprint_aliases(
            value,
            digest_fields=_RIVAL_ACTION_DIGEST_FIELDS,
            raw_fields=_RIVAL_ACTION_RAW_FIELDS,
            label=event_label,
        )
        postworld, _ = _fingerprint_aliases(
            value,
            digest_fields=_POSTWORLD_DIGEST_FIELDS,
            raw_fields=_POSTWORLD_RAW_FIELDS,
            label=event_label,
        )
        parsed.append(CausalStep(
            step=step,
            preworld_sha256=preworld,
            tested_action_sha256=tested_action,
            rival_action_sha256=rival_action,
            postworld_sha256=postworld,
        ))
    return tuple(parsed), source

def _causal_action_fingerprint(trace: Sequence[CausalStep], label: str) -> str:
    actions = [
        {"step": row.step, "tested_action_sha256": row.tested_action_sha256}
        for row in trace
    ]
    return _canonical_json_sha(actions, label)

def _action_fingerprint(row: Mapping[str, Any], label: str) -> tuple[str | None, str | None]:
    for field in _ACTION_FIELDS:
        if field not in row:
            continue
        return _normalize_sha256(row[field], f"{label}.{field}"), field
    for field in _RAW_ACTION_FIELDS:
        if field in row:
            return _canonical_json_sha(row[field], f"{label}.{field}"), field
    causal_trace, causal_source = _parse_causal_trace(row, label)
    if causal_trace is not None:
        return (
            _causal_action_fingerprint(causal_trace, f"{label}.{causal_source}.tested_actions"),
            f"{causal_source}:tested_actions",
        )
    return None, None

def _row_key(row: Mapping[str, Any], top_engine: Any, label: str) -> EvidenceKey:
    engine = row.get("engine_sha256", top_engine)
    seed = row.get("environment_seed", row.get("seed"))
    opponent = row.get("opponent_sha256", row.get("opponent_archive_sha256"))
    seat = row.get("seat", row.get("candidate_seat"))
    for name, value in (
        ("engine_sha256", engine),
        ("environment_seed", seed),
        ("opponent_sha256", opponent),
    ):
        if value is None or not str(value).strip():
            raise GateError(f"{label}.{name} must be nonempty")
    if isinstance(seat, bool) or not isinstance(seat, int) or seat < 0:
        raise GateError(f"{label}.seat must be a nonnegative integer")
    return EvidenceKey(str(engine).strip(), str(seed).strip(), str(opponent).strip(), seat)

def _evidence_rows(ledger: Mapping[str, Any], label: str) -> dict[EvidenceKey, RowEvidence]:
    rows = ledger.get("rows")
    if not isinstance(rows, list) or not rows:
        raise GateError(f"{label}.rows must be a nonempty list")
    top_engine = ledger.get("engine_sha256")
    parsed: dict[EvidenceKey, RowEvidence] = {}
    for index, value in enumerate(rows):
        if not isinstance(value, Mapping):
            raise GateError(f"{label}.rows[{index}] must be an object")
        row_label = f"{label}.rows[{index}]"
        key = _row_key(value, top_engine, row_label)
        if key in parsed:
            raise GateError(f"{label}: duplicate evidence cell {key.as_dict()}")
        causal_trace, causal_source = _parse_causal_trace(value, row_label)
        if causal_trace is not None:
            fingerprint = _causal_action_fingerprint(
                causal_trace, f"{row_label}.{causal_source}.tested_actions"
            )
            source = f"{causal_source}:tested_actions"
        else:
            fingerprint, source = _action_fingerprint(value, row_label)
        parsed[key] = RowEvidence(
            key=key,
            action_fingerprint=fingerprint,
            action_source=source,
            margin=_row_margin(value, row_label),
            candidate_cash=_finite_optional(value, _CANDIDATE_CASH_FIELDS, row_label),
            opponent_cash=_finite_optional(value, _OPPONENT_CASH_FIELDS, row_label),
            causal_trace=causal_trace,
            causal_source=causal_source,
        )
    return parsed

def _numeric_summary(values: Sequence[float]) -> dict[str, Any] | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    median = (
        ordered[middle]
        if len(ordered) % 2
        else (ordered[middle - 1] + ordered[middle]) / 2.0
    )
    return {
        "cells": len(values),
        "mean": math.fsum(values) / len(values),
        "median": median,
        "minimum": min(values),
        "maximum": max(values),
        "sum": math.fsum(values),
    }

def _execution_provenance(
    ledger: Mapping[str, Any],
    label: str,
) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    missing: list[str] = []
    for canonical, aliases in _EXECUTION_PROVENANCE_ALIASES.items():
        present = [alias for alias in aliases if alias in ledger]
        if not present:
            missing.append(canonical)
            continue
        digests = {
            _normalize_sha256(ledger[alias], f"{label}.{alias}")
            for alias in present
        }
        if len(digests) != 1:
            raise GateError(f"{label} contains conflicting aliases for {canonical}")
        values[canonical] = next(iter(digests))
    return values, missing
