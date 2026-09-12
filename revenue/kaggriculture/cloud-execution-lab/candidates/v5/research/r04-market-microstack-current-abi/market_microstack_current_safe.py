# SPDX-License-Identifier: Apache-2.0
"""Fail-closed public surface for the submitted V3.1 R04 market microstack.

The historical V224 helper compacts zero/dead rows. At the current selected-action
boundary that is only safe for a zero quantity created *inside this component* by
settling an authenticated prior reservation. A dead row supplied by the current
producer is a barrier/evidence ambiguity and must fail closed instead of being
silently deleted.

The current runtime may retry the same public step. The historical whole-route
agent did not have to expose its intermediate H8/H4 ledger across that boundary,
so this public adapter owns a small transaction seam:

* a true rewind is ``step < previous_step``;
* an exact same-step sale-window replay returns the exact cached result/report
  without touching the live shared H8/H4 debt ledger;
* changed same-step evidence recomputes from saved *pre-step* player/rival state;
* H4 is bound to the exact sale-window transaction revision and has its own
  idempotent retry checkpoint over the same shared debt ledger.

That closes the standalone-H4 double-realization class: due debt is always settled
by the H8/E184 stage before H4 may create fresh STRAWBERRY reservations.
"""
from __future__ import annotations

from copy import deepcopy

from market_microstack_current import (
    ADVANCE_START,
    ANIMALS,
    LAST_STEP,
    MAX_ORDERS,
    SALE_HORIZON,
    R04MarketMicrostackCurrentABI as _Base,
    _PlayerState,
    _RivalGateState,
    _strict_bool,
)

H4_DONOR_COMMIT = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
H4_DONOR_PATH = (
    "revenue/kaggriculture/cloud-execution-lab/"
    "candidates/v3/overlay/r04_h4_strawberry.py"
)
H4_DONOR_BLOB = "d6e3ffb76856ff171dab2a45b4d3c1788f2b2cb8"
STRAWBERRY = "STRAWBERRY"


