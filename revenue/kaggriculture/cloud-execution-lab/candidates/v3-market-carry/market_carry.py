# SPDX-License-Identifier: Apache-2.0
"""Append-only, observation-grounded town-absorption carry experiment.

The overlay calls no policy and never edits an inherited order.  It may append
one fully funded BUY_PRODUCT row after the canonical queue when deterministic,
already-visible town demand makes the next observable quote profitable under a
bounded public-rival supply stress.  The existing TITAN seller exclusively owns
liquidation on later turns, so its pending ledger and selected action remain
coherent.

This is an experimental score mechanism, not a claim of leaderboard gain.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping, Sequence


ALLOWED_INHERITED_OPS = frozenset(("SELL", "PASS"))
NON_CARRY_ITEM = "FERTILIZER"


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


@dataclass
class CarryLot:
    item: str
    quantity: int
    entry_step: int
    baseline_shed: int
    worst_cost: int
    worst_receipt: int
    worst_profit: int
    absorption: int
    rival_supply_stress: int
    confirmed_quantity: int = 0

    def public(self) -> dict[str, Any]:
        return asdict(self)


class MarketCarry:
    """Stateful, append-only market overlay around one completed parent action."""

    REVISION = "v3-market-carry-r1"

    def __init__(
        self,
        mechanics: Any,
        *,
        post_units: Callable[[Any, dict[str, Any], Any], tuple[Any, Any]] | None = None,
        max_units: int = 12,
        cash_fraction_bps: int = 2_000,
        min_cash_reserve: int = 1_000,
        min_profit: int = 12,
        min_profit_per_unit: int = 1,
        min_roi_bps: int = 75,
        min_day: int = 4,
        terminal_buffer_steps: int = 48,
        unseen_rival_supply: int = 1,
        rival_supply_cap: int = 12,
        rival_buy_stress: int = 2,
        active_max_age: int = 8,
    ) -> None:
        if max_units <= 0:
            raise ValueError("max_units must be positive")
        if not 0 < cash_fraction_bps <= 10_000:
            raise ValueError("cash_fraction_bps must be in 1..10000")
        if min_cash_reserve < 0 or min_profit < 0 or min_roi_bps < 0:
            raise ValueError("reserves and thresholds must be nonnegative")
        if min_day < 0 or terminal_buffer_steps < 1 or active_max_age < 1:
            raise ValueError("invalid horizon")
        self.m = mechanics
        self.post_units = post_units
        self.max_units = int(max_units)
        self.cash_fraction_bps = int(cash_fraction_bps)
        self.min_cash_reserve = int(min_cash_reserve)
        self.min_profit = int(min_profit)
        self.min_profit_per_unit = int(min_profit_per_unit)
        self.min_roi_bps = int(min_roi_bps)
        self.min_day = int(min_day)
        self.terminal_buffer_steps = int(terminal_buffer_steps)
        self.unseen_rival_supply = max(0, int(unseen_rival_supply))
        self.rival_supply_cap = max(0, int(rival_supply_cap))
        self.rival_buy_stress = max(0, int(rival_buy_stress))
        self.active_max_age = int(active_max_age)
        self.active: CarryLot | None = None
        self.last_step: int | None = None
        self.last_report: dict[str, Any] = {}

    def reset(self) -> None:
        self.active = None
        self.last_step = None
        self.last_report = {}

    @staticmethod
    def step(observation: Any, configuration: Any) -> int:
        explicit = _get(observation, "step")
        if explicit is not None:
            return _integer(explicit)
        turns = max(1, _integer(_get(configuration, "turnsPerDay", 24), 24))
        return _integer(_get(observation, "day")) * turns + _integer(
            _get(observation, "hour")
        )

    @staticmethod
    def shops(observation: Any) -> list[str]:
        town = _get(observation, "town", {}) or {}
        raw = _get(town, "unlocked_shops")
        if raw is None:
            raw = _get(town, "shops")
        if raw is None:
            raw = _get(observation, "shops")
        if not isinstance(raw, (list, tuple)):
            return []
        return [str(shop) for shop in raw]

    def absorption(
        self,
        item: str,
        step: int,
        shops: Sequence[str],
        configuration: Any,
    ) -> int:
        """Exact deterministic town consumption after this step's market."""
        shop_interval = max(
            1, _integer(_get(configuration, "townShopSellInterval", 4), 4)
        )
        center_interval = max(
            1, _integer(_get(configuration, "townCenterSellInterval", 24), 24)
        )
        units = 0
        if step % shop_interval == 0:
            for shop in shops:
                products = tuple(_get(self.m, "SHOPS", {}).get(shop, ()))
                if item in products:
                    units += 2 if len(products) == 1 else 1
        if item != NON_CARRY_ITEM and step % center_interval == 0:
            units += 1
        return units

    def visible_rival_supply(self, observation: Any, item: str) -> int:
        """Bound public standing yield that could be sold into the same market."""
        player = _integer(_get(observation, "player"))
        farms = _get(observation, "farms", ())
        try:
            rival = farms[1 - player]
        except (IndexError, KeyError, TypeError):
            return self.rival_supply_cap
        total = 0
        animals = _get(self.m, "ANIMALS", {})
        for row in _get(rival, "tiles", ()) or ():
            for tile in row or ():
                if not isinstance(tile, Mapping):
                    continue
                product = None
                if tile.get("kind") == "PLANT":
                    product = tile.get("crop")
                else:
                    animal = tile.get("animal")
                    if animal in animals:
                        product = animals[animal].get("product")
                if product == item:
                    total += max(0, _integer(tile.get("yield_units")))
                    if total >= self.rival_supply_cap:
                        return self.rival_supply_cap
        return min(total, self.rival_supply_cap)

    def buy_cost(
        self, item: str, inventory: int, quantity: int, params: Any
    ) -> tuple[int, int]:
        cash = 0
        current = int(inventory)
        for _ in range(max(0, int(quantity))):
            cash += int(self.m.market_price(item, current - 1, params))
            current -= 1
        return cash, current

    def sale_receipt(
        self, item: str, inventory: int, quantity: int, params: Any
    ) -> tuple[int, int]:
        cash = 0
        current = int(inventory)
        for _ in range(max(0, int(quantity))):
            quote = int(self.m.market_price(item, current, params))
            if quote <= 1:
                break
            cash += quote
            current += 1
        return cash, current

    def _own(self, observation: Any) -> Any:
        farms = _get(observation, "farms", ())
        return farms[_integer(_get(observation, "player"))]

    def _post_unit_private(
        self, observation: Any, configuration: Any, selected: dict[str, Any]
    ) -> Any | None:
        if self.post_units is None:
            # Without the exact projection, only admit actions whose unit stage
            # cannot mutate shed stock.
            actions = [
                selected.get("farmer", ["PASS"]),
                *(selected.get("hands") or ()),
            ]
            if any(action and action[0] in ("DROP", "PICKUP") for action in actions):
                return None
            return _get(observation, "private", {})
        try:
            _farm, private = self.post_units(observation, selected, configuration)
            return private
        except (ArithmeticError, KeyError, TypeError, ValueError, IndexError):
            return None

    @staticmethod
    def _market_is_append_safe(market: Sequence[Any], max_orders: int) -> bool:
        if len(market) >= max_orders:
            return False
        for order in market:
            if not order:
                continue
            if not isinstance(order, (list, tuple)) or not order:
                return False
            if order[0] not in ALLOWED_INHERITED_OPS:
                return False
        return True

    def _clear_or_block_active(
        self, observation: Any, step: int
    ) -> tuple[bool, dict[str, Any] | None]:
        lot = self.active
        if lot is None:
            return False, None
        private = _get(observation, "private", {}) or {}
        shed = _get(private, "shed", {}) or {}
        current = max(0, _integer(_get(shed, lot.item, 0)))
        age = max(0, step - lot.entry_step)
        gained = max(0, current - lot.baseline_shed)
        if step > lot.entry_step and lot.confirmed_quantity == 0:
            lot.confirmed_quantity = min(lot.quantity, gained)
            if lot.confirmed_quantity == 0:
                report = {
                    "reason": "prior_buy_not_observed",
                    "cleared": lot.public(),
                    "current_shed": current,
                    "age": age,
                }
                self.active = None
                return False, report
        if current <= lot.baseline_shed:
            report = {
                "reason": "seller_liquidated_carry",
                "cleared": lot.public(),
                "current_shed": current,
                "age": age,
            }
            self.active = None
            return False, report
        if age >= self.active_max_age:
            report = {
                "reason": "carry_cooldown_elapsed",
                "cleared": lot.public(),
                "current_shed": current,
                "age": age,
            }
            self.active = None
            return False, report
        return True, {
            "reason": "active_carry",
            "active": lot.public(),
            "current_shed": current,
            "age": age,
        }

    def _plan(
        self,
        observation: Any,
        configuration: Any,
        selected: dict[str, Any],
        step: int,
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str]:
        market = list(selected.get("market") or ())
        max_orders = max(
            1, _integer(_get(configuration, "maxMarketOrdersPerTurn", 10), 10)
        )
        if not self._market_is_append_safe(market, max_orders):
            return None, [], "inherited_market_not_append_safe"

        private = self._post_unit_private(observation, configuration, selected)
        if private is None:
            return None, [], "post_unit_projection_unavailable"
        shed = _get(private, "shed", {}) or {}
        capacity = max(0, _integer(_get(configuration, "shedCapacity", 100), 100))
        shed_total = sum(max(0, _integer(value)) for value in shed.values())
        room = max(0, capacity - shed_total)
        if room <= 0:
            return None, [], "no_post_unit_capacity"

        own = self._own(observation)
        cash = max(0, _integer(_get(own, "money", 0)))
        fraction_budget = cash * self.cash_fraction_bps // 10_000
        spend_budget = min(max(0, cash - self.min_cash_reserve), fraction_budget)
        if spend_budget <= 0:
            return None, [], "cash_reserve"

        market_state = _get(observation, "market", {}) or {}
        inventory = _get(market_state, "inventory", {}) or {}
        params = _get(market_state, "params")
        shops = self.shops(observation)
        products = tuple(_get(self.m, "PRODUCTS", ()))
        same_turn_sells = {
            str(order[1])
            for order in market
            if order and len(order) > 2 and order[0] == "SELL"
        }
        evaluated: list[dict[str, Any]] = []
        candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

        for item in products:
            item = str(item)
            if item == NON_CARRY_ITEM or item in same_turn_sells:
                continue
            if item not in inventory:
                continue
            demand = self.absorption(item, step, shops, configuration)
            if demand <= 0:
                continue
            visible = self.visible_rival_supply(observation, item)
            supply_stress = min(
                self.rival_supply_cap, self.unseen_rival_supply + visible
            )
            if demand <= supply_stress:
                evaluated.append(
                    {
                        "item": item,
                        "reason": "demand_not_above_supply_stress",
                        "absorption": demand,
                        "rival_supply_stress": supply_stress,
                    }
                )
                continue

            inv = _integer(_get(inventory, item))
            best_for_item: dict[str, Any] | None = None
            limit = min(self.max_units, room)
            for quantity in range(1, limit + 1):
                # Scenario A: public/unknown rival supply lands in the same
                # market, then deterministic town demand consumes inventory.
                cost_a, after_buy_a = self.buy_cost(item, inv, quantity, params)
                receipt_a, _ = self.sale_receipt(
                    item, after_buy_a + supply_stress - demand, quantity, params
                )
                # Scenario B: rival BUY_PRODUCT demand precedes our trailing
                # order.  It can raise our purchase quote, but also lowers the
                # inventory from which the canonical seller later exits.
                cost_b, after_buy_b = self.buy_cost(
                    item, inv - self.rival_buy_stress, quantity, params
                )
                receipt_b, _ = self.sale_receipt(
                    item, after_buy_b - demand, quantity, params
                )
                worst_cost = max(cost_a, cost_b)
                worst_receipt = min(receipt_a, receipt_b)
                profit = worst_receipt - worst_cost
                roi_bps = profit * 10_000 // max(1, worst_cost)
                row = {
                    "item": item,
                    "quantity": quantity,
                    "absorption": demand,
                    "visible_rival_supply": visible,
                    "rival_supply_stress": supply_stress,
                    "worst_cost": worst_cost,
                    "worst_receipt": worst_receipt,
                    "worst_profit": profit,
                    "roi_bps": roi_bps,
                }
                if worst_cost > spend_budget:
                    continue
                if (
                    profit < self.min_profit
                    or profit < self.min_profit_per_unit * quantity
                    or roi_bps < self.min_roi_bps
                ):
                    continue
                key = (profit, roi_bps, quantity, -worst_cost, item)
                if best_for_item is None or key > best_for_item["_key"]:
                    best_for_item = {"_key": key, **row}
            if best_for_item is None:
                evaluated.append(
                    {
                        "item": item,
                        "reason": "no_funded_positive_lot",
                        "absorption": demand,
                        "visible_rival_supply": visible,
                        "rival_supply_stress": supply_stress,
                    }
                )
                continue
            public = {k: v for k, v in best_for_item.items() if k != "_key"}
            evaluated.append({"reason": "candidate", **public})
            candidates.append((best_for_item["_key"], public))

        if not candidates:
            return None, evaluated, "no_positive_carry"
        _key, winner = max(candidates, key=lambda entry: entry[0])
        return winner, evaluated, "planned"

    def transform(
        self, observation: Any, configuration: Any, selected: Any
    ) -> tuple[Any, dict[str, Any]]:
        step = self.step(observation, configuration)
        if self.last_step is not None and step < self.last_step:
            self.reset()
        self.last_step = step
        base_report: dict[str, Any] = {
            "revision": self.REVISION,
            "changed": False,
            "step": step,
        }
        if not isinstance(selected, dict):
            report = {**base_report, "reason": "no_action"}
            self.last_report = report
            return selected, report

        blocked, active_report = self._clear_or_block_active(observation, step)
        if blocked:
            report = {**base_report, **(active_report or {})}
            self.last_report = report
            return selected, report

        turns = max(1, _integer(_get(configuration, "turnsPerDay", 24), 24))
        last = _integer(_get(configuration, "episodeSteps", 720), 720) - 2
        if step // turns < self.min_day:
            report = {**base_report, "reason": "opening_protected"}
            if active_report is not None:
                report["prior"] = active_report
            self.last_report = report
            return selected, report
        if step > last - self.terminal_buffer_steps:
            report = {**base_report, "reason": "terminal_buffer"}
            if active_report is not None:
                report["prior"] = active_report
            self.last_report = report
            return selected, report

        plan, evaluated, reason = self._plan(
            observation, configuration, selected, step
        )
        if plan is None:
            report = {**base_report, "reason": reason, "evaluated": evaluated}
            if active_report is not None:
                report["prior"] = active_report
            self.last_report = report
            return selected, report

        result = deepcopy(selected)
        result["market"] = list(result.get("market") or ())
        result["market"].append(["BUY_PRODUCT", plan["item"], plan["quantity"]])
        private = self._post_unit_private(observation, configuration, selected)
        shed = _get(private, "shed", {}) if private is not None else {}
        baseline_shed = max(0, _integer(_get(shed, plan["item"], 0)))
        self.active = CarryLot(
            item=plan["item"],
            quantity=plan["quantity"],
            entry_step=step,
            baseline_shed=baseline_shed,
            worst_cost=plan["worst_cost"],
            worst_receipt=plan["worst_receipt"],
            worst_profit=plan["worst_profit"],
            absorption=plan["absorption"],
            rival_supply_stress=plan["rival_supply_stress"],
        )
        report = {
            **base_report,
            "changed": True,
            "reason": "append_carry_buy",
            "entry": self.active.public(),
            "append_index": len(result["market"]) - 1,
            "evaluated": evaluated,
        }
        if active_report is not None:
            report["prior"] = active_report
        self.last_report = report
        return result, report
