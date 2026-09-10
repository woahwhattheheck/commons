# SPDX-License-Identifier: Apache-2.0
"""Validation and policy primitives for TITAN's paired promotion gate."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

SCHEMA = "titan.paired-promotion.v1"
FIELD_SCHEMA = "titan.paired-field.v1"
POLICY_SCHEMA = "titan.paired-promotion-policy.v1"
CellKey = tuple[str, int, int]


class PromotionData(ValueError):
    """Malformed or ambiguous promotion evidence."""


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PromotionData(f"{label} must be a finite number")
    value = float(value)
    if not math.isfinite(value):
        raise PromotionData(f"{label} must be a finite number")
    return value


def _name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PromotionData(f"{label} must be a nonempty string")
    return value


def _key_json(key: CellKey) -> dict[str, Any]:
    return {"opponent": key[0], "seed": key[1], "candidate_seat": key[2]}


@dataclass(frozen=True)
class PromotionPolicy:
    max_cell_own_cash_drop: float = 0.0
    max_stratum_mean_own_cash_drop: float = 0.0
    min_mean_own_cash_delta: float = 0.0
    min_mean_margin_delta: float = 0.0
    min_positive_cells: int = 1

    def normalized(self) -> "PromotionPolicy":
        values = {
            "max_cell_own_cash_drop": _finite(self.max_cell_own_cash_drop, "max_cell_own_cash_drop"),
            "max_stratum_mean_own_cash_drop": _finite(
                self.max_stratum_mean_own_cash_drop, "max_stratum_mean_own_cash_drop"
            ),
            "min_mean_own_cash_delta": _finite(self.min_mean_own_cash_delta, "min_mean_own_cash_delta"),
            "min_mean_margin_delta": _finite(self.min_mean_margin_delta, "min_mean_margin_delta"),
            "min_positive_cells": self.min_positive_cells,
        }
        if values["max_cell_own_cash_drop"] < 0 or values["max_stratum_mean_own_cash_drop"] < 0:
            raise PromotionData("maximum tolerated drops must be nonnegative")
        if isinstance(self.min_positive_cells, bool) or not isinstance(self.min_positive_cells, int) or self.min_positive_cells < 1:
            raise PromotionData("min_positive_cells must be a positive int")
        return PromotionPolicy(**values)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> "PromotionPolicy":
        if raw is None:
            return cls().normalized()
        allowed = set(cls.__dataclass_fields__) | {"schema"}
        if set(raw) - allowed:
            raise PromotionData(f"unknown promotion policy keys: {sorted(set(raw) - allowed)}")
        if raw.get("schema") not in (None, POLICY_SCHEMA):
            raise PromotionData(f"unsupported promotion policy schema: {raw.get('schema')!r}")
        return cls(**{key: raw[key] for key in cls.__dataclass_fields__ if key in raw}).normalized()

    def to_json(self) -> dict[str, Any]:
        return {"schema": POLICY_SCHEMA, **asdict(self.normalized())}


def expected_keys_from_plan(plan: Mapping[str, Any]) -> set[CellKey]:
    """Expand the exact opponent x seed x seat grid declared by a league plan."""
    opponents, seeds = plan.get("opponents"), plan.get("seeds")
    if not isinstance(opponents, Sequence) or isinstance(opponents, (str, bytes)):
        raise PromotionData("plan opponents must be a sequence")
    if not isinstance(seeds, Sequence) or isinstance(seeds, (str, bytes)):
        raise PromotionData("plan seeds must be a sequence")
    opponents = [_name(value, "plan opponent") for value in opponents]
    if len(opponents) != len(set(opponents)):
        raise PromotionData("plan opponents contain duplicates")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in seeds):
        raise PromotionData("plan seeds must be ints")
    seeds = list(seeds)
    if len(seeds) != len(set(seeds)):
        raise PromotionData("plan seeds contain duplicates")
    expected = {(opponent, seed, seat) for opponent in opponents for seed in seeds for seat in (0, 1)}
    declared = plan.get("cells_per_contestant")
    if declared is not None and (isinstance(declared, bool) or not isinstance(declared, int)):
        raise PromotionData("plan cells_per_contestant must be an int")
    if declared is not None and declared != len(expected):
        raise PromotionData("plan cells_per_contestant disagrees with opponents x seeds x seats")
    if not expected:
        raise PromotionData("plan expands to zero cells")
    return expected


def _cell_key(row: Mapping[str, Any], index: int) -> CellKey:
    opponent = _name(row.get("opponent"), f"row {index} opponent")
    seed, seat = row.get("seed"), row.get("candidate_seat")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise PromotionData(f"row {index} seed must be an int")
    if seat not in (0, 1):
        raise PromotionData(f"row {index} candidate_seat must be 0 or 1")
    return opponent, seed, seat


def index_contestant(rows: Sequence[Mapping[str, Any]], contestant: str) -> dict[CellKey, dict[str, float]]:
    """Validate and index one contestant by exact cell."""
    contestant = _name(contestant, "contestant")
    out: dict[CellKey, dict[str, float]] = {}
    for index, row in enumerate(rows):
        if row.get("contestant") != contestant:
            continue
        if row.get("status") != "complete" or row.get("failure") not in (None, ""):
            raise PromotionData(f"{contestant} row {index} is failed or incomplete")
        key = _cell_key(row, index)
        if key in out:
            raise PromotionData(f"{contestant} has duplicate cell {key!r}")
        out[key] = {
            "own_cash": _finite(row.get("own_cash"), f"{contestant} {key} own_cash"),
            "margin": _finite(row.get("margin"), f"{contestant} {key} margin"),
        }
    if not out:
        raise PromotionData(f"no completed evidence for contestant {contestant!r}")
    return out


def coverage_report(
    reference: Mapping[CellKey, Any], challenger: Mapping[CellKey, Any], expected: set[CellKey] | None
) -> dict[str, Any]:
    rkeys, ckeys = set(reference), set(challenger)
    target = set(expected) if expected is not None else rkeys | ckeys
    fields = {
        "missing_reference": target - rkeys,
        "missing_challenger": target - ckeys,
        "unexpected_reference": rkeys - target,
        "unexpected_challenger": ckeys - target,
    }
    return {
        "expected_cells": len(target), "reference_cells": len(rkeys), "challenger_cells": len(ckeys),
        "paired_cells": len(rkeys & ckeys & target),
        "complete": rkeys == ckeys == target and not any(fields.values()),
        **{name: [_key_json(key) for key in sorted(keys)] for name, keys in fields.items()},
    }
