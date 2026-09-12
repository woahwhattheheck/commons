# SPDX-License-Identifier: Apache-2.0
"""Fail-closed admission for row-shed ordering that survives final pressure.

The canonical TITAN runtime applies market pressure after selected-action SELL
composition.  Comparing a raw row-shed rank with ``pressure(parent)`` is not
enough: a different raw rank can be sorted back to the same final action by the
later pressure pass.

This helper therefore consumes two caller-produced downstream pressure
postimages: one from the incumbent parent path and one from the row-shed path.
It admits the raw row-shed candidate only when both postimages are conservative
row permutations and the *final* postimages differ.  Missing or ambiguous
downstream evidence returns exact parent identity.  The helper never mutates
inputs and does not implement pressure policy itself.
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
    sale-only prefix slots, so suffix-index equality is deliberately *not*
    required here.  It may not change non-market surfaces, row values,
    quantities, duplicate multiplicity, or market cardinality.
    """
    if not isinstance(after, dict):
        raise RankEvidenceError(f"{label} pressure postimage must be a dict")
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


class NovelRankGuard:
    """Keep row-shed only when its effect survives the downstream pressure pass."""

    def __init__(self):
        self.diagnostics = {}

    def choose(
        self,
        parent_action,
        row_shed_action,
        pressure_parent_action,
        pressure_row_shed_action=None,
    ):
        self.diagnostics = {
            "status": "identity",
            "reason": None,
            "leading_sell_count": 0,
            "row_shed_rank": [],
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

            if pressure_parent_action is None or pressure_row_shed_action is None:
                raise RankEvidenceError("both downstream pressure postimages are required")
            _pressure_postimage(parent, pressure_parent_action, "parent")
            _pressure_postimage(row_shed_action, pressure_row_shed_action, "row-shed")

            final_equal = pressure_parent_action == pressure_row_shed_action
            self.diagnostics["final_pressure_equal"] = final_equal
            if final_equal:
                self.diagnostics["reason"] = "redundant_after_pressure"
                return deepcopy(parent_action)

            self.diagnostics.update(
                status="applied",
                reason="survives_pressure_postimage",
            )
            return deepcopy(row_shed_action)
        except (RankEvidenceError, KeyError, TypeError, IndexError) as error:
            self.diagnostics["reason"] = str(error)
            return deepcopy(parent_action)


def choose(
    parent_action,
    row_shed_action,
    pressure_parent_action,
    pressure_row_shed_action=None,
):
    """Stateless convenience wrapper; incomplete downstream evidence fails closed."""
    return NovelRankGuard().choose(
        parent_action,
        row_shed_action,
        pressure_parent_action,
        pressure_row_shed_action,
    )
