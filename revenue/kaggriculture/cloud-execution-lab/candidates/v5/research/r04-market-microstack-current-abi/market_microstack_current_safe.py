# SPDX-License-Identifier: Apache-2.0
"""Fail-closed public surface for the recovered R04 market microstack.

The historical V224 helper compacts zero/dead rows. At the current selected-action
boundary that is only safe for a zero quantity created *inside this component* by
settling an authenticated prior reservation. A dead row supplied by the current
producer is a barrier/evidence ambiguity and must fail closed instead of being
silently deleted.

The current runtime may retry the same public step. The historical whole-route
agent did not have to expose its intermediate H8/H4 ledger across that boundary,
so the public adapter also owns a small transaction seam:

* a true rewind is ``step < previous_step``;
* an exact same-step replay returns the exact cached stage result/report without
  touching the live shared H8/H4 debt ledger;
* changed evidence on the same step recomputes from the saved *pre-step* player
  and rival-gate snapshots, never from partially-mutated post-step state.

That makes L3's opening certificate and H8/H4 debt deterministic across retries
while still allowing H4 to update the shared ledger between the two public stages.
"""
from __future__ import annotations

from copy import deepcopy

from market_microstack_current import (
    MAX_ORDERS,
    R04MarketMicrostackCurrentABI as _Base,
    _PlayerState,
    _RivalGateState,
)


class R04MarketMicrostackCurrentABI(_Base):
    """Canonical public class; use this instead of the base implementation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sale_transactions = {}

    @staticmethod
    def _validate_action(action, *, workers=None):
        _Base._validate_action(action, workers=workers)
        market = action.get("market", [])
        if len(market) > MAX_ORDERS:
            raise ValueError("current boundary requires executable market prefix only")
        for row in market:
            if row[0] not in {"HIRE", "BUY_LAND"} and row[2] <= 0:
                raise ValueError("pre-existing nonpositive market row fails closed")

    @staticmethod
    def _sales_first(action):
        """Exact V224 compaction after internal settlement on an admitted input."""
        original = action["market"][:MAX_ORDERS]
        orders = [
            list(row)
            for row in original
            if row
            and (
                row[0] in ("HIRE", "BUY_LAND")
                or (len(row) >= 3 and row[2] > 0)
            )
        ]
        for index in range(len(orders)):
            order = orders[index]
            if order[0] != "SELL":
                continue
            cursor = index
            while cursor > 0:
                previous = orders[cursor - 1]
                if previous[0] == "SELL":
                    break
                if (
                    previous[0] in ("BUY_PRODUCT", "BUY_ANIMAL")
                    and previous[1] == order[1]
                ):
                    break
                orders[cursor - 1], orders[cursor] = (
                    orders[cursor],
                    orders[cursor - 1],
                )
                cursor -= 1
        if orders == original:
            return action, False
        changed = deepcopy(action)
        changed["market"] = orders
        return changed, True

    @staticmethod
    def _retry_snapshot(
        observation,
        configuration,
        selected_action,
        post_unit_shed,
        future_actions,
        queued_commands,
    ):
        """Detached structural evidence used only to classify same-step retries."""
        return {
            "observation": deepcopy(observation),
            "configuration": deepcopy(configuration),
            "selected_action": deepcopy(selected_action),
            "post_unit_shed": deepcopy(post_unit_shed),
            "future_actions": deepcopy(future_actions),
            "queued_commands": deepcopy(queued_commands),
        }

    @staticmethod
    def _same_snapshot(left, right):
        try:
            return left == right
        except Exception:
            return False

    def sale_window_transform(
        self,
        observation,
        configuration,
        selected_action,
        *,
        post_unit_shed,
        future_actions=None,
        queued_commands=None,
    ):
        """Transactional public sale-window stage across current same-step retries."""
        fallback = deepcopy(selected_action)
        try:
            step, player, _ = self._identity(observation)
            snapshot = self._retry_snapshot(
                observation,
                configuration,
                selected_action,
                post_unit_shed,
                future_actions,
                queued_commands,
            )
        except Exception as error:
            return fallback, {
                "stage": "sale_window",
                "changed": False,
                "reason": f"fail_closed:retry_snapshot:{error}",
                "on_tape": True,
                "l3_suppressed": False,
                "debts_after": deepcopy(
                    self._players.get(
                        observation.get("player") if isinstance(observation, dict) else -1,
                        _PlayerState(),
                    ).sale_window_debts
                ),
            }

        transaction = self._sale_transactions.get(player)

        if transaction is not None and step == transaction["step"]:
            if self._same_snapshot(snapshot, transaction["input"]):
                # Crucially do not restore state here. H4 may have updated the
                # shared debt ledger after the first sale-window stage call.
                return (
                    deepcopy(transaction["result"]),
                    deepcopy(transaction["report"]),
                )

            # Changed evidence on the same callback is a replacement attempt.
            # Recompute from the authority that existed before this step, not
            # from debt/rival state partially produced by the prior attempt.
            self._players[player] = deepcopy(transaction["pre_player"])
            self._rivals[player] = deepcopy(transaction["pre_rival"])
            pre_player = deepcopy(transaction["pre_player"])
            pre_rival = deepcopy(transaction["pre_rival"])
        else:
            if transaction is not None and step < transaction["step"]:
                # A true episode rewind is strictly earlier, never same-step.
                self._sale_transactions.pop(player, None)
            pre_player = deepcopy(self._players.get(player, _PlayerState()))
            pre_rival = deepcopy(self._rivals.get(player, _RivalGateState()))

        result, report = super().sale_window_transform(
            observation,
            configuration,
            selected_action,
            post_unit_shed=post_unit_shed,
            future_actions=future_actions,
            queued_commands=queued_commands,
        )

        self._sale_transactions[player] = {
            "step": step,
            "input": snapshot,
            "pre_player": pre_player,
            "pre_rival": pre_rival,
            "result": deepcopy(result),
            "report": deepcopy(report),
        }
        return result, report
