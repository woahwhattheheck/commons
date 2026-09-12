# SPDX-License-Identifier: Apache-2.0
"""Fail-closed admission for row-shed ordering that survives final pressure.

The canonical TITAN stack inserts row-shed upstream of existing selected-action
SELL economics and applies market pressure later.  Comparing a raw row-shed rank
with ``pressure(parent)`` is therefore not enough: downstream SELL logic and the
later pressure pass can erase a raw ordering difference entirely.

This helper consumes caller-produced evidence from the *actual pressure seam*:
for both the incumbent path and the row-shed path, the action entering canonical
pressure and the corresponding pressure postimage.  It admits the raw row-shed
candidate only when the two final pressure postimages differ.  Missing,
malformed, or internally inconsistent downstream evidence returns exact parent
identity.  The helper never mutates inputs and does not implement pressure or
SELL policy itself.
"""
from __future__ import annotations

from copy import deepcopy


class RankEvidenceError(ValueError):
    """The supplied row/pressure evidence cannot safely prove final novelty."""


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
        raise RankEvidenceError("action must be a dict")
    rows = action.get("market")
    if not isinstance(rows, list):
        raise RankEvidenceError("action market must be a list")
    if _truthy_malformed_market_row(rows):
        raise RankEvidenceError("truthy market row must be a list")

    lead = 0
    while lead < len(rows):
        row = rows[lead]
        if not row:
            break
        if not isinstance(row, list) or row[0] != "SELL":
            break
        if len(row) < 3:
            raise RankEvidenceError("leading SELL row is missing item or quantity")
        lead += 1
    return rows, lead


def _row_shed_rank(parent, candidate, lead):
    """Authenticate the narrow raw row-shed mutation against its parent."""
    if not isinstance(candidate, dict):
        raise RankEvidenceError("row-shed candidate must be a dict")
    if set(candidate) != set(parent):
        raise RankEvidenceError("row-shed top-level keys differ from parent")
    for key in parent:
        if key != "market" and candidate[key] != parent[key]:
            raise RankEvidenceError("row-shed changed non-market action surface")

    parent_rows = parent["market"]
    rows = candidate.get("market")
    if not isinstance(rows, list) or len(rows) != len(parent_rows):
        raise RankEvidenceError("row-shed market cardinality differs from parent")
    if _truthy_malformed_market_row(rows):
        raise RankEvidenceError("truthy row-shed market row must be a list")
    if rows[lead:] != parent_rows[lead:]:
        raise RankEvidenceError("row-shed changed a market suffix or barrier")

    block = rows[:lead]
    if any(not row or not isinstance(row, list) or row[0] != "SELL" or len(row) < 3
           for row in block):
        raise RankEvidenceError("row-shed leading block is not all SELL rows")
    if not _same_rows_with_duplicates(block, parent_rows[:lead]):
        raise RankEvidenceError("row-shed did not preserve the leading SELL multiset")
    return block


def _pressure_postimage(before, after, label):
    """Authenticate a supplied pressure result as a conservative row permutation.

    Canonical pressure may reorder supported SELL blocks and compact known empty
    sale-only prefix slots.  It may not change non-market surfaces, row values,
    quantities, duplicate multiplicity, or market cardinality.
    """
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise RankEvidenceError(f"{label} pressure input/postimage must be dicts")
    if set(after) != set(before):
        raise RankEvidenceError(f"{label} pressure postimage top-level keys differ")
    for key in before:
        if key != "market" and after[key] != before[key]:
            raise RankEvidenceError(f"{label} pressure postimage changed non-market surface")

    before_rows = before.get("market")
    rows = after.get("market")
    if not isinstance(before_rows, list) or not isinstance(rows, list):
        raise RankEvidenceError(f"{label} pressure market must be a list")
    if len(rows) != len(before_rows):
        raise RankEvidenceError(f"{label} pressure market cardinality differs")
    if _truthy_malformed_market_row(rows):
        raise RankEvidenceError(f"{label} pressure postimage has malformed market row")
    if not _same_rows_with_duplicates(rows, before_rows):
        raise RankEvidenceError(f"{label} pressure postimage changed market row multiset")
    return rows


def _same_non_market_surface(left, right):
    if not isinstance(left, dict) or not isinstance(right, dict) or set(left) != set(right):
        return False
    return all(left[key] == right[key] for key in left if key != "market")


class NovelRankGuard:
    """Keep row-shed only when its effect survives the real pressure seam."""

    def __init__(self):
        self.diagnostics = {}

    def choose(
        self,
        parent_action,
        row_shed_action,
        pressure_parent_input=None,
        pressure_parent_output=None,
        pressure_row_shed_input=None,
        pressure_row_shed_output=None,
    ):
        self.diagnostics = {
            "status": "identity",
            "reason": None,
            "leading_sell_count": 0,
            "row_shed_rank": [],
            "pressure_input_equal": None,
            "final_pressure_equal": None,
        }
        try:
            parent_rows, lead = _parent_shape(parent_action)
            parent = deepcopy(parent_action)
            parent["market"] = deepcopy(parent_rows)
            self.diagnostics["leading_sell_count"] = lead
            if lead < 2:
                self.diagnostics["reason"] = "leading_sell_block_lt_2"
                return deepcopy(parent_action)

            row_rank = _row_shed_rank(parent, row_shed_action, lead)
            self.diagnostics["row_shed_rank"] = deepcopy(row_rank)
            if row_shed_action == parent_action:
                self.diagnostics["reason"] = "row_shed_identity"
                return deepcopy(parent_action)

            evidence = (
                pressure_parent_input,
                pressure_parent_output,
                pressure_row_shed_input,
                pressure_row_shed_output,
            )
            if any(value is None for value in evidence):
                raise RankEvidenceError("complete downstream pressure input/postimage evidence is required")
            if not _same_non_market_surface(pressure_parent_input, pressure_row_shed_input):
                raise RankEvidenceError("pressure-path inputs disagree on non-market action surface")

            _pressure_postimage(
                pressure_parent_input,
                pressure_parent_output,
                "parent-path",
            )
            _pressure_postimage(
                pressure_row_shed_input,
                pressure_row_shed_output,
                "row-shed-path",
            )

            inputs_equal = pressure_parent_input == pressure_row_shed_input
            final_equal = pressure_parent_output == pressure_row_shed_output
            self.diagnostics["pressure_input_equal"] = inputs_equal
            self.diagnostics["final_pressure_equal"] = final_equal
            if inputs_equal and not final_equal:
                raise RankEvidenceError("identical pressure inputs produced inconsistent postimages")
            if final_equal:
                self.diagnostics["reason"] = "redundant_after_downstream_pressure"
                return deepcopy(parent_action)

            self.diagnostics.update(
                status="applied",
                reason="survives_downstream_pressure",
            )
            return deepcopy(row_shed_action)
        except (RankEvidenceError, KeyError, TypeError, IndexError) as error:
            self.diagnostics["reason"] = str(error)
            return deepcopy(parent_action)


def choose(
    parent_action,
    row_shed_action,
    pressure_parent_input=None,
    pressure_parent_output=None,
    pressure_row_shed_input=None,
    pressure_row_shed_output=None,
):
    """Stateless wrapper; incomplete downstream evidence fails closed."""
    return NovelRankGuard().choose(
        parent_action,
        row_shed_action,
        pressure_parent_input,
        pressure_parent_output,
        pressure_row_shed_input,
        pressure_row_shed_output,
    )
