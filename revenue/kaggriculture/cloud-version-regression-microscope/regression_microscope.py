#!/usr/bin/env python3
"""TITAN cross-version, tested-seat action-bound regression microscope.

This module consumes *already executed* paired game evidence.  It does not run
Kaggriculture, call a provider, import candidate policy code, or mutate any
release artifact.  Its purpose is to answer a narrower and more trustworthy
question:

    Which tested-seat returned action first changed, and did that change help
    TITAN's own terminal objective on the exact same opponent/seed/seat cell?

The implementation is deliberately dependency-free and fail-closed.  A score
change in an action-identical cell is treated as confounded evidence, not as a
policy gain.  Candidate-own terminal cash is primary; margin and W/T/L are
secondary coherence guards.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

SCHEMA = "titan-regression-microscope/v1"
DEFAULT_EXPECTED_ACTION_COUNT = 719
COMPLETE_STATE = "complete"
FINAL_PHASE = "finalize"
OUTCOME_RANK = {"L": 0, "T": 1, "W": 2}


class MicroscopeError(ValueError):
    """Raised when the input cannot support an exact comparison."""


def canonical_json(value: Any) -> str:
    """Return the byte-stable JSON representation used for every digest."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _require_mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MicroscopeError(f"{where} must be an object")
    return value