class R04MarketMicrostackCurrentABI(_Base):
    """Canonical public class; use this instead of the base implementation."""

    def __init__(self, *args, strawberry_topup: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.strawberry_topup = _strict_bool("strawberry_topup", strawberry_topup)
        self._sale_transactions = {}
        self._sale_revisions = {}
        self._h4_transactions = {}

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

    @staticmethod
    def _fallback_debts(players, observation):
        if not isinstance(observation, dict):
            return {}
        player = observation.get("player")
        if type(player) is not int or player not in (0, 1):
            return {}
        state = players.get(player)
        return deepcopy({} if state is None else state.sale_window_debts)

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
        try:
            fallback = deepcopy(selected_action)
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
            try:
                fallback = deepcopy(selected_action)
            except Exception:
                fallback = selected_action
            return fallback, {
                "stage": "sale_window",
                "changed": False,
                "reason": f"fail_closed:retry_snapshot:{error}",
                "on_tape": True,
                "l3_suppressed": False,
                "debts_after": self._fallback_debts(self._players, observation),
            }

        transaction = self._sale_transactions.get(player)

        if transaction is not None and step == transaction["step"]:
            if self._same_snapshot(snapshot, transaction["input"]):
                # Do not restore state here. H4 may have updated the shared debt
                # ledger after the first sale-window stage call.
                return (
                    deepcopy(transaction["result"]),
                    deepcopy(transaction["report"]),
                )

            # Changed evidence on the same callback is a replacement attempt.
            # Recompute from the authority that existed before this step, never
            # from debt/rival state partially produced by the prior attempt.
            self._players[player] = deepcopy(transaction["pre_player"])
            self._rivals[player] = deepcopy(transaction["pre_rival"])
            pre_player = deepcopy(transaction["pre_player"])
            pre_rival = deepcopy(transaction["pre_rival"])
        else:
            if transaction is not None and step < transaction["step"]:
                # A true episode rewind is strictly earlier, never same-step.
                self._sale_transactions.pop(player, None)
                self._h4_transactions.pop(player, None)
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

        revision = self._sale_revisions.get(player, 0) + 1
        self._sale_revisions[player] = revision
        self._sale_transactions[player] = {
            "step": step,
            "revision": revision,
            "input": snapshot,
            "pre_player": pre_player,
            "pre_rival": pre_rival,
            "result": deepcopy(result),
            "report": deepcopy(report),
        }
        return result, report

    def strawberry_topup_transform(
        self,
        observation,
        configuration,
        selected_action,
        *,
        post_unit_shed,
        future_actions,
        queued_commands,
    ):
        """Apply submitted H4 after H8/L3 using the exact shared reservation ledger."""
        try:
            fallback = deepcopy(selected_action)
        except Exception:
            fallback = selected_action
        report = {
            "stage": "h4_strawberry_topup",
            "changed": False,
            "reason": "disabled",
            "reservations": (),
            "donor_commit": H4_DONOR_COMMIT,
            "donor_blob": H4_DONOR_BLOB,
        }
        if not self.strawberry_topup:
            return fallback, report
        if not self.sale_window:
            report["reason"] = "requires_sale_window"
            return fallback, report

        try:
            self._standard_configuration(configuration)
            step, player, farm = self._identity(observation)
            workers = 1 + len(farm.get("hands", []))
            self._validate_action(selected_action, workers=workers)
            shed = self._validate_post_unit_shed(post_unit_shed)
            prices = self._market_prices(observation)
            inventories = self._inventories(observation, workers)
            queued = self._queued_commands(queued_commands)

            sale_tx = self._sale_transactions.get(player)
            if sale_tx is None or sale_tx["step"] != step:
                report["reason"] = "requires_same_step_sale_window_stage"
                return fallback, report
            if not self._same_snapshot(selected_action, sale_tx["result"]):
                report["reason"] = "sale_window_postimage_mismatch"
                return fallback, report
            # H8 and H4 must consume one coherent future-route/queue snapshot.
            if not self._same_snapshot(future_actions, sale_tx["input"]["future_actions"]):
                report["reason"] = "future_snapshot_mismatch"
                return fallback, report
            if not self._same_snapshot(queued_commands, sale_tx["input"]["queued_commands"]):
                report["reason"] = "queue_snapshot_mismatch"
                return fallback, report

            h4_input = self._retry_snapshot(
                observation,
                configuration,
                selected_action,
                post_unit_shed,
                future_actions,
                queued_commands,
            )
            key = (step, sale_tx["revision"])
            h4_tx = self._h4_transactions.get(player)
            if h4_tx is not None and h4_tx["key"] == key:
                if self._same_snapshot(h4_input, h4_tx["input"]):
                    return deepcopy(h4_tx["result"]), deepcopy(h4_tx["report"])
                # Same sale-window authority, changed H4 evidence: recompute from
                # the shared ledger as it existed immediately before H4.
                self._players[player].sale_window_debts = deepcopy(h4_tx["pre_debts"])
                pre_debts = deepcopy(h4_tx["pre_debts"])
            else:
                pre_debts = deepcopy(self._players[player].sale_window_debts)

            if step < ADVANCE_START or step >= LAST_STEP:
                report["reason"] = "outside_window"
                result = fallback
            else:
                market = selected_action["market"]
                strawberry_rows = [
                    index
                    for index, row in enumerate(market)
                    if len(row) >= 3 and row[0] == "SELL" and row[1] == STRAWBERRY
                ]
                if len(strawberry_rows) != 1:
                    report["reason"] = "requires_one_current_sell"
                    result = fallback
                elif any(
                    len(row) >= 2
                    and row[0] == "BUY_PRODUCT"
                    and row[1] == STRAWBERRY
                    for row in market
                ):
                    report["reason"] = "current_buy_product"
                    result = fallback
                elif prices[STRAWBERRY] < 2:
                    report["reason"] = "price_floor"
                    result = fallback
                elif any(
                    len(command) > 1
                    and command[0] == "PICKUP"
                    and command[1] == STRAWBERRY
                    for command in queued
                ) or any(
                    len(command) > 1
                    and command[0] == "PICKUP"
                    and command[1] == STRAWBERRY
                    for command in self._current_commands(selected_action)
                ):
                    report["reason"] = "pickup_blocker"
                    result = fallback
                elif self._animal_place_uncertain(selected_action, inventories):
                    report["reason"] = "animal_place_uncertain"
                    result = fallback
                else:
                    row_index = strawberry_rows[0]
                    current_quantity = market[row_index][2]
                    available = max(0, shed[STRAWBERRY] - current_quantity)
                    end = min(
                        LAST_STEP,
                        step + (SALE_HORIZON if step >= 144 else 1),
                        (step // 72 + 1) * 72 - 1,
                    )
                    if not available or end <= step:
                        report["reason"] = "no_projected_surplus_or_window"
                        result = fallback
                    else:
                        future = self._future_range(future_actions, step + 1, end)
                        debts = deepcopy(self._players[player].sale_window_debts)
                        reservations = []
                        remaining_stock = available
                        blocked = False
                        for due_step in range(step + 1, end + 1):
                            authored = future[due_step]
                            work = self._current_commands(authored)
                            if any(
                                len(command) > 1
                                and command[0] == "PICKUP"
                                and command[1] == STRAWBERRY
                                for command in work
                            ):
                                blocked = True
                                break
                            if any(
                                len(row) > 1
                                and row[0] == "BUY_PRODUCT"
                                and row[1] == STRAWBERRY
                                for row in authored["market"]
                            ):
                                blocked = True
                                break
                            planned = sum(
                                max(0, row[2])
                                for row in authored["market"]
                                if (
                                    len(row) >= 3
                                    and row[0] == "SELL"
                                    and row[1] == STRAWBERRY
                                )
                            )
                            already = debts.get(due_step, {}).get(STRAWBERRY, 0)
                            amount = min(remaining_stock, max(0, planned - already))
                            if amount:
                                reservations.append((due_step, amount))
                                remaining_stock -= amount
                            if not remaining_stock:
                                break
                        added = sum(amount for _, amount in reservations)
                        if not added:
                            report["reason"] = (
                                "future_blocker" if blocked else "no_backed_future_sale"
                            )
                            result = fallback
                        else:
                            result = deepcopy(selected_action)
                            result["market"][row_index][2] = current_quantity + added
                            for due_step, amount in reservations:
                                due = debts.setdefault(due_step, {})
                                due[STRAWBERRY] = due.get(STRAWBERRY, 0) + amount
                            self._players[player].sale_window_debts = debts
                            report.update(
                                changed=True,
                                reason="strawberry_topup",
                                row_index=row_index,
                                original_quantity=current_quantity,
                                added_quantity=added,
                                final_quantity=current_quantity + added,
                                reservations=tuple(reservations),
                                window_end=end,
                            )

            self._h4_transactions[player] = {
                "key": key,
                "input": h4_input,
                "pre_debts": pre_debts,
                "result": deepcopy(result),
                "report": deepcopy(report),
            }
            return result, report
        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            AttributeError,
            OverflowError,
        ) as error:
            report["reason"] = f"fail_closed:{error}"
            return fallback, report
