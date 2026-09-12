# SPDX-License-Identifier: Apache-2.0
"""Fail-closed admission for row-shed SELL ordering novel after final pressure.

The legacy ``choose`` method retains the landed rank-evidence API.  The stronger
``choose_after_pressure`` method implements the current V4 theorem: the caller
supplies the exact canonical final pressure transform and quote function, that
same transform is applied independently to the incumbent and STRATUM candidate,
and row-shed is admitted only when the *final returned actions* still differ.

No pressure policy is imported or approximated here.  Inputs are deep-copied
before the supplied transform runs; malformed/mutating evidence fails closed to
the parent action.
"""
from __future__ import annotations

from copy import deepcopy


class RankEvidenceError(ValueError):
    """Supplied ordering/pressure evidence cannot safely prove an admission."""


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


def _validated_pressure_output(source_action, output):
    """Validate canonical pressure as a pure full-market permutation transform.

    LARK may reorder supported SELL blocks and may compact known empty rows inside
    an eligible sale-only executable prefix.  Therefore suffix equality is *not*
    required here; exact full-market row multiplicity/cardinality and every
    non-market action surface are.
    """
    if not isinstance(output, dict):
        raise RankEvidenceError("pressure output must be a dict")
    if set(output) != set(source_action):
        raise RankEvidenceError("pressure output top-level keys differ from input")
    for key in source_action:
        if key != "market" and output[key] != source_action[key]:
            raise RankEvidenceError("pressure changed non-market action surface")

    source_rows = source_action.get("market")
    rows = output.get("market")
    if not isinstance(source_rows, list) or not isinstance(rows, list):
        raise RankEvidenceError("pressure market must be a list")
    if len(rows) != len(source_rows):
        raise RankEvidenceError("pressure changed market cardinality")
    if _truthy_malformed_market_row(rows):
        raise RankEvidenceError("truthy pressure market row must be a list")
    if not _same_rows_with_duplicates(source_rows, rows):
        raise RankEvidenceError("pressure changed market row multiset")
    return deepcopy(output)


class NovelRankGuard:
    """Admit STRATUM only when its ordering remains distinct after pressure."""

    def __init__(self):
        self.diagnostics = {}

    def _begin(self, mode):
        self.diagnostics = {
            "status": "identity",
            "reason": None,
            "mode": mode,
            "leading_sell_count": 0,
            "row_shed_rank": [],
            "pressure_rank": [],
            "parent_pressure_changed": False,
            "row_shed_pressure_changed": False,
        }

    def choose(self, parent_action, row_shed_action, pressure_action):
        """Compatibility API: compare already-produced intermediate ranks."""
        self._begin("intermediate_rank")
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

    def choose_after_pressure(
        self,
        parent_action,
        row_shed_action,
        observation,
        configuration,
        *,
        pressure_transform,
        quote,
    ):
        """Prove STRATUM remains distinct after the exact final pressure transform.

        The callback must be the canonical pressure ``transform`` function with
        signature ``transform(action, observation, configuration, *, quote=...)``.
        It is invoked on isolated deep copies of the same public evidence.

        Return value deliberately remains either the original parent or the
        row-shed candidate.  The canonical runtime keeps sole ownership of the
        actual final pressure invocation later in the pipeline.
        """
        self._begin("final_pressure_output")
        try:
            parent_rows, lead = _parent_shape(parent_action)
            parent = deepcopy(parent_action)
            parent["market"] = deepcopy(parent_rows)
            self.diagnostics["leading_sell_count"] = lead
            if lead < 2:
                self.diagnostics["reason"] = "leading_sell_block_lt_2"
                return deepcopy(parent_action)

            row_rank = _candidate_rank(parent, row_shed_action, lead)
            self.diagnostics["row_shed_rank"] = deepcopy(row_rank)
            if row_shed_action == parent_action:
                self.diagnostics["reason"] = "row_shed_identity"
                return deepcopy(parent_action)

            if not isinstance(observation, dict):
                raise RankEvidenceError("observation must be a dict")
            if configuration is not None and not isinstance(configuration, dict):
                raise RankEvidenceError("configuration must be a dict or None")
            if not callable(pressure_transform):
                raise RankEvidenceError("pressure transform is missing")
            if not callable(quote):
                raise RankEvidenceError("pressure quote is missing")

            cfg = {} if configuration is None else configuration
            parent_for_pressure = deepcopy(parent)
            row_for_pressure = deepcopy(row_shed_action)
            parent_final = pressure_transform(
                parent_for_pressure,
                deepcopy(observation),
                deepcopy(cfg),
                quote=quote,
            )
            row_final = pressure_transform(
                row_for_pressure,
                deepcopy(observation),
                deepcopy(cfg),
                quote=quote,
            )
            parent_final = _validated_pressure_output(parent, parent_final)
            row_final = _validated_pressure_output(row_shed_action, row_final)

            self.diagnostics.update(
                parent_pressure_changed=parent_final != parent,
                row_shed_pressure_changed=row_final != row_shed_action,
                parent_final_market=deepcopy(parent_final["market"]),
                row_shed_final_market=deepcopy(row_final["market"]),
            )
            if parent_final == row_final:
                self.diagnostics["reason"] = "collapsed_after_final_pressure"
                return deepcopy(parent_action)

            self.diagnostics.update(
                status="applied",
                reason="survives_final_pressure",
            )
            return deepcopy(row_shed_action)
        except Exception as error:
            # This is evidence/admission code.  Any callback/source/shape failure
            # is a reason to preserve the incumbent, never to widen activation.
            self.diagnostics["reason"] = str(error) or type(error).__name__
            return deepcopy(parent_action)


def choose(parent_action, row_shed_action, pressure_action):
    """Stateless compatibility wrapper for intermediate-rank admission."""
    return NovelRankGuard().choose(parent_action, row_shed_action, pressure_action)


def choose_after_pressure(
    parent_action,
    row_shed_action,
    observation,
    configuration,
    *,
    pressure_transform,
    quote,
):
    """Stateless wrapper for the stronger final-pressure-output theorem."""
    return NovelRankGuard().choose_after_pressure(
        parent_action,
        row_shed_action,
        observation,
        configuration,
        pressure_transform=pressure_transform,
        quote=quote,
    )
