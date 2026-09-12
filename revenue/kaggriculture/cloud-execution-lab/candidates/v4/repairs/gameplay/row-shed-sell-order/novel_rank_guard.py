# SPDX-License-Identifier: Apache-2.0
"""Fail-closed admission for row-shed SELL ordering that is novel vs pressure rank.

This helper does not construct either ranking. It compares two already-produced
selected-action candidates against one shared parent action and admits the
row-shed candidate only when both candidates are exact, auditable permutations
of the same leading contiguous SELL block and their resulting ranks differ.

Missing or ambiguous pressure evidence returns parent identity. The helper is
pure: it never mutates any input action.
"""
from __future__ import annotations

from copy import deepcopy


class RankEvidenceError(ValueError):
    """The supplied ranking candidate cannot safely prove a comparable rank."""


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
        if not isinstance(row, list) or not row or row[0] != "SELL":
            break
        if len(row) < 3:
            raise RankEvidenceError("leading SELL row is missing item or quantity")
        lead += 1
    return rows, lead


def _candidate_rank(parent, candidate, lead):
    if not isinstance(candidate, dict):
        raise RankEvidenceError("candidate must be a dict")
    if set(candidate) != set(parent):
        raise RankEvidenceError("candidate top-level keys differ from parent")
    for key in parent:
        if key != "market" and candidate[key] != parent[key]:
            raise RankEvidenceError("candidate changed non-market action surface")

    parent_rows = parent["market"]
    rows = candidate.get("market")
    if not isinstance(rows, list) or len(rows) != len(parent_rows):
        raise RankEvidenceError("candidate market cardinality differs from parent")
    if _truthy_malformed_market_row(rows):
        raise RankEvidenceError("truthy candidate market row must be a list")
    if rows[lead:] != parent_rows[lead:]:
        raise RankEvidenceError("candidate changed a market suffix or barrier")

    block = rows[:lead]
    if any(not row or not isinstance(row, list) or row[0] != "SELL" or len(row) < 3
           for row in block):
        raise RankEvidenceError("candidate leading block is not all SELL rows")
    if not _same_rows_with_duplicates(block, parent_rows[:lead]):
        raise RankEvidenceError("candidate did not preserve the leading SELL multiset")
    return block


class NovelRankGuard:
    """Keep row-shed ordering only when its rank differs from pressure ordering."""

    def __init__(self):
        self.diagnostics = {}

    def choose(self, parent_action, row_shed_action, pressure_action):
        self.diagnostics = {
            "status": "identity",
            "reason": None,
            "leading_sell_count": 0,
            "row_shed_rank": [],
            "pressure_rank": [],
        }
        try:
            parent_rows, lead = _parent_shape(parent_action)
            parent = deepcopy(parent_action)
            parent["market"] = deepcopy(parent_rows)
            self.diagnostics["leading_sell_count"] = lead
            if lead < 2:
                self.diagnostics["reason"] = "leading_sell_block_lt_2"
                return deepcopy(parent_action)

            row_rank = _candidate_rank(parent, row_shed_action, lead)
            if row_shed_action == parent_action:
                self.diagnostics.update(
                    reason="row_shed_identity",
                    row_shed_rank=deepcopy(row_rank),
                )
                return deepcopy(parent_action)

            if pressure_action is None:
                raise RankEvidenceError("pressure rank evidence is missing")
            pressure_rank = _candidate_rank(parent, pressure_action, lead)
            self.diagnostics.update(
                row_shed_rank=deepcopy(row_rank),
                pressure_rank=deepcopy(pressure_rank),
            )

            if row_rank == pressure_rank:
                self.diagnostics["reason"] = "redundant_with_pressure_rank"
                return deepcopy(parent_action)

            self.diagnostics.update(
                status="applied",
                reason="novel_vs_pressure_rank",
            )
            return deepcopy(row_shed_action)
        except (RankEvidenceError, KeyError, TypeError, IndexError) as error:
            self.diagnostics["reason"] = str(error)
            return deepcopy(parent_action)


def choose(parent_action, row_shed_action, pressure_action):
    """Stateless convenience wrapper."""
    return NovelRankGuard().choose(parent_action, row_shed_action, pressure_action)
