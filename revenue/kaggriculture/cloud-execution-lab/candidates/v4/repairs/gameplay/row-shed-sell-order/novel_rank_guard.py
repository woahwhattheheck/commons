# SPDX-License-Identifier: Apache-2.0
"""Fail-closed admission for row-shed SELL ordering that survives pressure.

The canonical V4 stack applies its market-pressure transform after the row-shed
seam. A row-shed rank can therefore differ from the incumbent rank yet still be
fully erased downstream. This helper admits a row-shed candidate only when the
*same injected downstream pressure transform*, run with the same public
observation/configuration/quote evidence, produces a different final action
from the incumbent path.

The helper does not implement or approximate pressure policy. Callers retain
custody of the exact canonical transform and its source identity. Missing,
throwing, malformed, or structurally non-preserving downstream evidence fails
closed to parent identity. Inputs are never mutated.
"""
from __future__ import annotations

from copy import deepcopy


class NoveltyEvidenceError(ValueError):
    """Supplied row-shed or downstream-pressure evidence is not auditable."""


def _truthy_malformed_market_row(rows):
    return any(row and not isinstance(row, list) for row in rows)


def _same_rows_with_duplicates(left, right):
    if len(left) != len(right):
        return False
    used = [False] * len(right)
    for row in left:
        for index, other in enumerate(right):
            if not used[index] and type(row) is type(other) and row == other:
                used[index] = True
                break
        else:
            return False
    return True


def _parent_shape(action):
    if not isinstance(action, dict):
        raise NoveltyEvidenceError("action must be a dict")
    rows = action.get("market")
    if not isinstance(rows, list):
        raise NoveltyEvidenceError("action market must be a list")
    if _truthy_malformed_market_row(rows):
        raise NoveltyEvidenceError("truthy market row must be a list")

    lead = 0
    while lead < len(rows):
        row = rows[lead]
        if not row:
            break
        if not isinstance(row, list) or row[0] != "SELL":
            break
        if len(row) < 3:
            raise NoveltyEvidenceError("leading SELL row is missing item or quantity")
        lead += 1
    return rows, lead


def _same_non_market_surface(source, candidate):
    if set(candidate) != set(source):
        return False
    return all(candidate[key] == source[key] for key in source if key != "market")


def _validate_row_shed_candidate(parent, candidate, lead):
    if not isinstance(candidate, dict):
        raise NoveltyEvidenceError("row-shed candidate must be a dict")
    if not _same_non_market_surface(parent, candidate):
        raise NoveltyEvidenceError("row-shed changed a non-market action surface")

    parent_rows = parent["market"]
    rows = candidate.get("market")
    if not isinstance(rows, list) or len(rows) != len(parent_rows):
        raise NoveltyEvidenceError("row-shed market cardinality differs from parent")
    if _truthy_malformed_market_row(rows):
        raise NoveltyEvidenceError("truthy row-shed market row must be a list")
    if rows[lead:] != parent_rows[lead:]:
        raise NoveltyEvidenceError("row-shed changed a market suffix or barrier")

    block = rows[:lead]
    if any(
        not row or not isinstance(row, list) or row[0] != "SELL" or len(row) < 3
        for row in block
    ):
        raise NoveltyEvidenceError("row-shed leading block is not all SELL rows")
    if not _same_rows_with_duplicates(block, parent_rows[:lead]):
        raise NoveltyEvidenceError(
            "row-shed did not preserve the leading SELL multiset"
        )


def _validate_pressure_output(source_action, output):
    if not isinstance(output, dict):
        raise NoveltyEvidenceError("pressure output must be a dict")
    if not _same_non_market_surface(source_action, output):
        raise NoveltyEvidenceError("pressure changed a non-market action surface")

    source_rows = source_action.get("market")
    rows = output.get("market")
    if not isinstance(source_rows, list) or not isinstance(rows, list):
        raise NoveltyEvidenceError("pressure market evidence must be a list")
    if len(rows) != len(source_rows):
        raise NoveltyEvidenceError("pressure changed market cardinality")
    if _truthy_malformed_market_row(rows):
        raise NoveltyEvidenceError("truthy pressure market row must be a list")
    if not _same_rows_with_duplicates(rows, source_rows):
        raise NoveltyEvidenceError(
            "pressure changed market rows, quantities, or duplicate multiplicity"
        )


class PressureNoveltyGuard:
    """Keep row-shed only when its distinction survives downstream pressure."""

    def __init__(self):
        self.diagnostics = {}

    def choose(
        self,
        parent_action,
        row_shed_action,
        pressure_transform,
        observation,
        configuration,
        *,
        quote,
    ):
        self.diagnostics = {
            "status": "identity",
            "reason": None,
            "leading_sell_count": 0,
            "parent_pressure_market": [],
            "row_shed_pressure_market": [],
        }
        try:
            parent_rows, lead = _parent_shape(parent_action)
            parent = deepcopy(parent_action)
            parent["market"] = deepcopy(parent_rows)
            self.diagnostics["leading_sell_count"] = lead

            if lead < 2:
                self.diagnostics["reason"] = "leading_sell_block_lt_2"
                return deepcopy(parent_action)

            _validate_row_shed_candidate(parent, row_shed_action, lead)
            if row_shed_action == parent_action:
                self.diagnostics["reason"] = "row_shed_identity"
                return deepcopy(parent_action)

            if not callable(pressure_transform):
                raise NoveltyEvidenceError("downstream pressure transform is missing")
            if not callable(quote):
                raise NoveltyEvidenceError("pressure quote evidence is missing")

            incumbent_final = pressure_transform(
                deepcopy(parent),
                deepcopy(observation),
                deepcopy(configuration),
                quote=quote,
            )
            row_shed_final = pressure_transform(
                deepcopy(row_shed_action),
                deepcopy(observation),
                deepcopy(configuration),
                quote=quote,
            )

            _validate_pressure_output(parent, incumbent_final)
            _validate_pressure_output(row_shed_action, row_shed_final)
            self.diagnostics.update(
                parent_pressure_market=deepcopy(incumbent_final["market"]),
                row_shed_pressure_market=deepcopy(row_shed_final["market"]),
            )

            if incumbent_final == row_shed_final:
                self.diagnostics["reason"] = "collapsed_by_downstream_pressure"
                return deepcopy(parent_action)

            self.diagnostics.update(
                status="applied",
                reason="survives_downstream_pressure",
            )
            return deepcopy(row_shed_action)
        except Exception as error:  # fail closed at the external-evidence boundary
            self.diagnostics["reason"] = str(error)
            return deepcopy(parent_action)


NovelRankGuard = PressureNoveltyGuard


def choose(
    parent_action,
    row_shed_action,
    pressure_transform,
    observation,
    configuration,
    *,
    quote,
):
    """Stateless convenience wrapper."""
    return PressureNoveltyGuard().choose(
        parent_action,
        row_shed_action,
        pressure_transform,
        observation,
        configuration,
        quote=quote,
    )