def _require_sequence(value: Any, where: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise MicroscopeError(f"{where} must be an array")
    return value


def _require_int(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MicroscopeError(f"{where} must be an integer")
    return value


def _require_number(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MicroscopeError(f"{where} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise MicroscopeError(f"{where} must be a finite number")
    return result


def _require_nonempty_text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MicroscopeError(f"{where} must be a non-empty string")
    return value


def _coalesce(mapping: Mapping[str, Any], names: Iterable[str], where: str) -> Any:
    for name in names:
        if name in mapping:
            return mapping[name]
    joined = ", ".join(names)
    raise MicroscopeError(f"{where} is missing one of: {joined}")


def outcome(own_cash: float, rival_cash: float) -> str:
    if own_cash > rival_cash:
        return "W"
    if own_cash < rival_cash:
        return "L"
    return "T"


def _median(values: Sequence[float]) -> float:
    return float(statistics.median(values)) if values else 0.0


def _mean(values: Sequence[float]) -> float:
    return float(statistics.fmean(values)) if values else 0.0


def _fmt_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _normalise_action(action: Any) -> Any:
    """Remove wrapper-only step fields while preserving submitted action bytes."""
    if isinstance(action, Mapping) and set(action).issubset(
        {"step", "action", "tested_seat", "candidate_seat"}
    ) and "action" in action:
        return copy.deepcopy(action["action"])
    return copy.deepcopy(action)


def action_sequence_digest(actions: Sequence[Any]) -> str:
    return sha256_json([_normalise_action(action) for action in actions])


def _first_divergence(left: Sequence[Any], right: Sequence[Any]) -> int | None:
    if len(left) != len(right):
        raise MicroscopeError("cannot compare action sequences with different lengths")
    for index, (left_action, right_action) in enumerate(zip(left, right)):
        if canonical_json(_normalise_action(left_action)) != canonical_json(
            _normalise_action(right_action)
        ):
            return index
    return None


def _command_tokens(value: Any) -> list[str]:
    """Create a stable compact signature without pretending to interpret it."""
    tokens: list[str] = []

    def visit(node: Any) -> None:
        if isinstance(node, Mapping):
            type_value = None
            for key in ("type", "action", "command", "kind", "name"):
                candidate = node.get(key)
                if isinstance(candidate, str) and candidate:
                    type_value = candidate.upper()
                    break
            fields: list[str] = []
            if type_value is not None:
                fields.append(type_value)
            for key in ("product", "crop", "animal", "item", "resource"):
                candidate = node.get(key)
                if isinstance(candidate, (str, int, float)) and not isinstance(candidate, bool):
                    fields.append(str(candidate).upper())
                    break
            for key in ("quantity", "amount", "count", "number", "n"):
                candidate = node.get(key)
                if isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
                    fields.append(_fmt_number(float(candidate)))
                    break
            if fields:
                tokens.append(":".join(fields))
            else:
                for key in sorted(node):
                    visit(node[key])
        elif isinstance(node, Sequence) and not isinstance(node, (str, bytes, bytearray)):
            for item in node:
                visit(item)
        elif isinstance(node, str) and node.strip():
            tokens.append(node.strip().upper())

    visit(_normalise_action(value))
    if not tokens:
        tokens.append(f"sha256:{sha256_json(_normalise_action(value))[:16]}")
    return tokens


def divergence_signature(step: int, base_action: Any, candidate_action: Any) -> str:
    left = "+".join(_command_tokens(base_action))
    right = "+".join(_command_tokens(candidate_action))
    return f"step={step}|{left}->{right}"


@dataclass(frozen=True, order=True)
class CellKey:
    opponent: str
    seed: int
    seat: int

    def display(self) -> str:
        return f"{self.opponent}|seed={self.seed}|seat={self.seat}"


@dataclass(frozen=True)
class Terminal:
    own_cash: float
    rival_cash: float
    own_score: float
    rival_score: float
    terminal_world_sha256: str
    full_trace_sha256: str

    @property
    def own_outcome(self) -> str:
        return outcome(self.own_score, self.rival_score)


@dataclass(frozen=True)
class Cell:
    key: CellKey
    engine_sha256: str
    opponent_sha256: str
    state: str
    phase: str
    actions: tuple[Any, ...]
    action_sha256: str
    terminal: Terminal


@dataclass(frozen=True)
class Version:
    label: str
    source_identity: Mapping[str, Any]
    cells: Mapping[CellKey, Cell]


def _parse_terminal(raw_cell: Mapping[str, Any], where: str) -> Terminal:
    raw_terminal = _require_mapping(raw_cell.get("terminal", raw_cell), f"{where}.terminal")
    own_cash = _require_number(
        _coalesce(raw_terminal, ("own_cash", "candidate_cash", "tested_cash"), f"{where}.terminal.own_cash"),
        f"{where}.terminal.own_cash",
    )
    rival_cash = _require_number(
        _coalesce(raw_terminal, ("rival_cash", "opponent_cash"), f"{where}.terminal.rival_cash"),
        f"{where}.terminal.rival_cash",
    )
    own_score = _require_number(
        raw_terminal.get("own_score", raw_terminal.get("candidate_score", own_cash)),
        f"{where}.terminal.own_score",
    )
    rival_score = _require_number(
        raw_terminal.get("rival_score", raw_terminal.get("opponent_score", rival_cash)),
        f"{where}.terminal.rival_score",
    )
    terminal_world_sha256 = _require_nonempty_text(
        _coalesce(
            raw_terminal,
            ("terminal_world_sha256", "world_sha256", "state_sha256"),
            f"{where}.terminal.terminal_world_sha256",
        ),
        f"{where}.terminal.terminal_world_sha256",
    )
    full_trace_sha256 = _require_nonempty_text(
        _coalesce(
            raw_terminal,
            ("full_trace_sha256", "trace_sha256"),
            f"{where}.terminal.full_trace_sha256",
        ),
        f"{where}.terminal.full_trace_sha256",
    )
    return Terminal(
        own_cash=own_cash,
        rival_cash=rival_cash,
        own_score=own_score,
        rival_score=rival_score,
        terminal_world_sha256=terminal_world_sha256,
        full_trace_sha256=full_trace_sha256,
    )


def _parse_cell(raw: Any, where: str, expected_action_count: int) -> Cell:
    cell = _require_mapping(raw, where)
    opponent = _require_nonempty_text(cell.get("opponent"), f"{where}.opponent")
    seed = _require_int(cell.get("seed"), f"{where}.seed")
    seat = _require_int(
        _coalesce(cell, ("seat", "candidate_seat", "tested_seat"), f"{where}.seat"),
        f"{where}.seat",
    )
    if seat not in (0, 1):
        raise MicroscopeError(f"{where}.seat must be 0 or 1")
    state = _require_nonempty_text(cell.get("state"), f"{where}.state").lower()
    phase = _require_nonempty_text(cell.get("phase"), f"{where}.phase").lower()
    if state != COMPLETE_STATE:
        raise MicroscopeError(f"{where}.state must be {COMPLETE_STATE!r}, got {state!r}")
    if phase != FINAL_PHASE:
        raise MicroscopeError(f"{where}.phase must be {FINAL_PHASE!r}, got {phase!r}")

    engine_sha256 = _require_nonempty_text(cell.get("engine_sha256"), f"{where}.engine_sha256")
    opponent_sha256 = _require_nonempty_text(cell.get("opponent_sha256"), f"{where}.opponent_sha256")
    raw_actions = _coalesce(
        cell,
        ("tested_seat_actions", "candidate_actions", "actions"),
        f"{where}.tested_seat_actions",
    )
    actions_seq = _require_sequence(raw_actions, f"{where}.tested_seat_actions")
    actions = tuple(_normalise_action(action) for action in actions_seq)
    if len(actions) != expected_action_count:
        raise MicroscopeError(
            f"{where}.tested_seat_actions must contain exactly "
            f"{expected_action_count} returned actions, got {len(actions)}"
        )
    action_sha256 = action_sequence_digest(actions)
    declared_digest = cell.get("tested_action_sha256", cell.get("candidate_action_sha256"))
    if declared_digest is not None:
        declared_digest = _require_nonempty_text(declared_digest, f"{where}.tested_action_sha256")
        if declared_digest != action_sha256:
            raise MicroscopeError(
                f"{where}.tested_action_sha256 does not match the exact returned-action sequence"
            )
    terminal = _parse_terminal(cell, where)
    return Cell(
        key=CellKey(opponent=opponent, seed=seed, seat=seat),
        engine_sha256=engine_sha256,
        opponent_sha256=opponent_sha256,
        state=state,
        phase=phase,
        actions=actions,
        action_sha256=action_sha256,
        terminal=terminal,
    )


def _parse_source_identity(raw: Any, where: str) -> Mapping[str, Any]:
    identity = _require_mapping(raw, where)
    required = ("source_sha256", "archive_sha256", "config_sha256")
    parsed: dict[str, Any] = {}
    for field in required:
        parsed[field] = _require_nonempty_text(identity.get(field), f"{where}.{field}")
    config_text = identity.get("config_text")
    if config_text is not None:
        config_text = _require_nonempty_text(config_text, f"{where}.config_text")
        actual_config_sha256 = hashlib.sha256(config_text.encode("utf-8")).hexdigest()
        if actual_config_sha256 != parsed["config_sha256"]:
            raise MicroscopeError(f"{where}.config_text bytes do not match config_sha256")
        try:
            json.loads(config_text)
        except json.JSONDecodeError as exc:
            raise MicroscopeError(f"{where}.config_text is not valid JSON: {exc}") from exc
        parsed["config_text"] = config_text
    for key, value in identity.items():
        if key not in parsed and isinstance(value, str) and value:
            parsed[str(key)] = value
    return parsed


def parse_dataset(raw: Any) -> tuple[int, Mapping[str, Version], Mapping[str, Any]]:
    root = _require_mapping(raw, "dataset")
    schema = root.get("schema", SCHEMA)
    if schema != SCHEMA:
        raise MicroscopeError(f"dataset.schema must be {SCHEMA!r}, got {schema!r}")
    expected_action_count = _require_int(
        root.get("expected_action_count", DEFAULT_EXPECTED_ACTION_COUNT),
        "dataset.expected_action_count",
    )
    if expected_action_count <= 0:
        raise MicroscopeError("dataset.expected_action_count must be positive")
    raw_versions = _require_mapping(root.get("versions"), "dataset.versions")
    if len(raw_versions) < 2:
        raise MicroscopeError("dataset.versions must contain at least two versions")

    versions: dict[str, Version] = {}
    for raw_label, raw_version in raw_versions.items():
        label = _require_nonempty_text(raw_label, "dataset.versions label")
        version_obj = _require_mapping(raw_version, f"dataset.versions[{label!r}]")
        source_identity = _parse_source_identity(
            version_obj.get("identity"), f"dataset.versions[{label!r}].identity"
        )
        raw_cells = _require_sequence(version_obj.get("cells"), f"dataset.versions[{label!r}].cells")
        cells: dict[CellKey, Cell] = {}
        for index, raw_cell in enumerate(raw_cells):
            where = f"dataset.versions[{label!r}].cells[{index}]"
            parsed_cell = _parse_cell(raw_cell, where, expected_action_count)
            if parsed_cell.key in cells:
                raise MicroscopeError(
                    f"dataset.versions[{label!r}] contains duplicate cell {parsed_cell.key.display()}"
                )
            cells[parsed_cell.key] = parsed_cell
        if not cells:
            raise MicroscopeError(f"dataset.versions[{label!r}].cells cannot be empty")
        versions[label] = Version(label=label, source_identity=source_identity, cells=cells)
    metadata = {key: value for key, value in root.items() if key != "versions"}
    return expected_action_count, versions, metadata


def _pair_identity_issues(base: Cell, candidate: Cell) -> list[str]:
    issues: list[str] = []
    if base.engine_sha256 != candidate.engine_sha256:
        issues.append("engine_sha256_mismatch")
    if base.opponent_sha256 != candidate.opponent_sha256:
        issues.append("opponent_sha256_mismatch")
    return issues


def compare_cell(base: Cell, candidate: Cell) -> Mapping[str, Any]:
    if base.key != candidate.key:
        raise MicroscopeError("compare_cell requires the same opponent/seed/seat key")
    identity_issues = _pair_identity_issues(base, candidate)
    first_divergence = _first_divergence(base.actions, candidate.actions)
    action_changed = first_divergence is not None

    bt = base.terminal
    ct = candidate.terminal
    own_delta = ct.own_cash - bt.own_cash
    rival_delta = ct.rival_cash - bt.rival_cash
    base_margin = bt.own_score - bt.rival_score
    candidate_margin = ct.own_score - ct.rival_score
    margin_delta = candidate_margin - base_margin
    base_outcome = bt.own_outcome
    candidate_outcome = ct.own_outcome
    outcome_delta = OUTCOME_RANK[candidate_outcome] - OUTCOME_RANK[base_outcome]

    causality_issues: list[str] = list(identity_issues)
    if not action_changed:
        if bt.terminal_world_sha256 != ct.terminal_world_sha256:
            causality_issues.append("action_identical_terminal_world_drift")
        if bt.full_trace_sha256 != ct.full_trace_sha256:
            causality_issues.append("action_identical_full_trace_drift")
        if bt.own_cash != ct.own_cash:
            causality_issues.append("action_identical_own_cash_drift")
        if bt.rival_cash != ct.rival_cash:
            causality_issues.append("action_identical_rival_cash_drift")
        if bt.own_score != ct.own_score:
            causality_issues.append("action_identical_own_score_drift")
        if bt.rival_score != ct.rival_score:
            causality_issues.append("action_identical_rival_score_drift")
    elif bt.full_trace_sha256 == ct.full_trace_sha256:
        causality_issues.append("action_changed_but_full_trace_identical")

    if causality_issues:
        classification = "invalid_confounded"
    elif not action_changed:
        classification = "inert"
    elif own_delta == 0 and rival_delta == 0 and outcome_delta == 0:
        classification = "realized_neutral"
    elif own_delta > 0 and margin_delta >= 0 and outcome_delta >= 0:
        classification = "candidate_benefit"
    elif own_delta < 0 and margin_delta <= 0 and outcome_delta <= 0:
        classification = "candidate_harm"
    else:
        classification = "objective_conflict"

    signature = None
    base_action = None
    candidate_action = None
    if first_divergence is not None:
        base_action = base.actions[first_divergence]
        candidate_action = candidate.actions[first_divergence]
        signature = divergence_signature(first_divergence, base_action, candidate_action)

    return {
        "cell": {
            "opponent": base.key.opponent,
            "seed": base.key.seed,
            "seat": base.key.seat,
            "key": base.key.display(),
        },
        "classification": classification,
        "causality_issues": causality_issues,
        "action_changed": action_changed,
        "base_action_sha256": base.action_sha256,
        "candidate_action_sha256": candidate.action_sha256,
        "first_divergence_step": first_divergence,
        "first_divergence_signature": signature,
        "first_divergence_base_action": base_action,
        "first_divergence_candidate_action": candidate_action,
        "base": {
            "own_cash": bt.own_cash,
            "rival_cash": bt.rival_cash,
            "own_score": bt.own_score,
            "rival_score": bt.rival_score,
            "margin": base_margin,
            "outcome": base_outcome,
            "terminal_world_sha256": bt.terminal_world_sha256,
            "full_trace_sha256": bt.full_trace_sha256,
        },
        "candidate": {
            "own_cash": ct.own_cash,
            "rival_cash": ct.rival_cash,
            "own_score": ct.own_score,
            "rival_score": ct.rival_score,
            "margin": candidate_margin,
            "outcome": candidate_outcome,
            "terminal_world_sha256": ct.terminal_world_sha256,
            "full_trace_sha256": ct.full_trace_sha256,
        },
        "delta": {
            "own_cash": own_delta,
            "rival_cash": rival_delta,
            "margin": margin_delta,
            "outcome_rank": outcome_delta,
        },
    }


def _stratum_summary(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    own_deltas = [float(row["delta"]["own_cash"]) for row in rows]
    margin_deltas = [float(row["delta"]["margin"]) for row in rows]
    return {
        "cells": len(rows),
        "mean_own_cash_delta": _mean(own_deltas),
        "min_own_cash_delta": min(own_deltas) if own_deltas else 0.0,
        "mean_margin_delta": _mean(margin_deltas),
        "min_margin_delta": min(margin_deltas) if margin_deltas else 0.0,
        "new_losses": sum(
            1
            for row in rows
            if row["base"]["outcome"] != "L" and row["candidate"]["outcome"] == "L"
        ),
    }


def _promotion_verdict(rows: Sequence[Mapping[str, Any]]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    invalid = [row for row in rows if row["classification"] == "invalid_confounded"]
    if invalid:
        reasons.append(f"{len(invalid)} confounded or identity-invalid cells")
        return "INVALID", reasons

    action_changed = [row for row in rows if row["action_changed"]]
    if not action_changed:
        reasons.append("zero tested-seat returned-action activations")
        return "NO_SIGNAL", reasons

    own_deltas = [float(row["delta"]["own_cash"]) for row in rows]
    margin_deltas = [float(row["delta"]["margin"]) for row in rows]
    new_losses = [
        row
        for row in rows
        if row["base"]["outcome"] != "L" and row["candidate"]["outcome"] == "L"
    ]
    lost_wins = [
        row
        for row in rows
        if row["base"]["outcome"] == "W" and row["candidate"]["outcome"] != "W"
    ]
    negative_own = [row for row in rows if float(row["delta"]["own_cash"]) < 0]
    conflicts = [row for row in rows if row["classification"] == "objective_conflict"]

    if new_losses:
        reasons.append(f"{len(new_losses)} new losses")
    if lost_wins:
        reasons.append(f"{len(lost_wins)} lost wins")
    if negative_own:
        reasons.append(f"{len(negative_own)} cells reduce candidate-own terminal cash")
    if new_losses or lost_wins or negative_own:
        return "REGRESSION", reasons

    if conflicts:
        reasons.append(f"{len(conflicts)} own/margin/WTL objective conflicts")
        return "MORE_EVIDENCE", reasons

    strata: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        cell_data = row["cell"]
        strata[(str(cell_data["opponent"]), int(cell_data["seat"]))].append(row)
    negative_strata = []
    for key, stratum_rows in sorted(strata.items()):
        summary = _stratum_summary(stratum_rows)
        if summary["mean_own_cash_delta"] < 0 or summary["mean_margin_delta"] < 0:
            negative_strata.append((key, summary))
    if negative_strata:
        reasons.append(
            f"{len(negative_strata)} opponent×seat strata have negative own or margin mean"
        )
        return "MORE_EVIDENCE", reasons

    if sum(own_deltas) <= 0:
        reasons.append("aggregate candidate-own terminal-cash signal is not positive")
        return "NO_SIGNAL", reasons
    if _median(own_deltas) < 0:
        reasons.append("median candidate-own terminal-cash delta is negative")
        return "MORE_EVIDENCE", reasons
    if sum(margin_deltas) < 0:
        reasons.append("aggregate margin delta is negative")
        return "MORE_EVIDENCE", reasons

    reasons.append("action-bound positive own signal with no negative cell or outcome regression")
    return "ADVANCE", reasons


def compare_versions(base: Version, candidate: Version) -> Mapping[str, Any]:
    base_keys = set(base.cells)
    candidate_keys = set(candidate.cells)
    missing_from_candidate = sorted(base_keys - candidate_keys)
    extra_in_candidate = sorted(candidate_keys - base_keys)
    if missing_from_candidate or extra_in_candidate:
        detail: list[str] = []
        if missing_from_candidate:
            detail.append("missing=" + ",".join(key.display() for key in missing_from_candidate))
        if extra_in_candidate:
            detail.append("extra=" + ",".join(key.display() for key in extra_in_candidate))
        raise MicroscopeError(
            f"comparison {base.label!r}->{candidate.label!r} grid mismatch: "
            + "; ".join(detail)
        )

    rows = [compare_cell(base.cells[key], candidate.cells[key]) for key in sorted(base_keys)]
    verdict, verdict_reasons = _promotion_verdict(rows)
    own_deltas = [float(row["delta"]["own_cash"]) for row in rows]
    rival_deltas = [float(row["delta"]["rival_cash"]) for row in rows]
    margin_deltas = [float(row["delta"]["margin"]) for row in rows]
    classifications = Counter(str(row["classification"]) for row in rows)

    strata_rows: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        cell_data = row["cell"]
        strata_rows[(str(cell_data["opponent"]), int(cell_data["seat"]))].append(row)
    strata = {
        f"{opponent}|seat={seat}": _stratum_summary(group)
        for (opponent, seat), group in sorted(strata_rows.items())
    }

    new_losses = sum(
        1
        for row in rows
        if row["base"]["outcome"] != "L" and row["candidate"]["outcome"] == "L"
    )
    lost_wins = sum(
        1
        for row in rows
        if row["base"]["outcome"] == "W" and row["candidate"]["outcome"] != "W"
    )
    gained_wins = sum(
        1
        for row in rows
        if row["base"]["outcome"] != "W" and row["candidate"]["outcome"] == "W"
    )

    return {
        "base": base.label,
        "candidate": candidate.label,
        "base_identity": dict(base.source_identity),
        "candidate_identity": dict(candidate.source_identity),
        "cells": rows,
        "summary": {
            "cell_count": len(rows),
            "action_changed_cells": sum(1 for row in rows if row["action_changed"]),
            "action_identical_cells": sum(1 for row in rows if not row["action_changed"]),
            "classifications": dict(sorted(classifications.items())),
            "own_cash_delta_sum": sum(own_deltas),
            "own_cash_delta_mean": _mean(own_deltas),
            "own_cash_delta_median": _median(own_deltas),
            "own_cash_delta_min": min(own_deltas) if own_deltas else 0.0,
            "own_cash_delta_max": max(own_deltas) if own_deltas else 0.0,
            "rival_cash_delta_sum": sum(rival_deltas),
            "rival_cash_delta_mean": _mean(rival_deltas),
            "margin_delta_sum": sum(margin_deltas),
            "margin_delta_mean": _mean(margin_deltas),
            "margin_delta_median": _median(margin_deltas),
            "new_losses": new_losses,
            "lost_wins": lost_wins,
            "gained_wins": gained_wins,
            "promotion_verdict": verdict,
            "promotion_reasons": verdict_reasons,
            "strata": strata,
        },
    }


def _rows_by_key(comparison: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    return {str(row["cell"]["key"]): row for row in comparison["cells"]}


def _is_regression_row(row: Mapping[str, Any]) -> bool:
    return (
        row["classification"] in {"candidate_harm", "objective_conflict"}
        and (
            float(row["delta"]["own_cash"]) < 0
            or int(row["delta"]["outcome_rank"]) < 0
        )
    )


def _is_repaired_to_baseline(
    baseline_to_middle: Mapping[str, Any],
    middle_to_candidate: Mapping[str, Any],
    baseline_to_candidate: Mapping[str, Any],
) -> bool:
    if not _is_regression_row(baseline_to_middle):
        return False
    if baseline_to_candidate["classification"] == "invalid_confounded":
        return False
    return (
        float(baseline_to_candidate["delta"]["own_cash"]) >= 0
        and int(baseline_to_candidate["delta"]["outcome_rank"]) >= 0
        and float(middle_to_candidate["delta"]["own_cash"]) > 0
    )


def _cluster_signatures(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    groups: MutableMapping[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        signature = row.get("first_divergence_signature")
        if signature:
            groups[str(signature)].append(row)
    clusters: list[Mapping[str, Any]] = []
    for signature, group in groups.items():
        own_deltas = [float(row["delta"]["own_cash"]) for row in group]
        margin_deltas = [float(row["delta"]["margin"]) for row in group]
        clusters.append(
            {
                "signature": signature,
                "count": len(group),
                "cells": [row["cell"]["key"] for row in group],
                "own_cash_delta_sum": sum(own_deltas),
                "own_cash_delta_mean": _mean(own_deltas),
                "own_cash_delta_min": min(own_deltas),
                "margin_delta_sum": sum(margin_deltas),
                "new_losses": sum(
                    1
                    for row in group
                    if row["base"]["outcome"] != "L"
                    and row["candidate"]["outcome"] == "L"
                ),
            }
        )
    return sorted(
        clusters,
        key=lambda item: (
            float(item["own_cash_delta_sum"]),
            -int(item["count"]),
            str(item["signature"]),
        ),
    )


def three_way_report(versions: Mapping[str, Version], labels: Sequence[str]) -> Mapping[str, Any]:
    if len(labels) != 3:
        raise MicroscopeError("three_way must contain exactly three version labels")
    missing = [label for label in labels if label not in versions]
    if missing:
        raise MicroscopeError(f"three_way refers to unknown versions: {', '.join(missing)}")
    baseline_label, middle_label, candidate_label = labels
    baseline = versions[baseline_label]
    middle = versions[middle_label]
    candidate = versions[candidate_label]

    baseline_to_middle = compare_versions(baseline, middle)
    middle_to_candidate = compare_versions(middle, candidate)
    baseline_to_candidate = compare_versions(baseline, candidate)
    bm_rows = _rows_by_key(baseline_to_middle)
    mc_rows = _rows_by_key(middle_to_candidate)
    bc_rows = _rows_by_key(baseline_to_candidate)

    regression_keys = sorted(key for key, row in bm_rows.items() if _is_regression_row(row))
    repaired_keys = sorted(
        key
        for key in regression_keys
        if _is_repaired_to_baseline(bm_rows[key], mc_rows[key], bc_rows[key])
    )
    unrepaired_keys = sorted(set(regression_keys) - set(repaired_keys))
    new_candidate_regressions = sorted(
        key
        for key, row in bc_rows.items()
        if _is_regression_row(row) and key not in regression_keys
    )
    harmful_rows = [bm_rows[key] for key in regression_keys]

    return {
        "labels": {
            "baseline": baseline_label,
            "middle": middle_label,
            "candidate": candidate_label,
        },
        "comparisons": {
            f"{baseline_label}->{middle_label}": baseline_to_middle,
            f"{middle_label}->{candidate_label}": middle_to_candidate,
            f"{baseline_label}->{candidate_label}": baseline_to_candidate,
        },
        "attribution": {
            "middle_regression_cells": regression_keys,
            "candidate_repaired_cells": repaired_keys,
            "candidate_unrepaired_cells": unrepaired_keys,
            "candidate_new_regression_cells": new_candidate_regressions,
            "harmful_first_divergence_clusters": _cluster_signatures(harmful_rows),
            "net_promotion_verdict": baseline_to_candidate["summary"]["promotion_verdict"],
        },
    }


def _config_from_identity(version: Version) -> Any:
    config_text = version.source_identity.get("config_text")
    if not isinstance(config_text, str) or not config_text:
        raise MicroscopeError(
            f"version {version.label!r} lacks exact identity.config_text required for feature surgery"
        )
    try:
        return json.loads(config_text)
    except json.JSONDecodeError as exc:
        raise MicroscopeError(
            f"version {version.label!r} identity.config_text is invalid JSON: {exc}"
        ) from exc


def _json_diff_paths(left: Any, right: Any, path: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
    if type(left) is not type(right):
        return [path]
    if isinstance(left, Mapping):
        paths: list[tuple[str, ...]] = []
        keys = sorted(set(left) | set(right), key=str)
        for key in keys:
            key_text = str(key)
            if key not in left or key not in right:
                paths.append(path + (key_text,))
            else:
                paths.extend(_json_diff_paths(left[key], right[key], path + (key_text,)))
        return paths
    if isinstance(left, list):
        paths = []
        if len(left) != len(right):
            paths.append(path + ("<length>",))
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            paths.extend(_json_diff_paths(left_item, right_item, path + (str(index),)))
        return paths
    return [] if left == right else [path]


def _get_json_path(value: Any, path: Sequence[str]) -> Any:
    node = value
    for component in path:
        if not isinstance(node, Mapping) or component not in node:
            raise MicroscopeError("feature config path does not exist: " + ".".join(path))
        node = node[component]
    return node


def _feature_arm_closure_issues(
    *,
    control: Version,
    arm: Version,
    feature: str,
    feature_path: Sequence[str],
    canonical_control_config_sha256: str,
) -> list[str]:
    issues: list[str] = []
    if control.source_identity["config_sha256"] != canonical_control_config_sha256:
        issues.append("all_enabled_control_bytes_not_canonical")
    try:
        control_config = _config_from_identity(control)
        arm_config = _config_from_identity(arm)
    except MicroscopeError as exc:
        issues.append(str(exc))
        return issues
    expected_path = tuple(feature_path) + (feature,)
    diff_paths = _json_diff_paths(control_config, arm_config)
    if diff_paths != [expected_path]:
        rendered = [".".join(path) or "<root>" for path in diff_paths]
        issues.append("arm_not_exactly_one_feature_bit:" + ",".join(rendered))
        return issues
    try:
        control_value = _get_json_path(control_config, expected_path)
        arm_value = _get_json_path(arm_config, expected_path)
    except MicroscopeError as exc:
        issues.append(str(exc))
        return issues
    if control_value is not True or arm_value is not False:
        issues.append("feature_bit_must_transition_true_to_false")
    return issues


def feature_surgery_report(versions: Mapping[str, Version], spec: Mapping[str, Any]) -> Mapping[str, Any]:
    control_label = _require_nonempty_text(spec.get("control"), "feature_arms.control")
    if control_label not in versions:
        raise MicroscopeError(f"feature_arms.control {control_label!r} is not a version")
    disabled = _require_mapping(spec.get("disabled"), "feature_arms.disabled")
    if not disabled:
        raise MicroscopeError("feature_arms.disabled cannot be empty")
    canonical_control_config_sha256 = _require_nonempty_text(
        spec.get("canonical_control_config_sha256"),
        "feature_arms.canonical_control_config_sha256",
    )
    raw_feature_path = spec.get("feature_path", ["features"])
    feature_path_seq = _require_sequence(raw_feature_path, "feature_arms.feature_path")
    feature_path = [
        _require_nonempty_text(item, f"feature_arms.feature_path[{index}]")
        for index, item in enumerate(feature_path_seq)
    ]

    recommendations: list[Mapping[str, Any]] = []
    for feature, arm_value in sorted(disabled.items(), key=lambda item: str(item[0])):
        feature_name = _require_nonempty_text(feature, "feature_arms feature name")
        arm_label = _require_nonempty_text(
            arm_value, f"feature_arms.disabled[{feature_name!r}]"
        )
        if arm_label not in versions:
            raise MicroscopeError(
                f"feature_arms.disabled[{feature_name!r}] refers to unknown version {arm_label!r}"
            )
        control_version = versions[control_label]
        arm_version = versions[arm_label]
        closure_issues = _feature_arm_closure_issues(
            control=control_version,
            arm=arm_version,
            feature=feature_name,
            feature_path=feature_path,
            canonical_control_config_sha256=canonical_control_config_sha256,
        )
        comparison = compare_versions(control_version, arm_version)
        verdict = comparison["summary"]["promotion_verdict"]
        if closure_issues:
            recommendation = "invalid_arm"
        elif verdict == "ADVANCE":
            recommendation = "candidate_disable"
        elif verdict == "REGRESSION":
            recommendation = "candidate_keep"
        else:
            recommendation = "needs_more_evidence"
        recommendations.append(
            {
                "feature": feature_name,
                "control": control_label,
                "disabled_arm": arm_label,
                "recommendation": recommendation,
                "config_closure_issues": closure_issues,
                "comparison": comparison,
            }
        )
    return {
        "control": control_label,
        "canonical_control_config_sha256": canonical_control_config_sha256,
        "feature_path": feature_path,
        "recommendations": recommendations,
    }


def build_report(raw: Any) -> Mapping[str, Any]:
    expected_action_count, versions, metadata = parse_dataset(raw)
    labels = metadata.get("three_way")
    if labels is None:
        labels = list(versions)[:3] if len(versions) >= 3 else None
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "expected_action_count": expected_action_count,
        "input_sha256": sha256_json(raw),
        "version_labels": list(versions),
    }
    if labels is not None:
        labels = _require_sequence(labels, "dataset.three_way")
        parsed_labels = [
            _require_nonempty_text(label, f"dataset.three_way[{index}]")
            for index, label in enumerate(labels)
        ]
        report["three_way"] = three_way_report(versions, parsed_labels)
    else:
        first, second = list(versions)[:2]
        report["comparison"] = compare_versions(versions[first], versions[second])

    feature_spec = metadata.get("feature_arms")
    if feature_spec is not None:
        report["feature_surgery"] = feature_surgery_report(
            versions, _require_mapping(feature_spec, "dataset.feature_arms")
        )
    report["report_sha256"] = sha256_json(report)
    return report


def _comparison_markdown(name: str, comparison: Mapping[str, Any]) -> list[str]:
    summary = comparison["summary"]
    lines = [
        f"## {name}",
        "",
        f"- Verdict: **{summary['promotion_verdict']}**",
        f"- Cells: {summary['cell_count']}; tested-seat action changes: {summary['action_changed_cells']}",
        f"- Own cash Δ: sum {_fmt_number(float(summary['own_cash_delta_sum']))}, "
        f"mean {_fmt_number(float(summary['own_cash_delta_mean']))}, "
        f"median {_fmt_number(float(summary['own_cash_delta_median']))}, "
        f"min {_fmt_number(float(summary['own_cash_delta_min']))}",
        f"- Margin Δ: sum {_fmt_number(float(summary['margin_delta_sum']))}, "
        f"mean {_fmt_number(float(summary['margin_delta_mean']))}",
        f"- Outcome transitions: {summary['gained_wins']} gained wins, "
        f"{summary['lost_wins']} lost wins, {summary['new_losses']} new losses",
        f"- Reasons: {'; '.join(summary['promotion_reasons'])}",
        "",
        "| Cell | Class | First divergence | Own Δ | Margin Δ | Outcome |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in comparison["cells"]:
        step = row["first_divergence_step"]
        step_text = "—" if step is None else str(step)
        lines.append(
            "| {cell} | {classification} | {step} | {own} | {margin} | {base}→{candidate} |".format(
                cell=row["cell"]["key"],
                classification=row["classification"],
                step=step_text,
                own=_fmt_number(float(row["delta"]["own_cash"])),
                margin=_fmt_number(float(row["delta"]["margin"])),
                base=row["base"]["outcome"],
                candidate=row["candidate"]["outcome"],
            )
        )
    lines.append("")
    return lines


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# TITAN Version Regression Microscope",
        "",
        f"Input SHA-256: `{report['input_sha256']}`  ",
        f"Report SHA-256: `{report['report_sha256']}`  ",
        f"Expected tested-seat lifecycle: `{report['expected_action_count']}` returned actions per cell.",
        "",
        "> Candidate-own terminal cash is primary. Margin and W/T/L are coherence guards. "
        "Action-identical score or world drift is invalid evidence.",
        "",
    ]
    three_way = report.get("three_way")
    if three_way is not None:
        attribution = three_way["attribution"]
        labels = three_way["labels"]
        lines.extend(
            [
                "## Three-way attribution",
                "",
                f"- Baseline: `{labels['baseline']}`; middle: `{labels['middle']}`; candidate: `{labels['candidate']}`",
                f"- Middle regression cells: {len(attribution['middle_regression_cells'])}",
                f"- Candidate repairs to at least baseline: {len(attribution['candidate_repaired_cells'])}",
                f"- Unrepaired middle regressions: {len(attribution['candidate_unrepaired_cells'])}",
                f"- New candidate regressions: {len(attribution['candidate_new_regression_cells'])}",
                f"- Net verdict: **{attribution['net_promotion_verdict']}**",
                "",
            ]
        )
        clusters = attribution["harmful_first_divergence_clusters"]
        if clusters:
            lines.extend(
                [
                    "### Repeated harmful first-divergence signatures",
                    "",
                    "| Signature | Cells | Own Δ sum | Margin Δ sum | New losses |",
                    "|---|---:|---:|---:|---:|",
                ]
            )
            for cluster in clusters:
                lines.append(
                    "| `{signature}` | {count} | {own} | {margin} | {losses} |".format(
                        signature=str(cluster["signature"]).replace("|", "\\|"),
                        count=cluster["count"],
                        own=_fmt_number(float(cluster["own_cash_delta_sum"])),
                        margin=_fmt_number(float(cluster["margin_delta_sum"])),
                        losses=cluster["new_losses"],
                    )
                )
            lines.append("")
        for name, comparison in three_way["comparisons"].items():
            lines.extend(_comparison_markdown(name, comparison))
    else:
        comparison = report["comparison"]
        lines.extend(_comparison_markdown(f"{comparison['base']}→{comparison['candidate']}", comparison))

    feature_surgery = report.get("feature_surgery")
    if feature_surgery is not None:
        lines.extend(
            [
                "## Feature surgery",
                "",
                "| Feature | Disabled arm | Recommendation | Config closure | Verdict | Own Δ sum | New losses |",
                "|---|---|---|---|---|---:|---:|",
            ]
        )
        for item in feature_surgery["recommendations"]:
            summary = item["comparison"]["summary"]
            lines.append(
                "| {feature} | `{arm}` | **{recommendation}** | {closure} | {verdict} | {own} | {losses} |".format(
                    feature=item["feature"],
                    arm=item["disabled_arm"],
                    recommendation=item["recommendation"],
                    closure="PASS" if not item["config_closure_issues"] else "; ".join(item["config_closure_issues"]),
                    verdict=summary["promotion_verdict"],
                    own=_fmt_number(float(summary["own_cash_delta_sum"])),
                    losses=summary["new_losses"],
                )
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise MicroscopeError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise MicroscopeError(f"invalid JSON in {path}: {exc}") from exc


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed, action-bound V1/V2/V3 regression attribution"
    )
    parser.add_argument("input", type=Path, help="normalized paired-evidence JSON")
    parser.add_argument("--json-out", type=Path, required=True, help="machine report")
    parser.add_argument("--markdown-out", type=Path, required=True, help="human receipt")
    args = parser.parse_args(argv)
    try:
        raw = _read_json(args.input)
        report = build_report(raw)
        _write_text(args.json_out, json.dumps(report, indent=2, sort_keys=True) + "\n")
        _write_text(args.markdown_out, render_markdown(report))
    except MicroscopeError as exc:
        print(f"regression microscope: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
