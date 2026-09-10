# SPDX-License-Identifier: Apache-2.0
"""Opponent-seat own-cash regression alarms for the TITAN v3 adversarial league.

Generalizes the one-off #11907 admission gate ("reject opponent-seat
own-cash regressions") into an automatic weekly check.  The inherited gate
checked global, per-opponent, and per-seat own-cash means but not the joint
(opponent, candidate_seat) strata, so it accepted a candidate that lost
own-cash on every seed in one joint stratum while every marginal stayed
nonnegative:

    seat 0   seat 1
    arlene              -10      +30
    apex                +30      +10

This module derives the exact joint strata for every contestant, rejects
missing / nonfinite / negative own-cash values, and flags regressions
against the prior week's ledger baseline.  It raises no process exit on
alarm: the runner records alarms in the ledger and in ALARMS.md.
"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any


class AlarmData(ValueError):
    """Raised when the alarm input itself is malformed."""


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AlarmData(f"{name} must be a number, got {type(value).__name__}")
    result = float(value)
    if not math.isfinite(result):
        raise AlarmData(f"{name} must be finite")
    return result


def joint_strata(cells: Sequence[Mapping[str, Any]]) -> dict[tuple[str, int], list[float]]:
    """Group own-cash values by exact joint (opponent, candidate_seat) stratum.

    Each cell must carry ``opponent`` (nonempty str), ``candidate_seat``
    (0 or 1), and ``own_cash`` (finite number).  Malformed cells raise
    AlarmData: the alarm fails closed rather than silently dropping a
    stratum.
    """
    strata: dict[tuple[str, int], list[float]] = defaultdict(list)
    for index, cell in enumerate(cells):
        opponent = cell.get("opponent")
        seat = cell.get("candidate_seat")
        if not isinstance(opponent, str) or not opponent:
            raise AlarmData(f"cell {index}: opponent must be a nonempty string")
        if seat not in (0, 1):
            raise AlarmData(f"cell {index}: candidate_seat must be 0 or 1")
        own_cash = _finite_number(cell.get("own_cash"), f"cell {index} own_cash")
        strata[(opponent, seat)].append(own_cash)
    return dict(strata)


def check_own_cash_regressions(
    cells: Sequence[Mapping[str, Any]],
    baseline: Mapping[tuple[str, int], float] | None = None,
    floor: float = 0.0,
    drop_tolerance: float = 10000.0,
    min_cells_per_stratum: int = 1,
) -> list[dict[str, Any]]:
    """Evaluate one contestant's completed cells for own-cash alarms.

    Returns a list of alarm dicts; empty means clean.  Two alarm kinds:

    - ``negative_own_cash``: the joint-stratum mean own-cash is below
      ``floor`` (default 0.0).  This is the #11907 witness: a stratum can
      be negative on every seed while global, per-opponent, and per-seat
      marginals all stay nonnegative.
    - ``own_cash_regression``: the stratum mean dropped more than
      ``drop_tolerance`` below the prior-week baseline mean for the same
      joint stratum.

    ``baseline`` maps (opponent, seat) -> prior mean own-cash.  When it is
    None (first league week) only the floor check runs.
    """
    floor = _finite_number(floor, "floor")
    drop_tolerance = _finite_number(drop_tolerance, "drop_tolerance")
    if drop_tolerance < 0:
        raise AlarmData("drop_tolerance must be nonnegative")
    if not isinstance(min_cells_per_stratum, int) or min_cells_per_stratum < 1:
        raise AlarmData("min_cells_per_stratum must be a positive int")

    normalized_baseline: dict[tuple[str, int], float] = {}
    if baseline:
        for key, value in baseline.items():
            opponent, seat = key
            if not isinstance(opponent, str) or not opponent or seat not in (0, 1):
                raise AlarmData(f"baseline key {key!r} must be (opponent, seat)")
            normalized_baseline[(opponent, seat)] = _finite_number(value, f"baseline{key}")

    strata = joint_strata(cells)
    alarms: list[dict[str, Any]] = []
    for (opponent, seat), values in sorted(strata.items()):
        if len(values) < min_cells_per_stratum:
            alarms.append({
                "kind": "incomplete_stratum",
                "opponent": opponent,
                "candidate_seat": seat,
                "cells": len(values),
                "required": min_cells_per_stratum,
            })
            continue
        mean = sum(values) / len(values)
        if mean < floor:
            alarms.append({
                "kind": "negative_own_cash",
                "opponent": opponent,
                "candidate_seat": seat,
                "mean_own_cash": mean,
                "floor": floor,
                "cells": len(values),
            })
        prior = normalized_baseline.get((opponent, seat))
        if prior is not None and mean < prior - drop_tolerance:
            alarms.append({
                "kind": "own_cash_regression",
                "opponent": opponent,
                "candidate_seat": seat,
                "mean_own_cash": mean,
                "baseline_mean_own_cash": prior,
                "drop": prior - mean,
                "drop_tolerance": drop_tolerance,
                "cells": len(values),
            })
    return alarms


def alarms_to_markdown(contestant: str, alarms: Sequence[Mapping[str, Any]]) -> str:
    """Render alarms as a Markdown fragment for ALARMS.md."""
    lines = [f"## {contestant}", ""]
    if not alarms:
        lines.append("No own-cash alarms.")
        return "\n".join(lines) + "\n"
    for alarm in alarms:
        kind = alarm["kind"]
        where = f"{alarm['opponent']} x seat {alarm['candidate_seat']}"
        if kind == "negative_own_cash":
            lines.append(
                f"- NEGATIVE_OWN_CASH {where}: mean {alarm['mean_own_cash']:.3f} "
                f"< floor {alarm['floor']:.3f} over {alarm['cells']} cells")
        elif kind == "own_cash_regression":
            lines.append(
                f"- OWN_CASH_REGRESSION {where}: mean {alarm['mean_own_cash']:.3f} "
                f"vs baseline {alarm['baseline_mean_own_cash']:.3f} "
                f"(drop {alarm['drop']:.3f} > tolerance {alarm['drop_tolerance']:.3f})")
        elif kind == "incomplete_stratum":
            lines.append(
                f"- INCOMPLETE_STRATUM {where}: {alarm['cells']} cells, "
                f"required {alarm['required']}")
        else:
            lines.append(f"- {kind} {where}")
    return "\n".join(lines) + "\n"
