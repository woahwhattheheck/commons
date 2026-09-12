# SPDX-License-Identifier: Apache-2.0
"""Current-ABI recovery of the submitted V3.1 R04 market microstack.

This module intentionally does not call a producer/controller. It exposes the
two market stages that must surround independently-owned H4/row-shed work:

    selected action
      -> sale_window_transform()   # native pre-288 + E184 H8/L3 + V224 order
      -> [H4 owner]
      -> [row-shed owner]
      -> evening_flush_transform()

The caller supplies current projected-shed and future-authored-action evidence.
Missing or malformed evidence fails closed to the already-selected action.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

DONOR_COMMIT = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
FULL_ROUTER_GIT_BLOB = "a3e2fe87c717d128e43c9b65bae2265f40d1d76d"
L3_GIT_BLOB = "fb26e2ca9985cc65b1127f4eec654fb5cb2a3df0"

FULL_ROUTER_PATH = (
    "revenue/kaggriculture/cloud-execution-lab/"
    "candidates/v3/overlay/r04_full_router.py"
)
L3_PATH = (
    "revenue/kaggriculture/cloud-execution-lab/"
    "candidates/v3/overlay/r04_no_late_sale_advance.py"
)

LAST_STEP = 718
ADVANCE_START = 288
SALE_HORIZON = 8
L3_THRESHOLD = 648
MAX_ORDERS = 10
PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
ANIMALS = {"GOOSE", "COW", "SHEEP"}
FLUSH_ITEMS = ("WOOL", "MILK", "STRAWBERRY", "MELON")
FLUSH_HOURS = (21, 22, 23)

RIVAL_GATE_WINDOW = (1, 144)
RIVAL_GATE_SHARE = 0.8
RIVAL_GATE_REQUIRED_SEEN = RIVAL_GATE_WINDOW[1] - RIVAL_GATE_WINDOW[0]


def _plain_nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _strict_bool(name: str, value: Any) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name} must be exact bool")
    return value


@dataclass
class _PlayerState:
    last_step: int = -1
    sale_due_step: int = -1
    advanced_sales: dict[str, int] = field(default_factory=dict)
    sale_window_debts: dict[int, dict[str, int]] = field(default_factory=dict)


@dataclass
class _RivalGateState:
    same: int = 0
    seen: int = 0
    last: int = -1
    decision: bool | None = None
    valid: bool = True


class R04MarketMicrostackCurrentABI:
    """Stateful current-ABI recovery of submitted H8/L3/evening behavior.

    The class deliberately exposes sale-window and evening-flush as two separate
    calls. H4 and row-shed belong between them and have independent owners.
    """

    def __init__(
        self,
        *,
        sale_window: bool = False,
        sale_fertilizer: bool = False,
        no_late_sale_advance: bool = False,
        evening_flush: bool = False,
    ):
        self.sale_window = _strict_bool("sale_window", sale_window)
        self.sale_fertilizer = _strict_bool("sale_fertilizer", sale_fertilizer)
        self.no_late_sale_advance = _strict_bool(
            "no_late_sale_advance", no_late_sale_advance
        )
        self.evening_flush = _strict_bool("evening_flush", evening_flush)
        self._players: dict[int, _PlayerState] = {}
        self._rivals: dict[int, _RivalGateState] = {}

    # ---- public shared-debt seam -------------------------------------------------

    def reservation_debts(self, player: int) -> dict[int, dict[str, int]]:
        """Return a detached H8 debt snapshot for the H4 composition seam."""
        if type(player) is not int or player not in (0, 1):
            raise ValueError("player must be 0 or 1")
        state = self._players.get(player)
        return deepcopy({} if state is None else state.sale_window_debts)

    def replace_reservation_debts(
        self, player: int, debts: Mapping[int, Mapping[str, int]]
    ) -> None:
        """Replace H8 debt with a validated H4-updated snapshot.

        A composition wrapper should call this only with the debt snapshot
        returned by the independently-owned H4 transform. This prevents H8 and
        H4 from reserving the same authored future STRAWBERRY units twice.
        """
        if type(player) is not int or player not in (0, 1):
            raise ValueError("player must be 0 or 1")
        clean = self._validated_debts(debts)
        state = self._players.setdefault(player, _PlayerState())
        state.sale_window_debts = clean

    # ---- validation -------------------------------------------------------------

    @staticmethod
    def _validated_debts(
        debts: Mapping[int, Mapping[str, int]]
    ) -> dict[int, dict[str, int]]:
        if not isinstance(debts, Mapping):
            raise ValueError("debts must be a mapping")
        clean: dict[int, dict[str, int]] = {}
        for due, items in debts.items():
            if type(due) is not int or not 0 <= due <= LAST_STEP:
                raise ValueError("debt due-step must be a plain episode step")
            if not isinstance(items, Mapping):
                raise ValueError("debt item map must be a mapping")
            row: dict[str, int] = {}
            for item, quantity in items.items():
                if item not in PRODUCTS or not _plain_nonnegative_int(quantity):
                    raise ValueError(
                        "debt entries must be known products/nonnegative ints"
                    )
                if quantity:
                    row[item] = quantity
            if row:
                clean[due] = row
        return clean

    @staticmethod
    def _standard_configuration(configuration: Any) -> dict[str, Any]:
        if configuration is None:
            return {}
        if not isinstance(configuration, dict):
            raise ValueError("configuration must be dict or None")
        for key, expected in (
            ("boardSize", 10),
            ("turnsPerDay", 24),
            ("shedCapacity", 100),
            ("maxMarketOrdersPerTurn", 10),
        ):
            value = configuration.get(key, expected)
            if type(value) is not int or value != expected:
                raise ValueError(f"nonstandard {key}")
        return configuration

    @staticmethod
    def _identity(observation: Any) -> tuple[int, int, dict[str, Any]]:
        if not isinstance(observation, dict):
            raise ValueError("observation must be dict")
        step = observation.get("step")
        player = observation.get("player")
        farms = observation.get("farms")
        if type(step) is not int or not 0 <= step <= LAST_STEP:
            raise ValueError("invalid public step")
        if type(player) is not int or player not in (0, 1):
            raise ValueError("invalid public player")
        if not isinstance(farms, list) or len(farms) != 2:
            raise ValueError("farms must contain exactly two public farms")
        farm = farms[player]
        if not isinstance(farm, dict) or not isinstance(farm.get("hands", []), list):
            raise ValueError("selected public farm is malformed")
        return step, player, farm

    @staticmethod
    def _market_prices(observation: dict[str, Any]) -> dict[str, int]:
        market = observation.get("market")
        if not isinstance(market, dict) or not isinstance(market.get("prices"), dict):
            raise ValueError("public market prices are required")
        prices = market["prices"]
        for item in PRODUCTS:
            if item not in prices or type(prices[item]) is not int:
                raise ValueError("complete plain-int product prices are required")
        return prices

    @staticmethod
    def _validate_action(action: Any, *, workers: int | None = None) -> None:
        if not isinstance(action, dict):
            raise ValueError("selected action must be dict")
        farmer = action.get("farmer", ["PASS"])
        hands = action.get("hands", [])
        market = action.get("market", [])
        if (
            not isinstance(farmer, list)
            or not isinstance(hands, list)
            or not isinstance(market, list)
        ):
            raise ValueError("selected action envelope is malformed")
        if workers is not None and len(hands) + 1 != workers:
            raise ValueError("selected worker cardinality is not current-public exact")
        commands = [farmer, *hands]
        if any(not isinstance(command, list) or not command for command in commands):
            raise ValueError("worker command must be a nonempty list")
        for row in market:
            if not isinstance(row, list) or not row:
                raise ValueError("market rows must be nonempty lists")
            op = row[0]
            if op in {"SELL", "BUY_PRODUCT", "BUY_ANIMAL", "BUY_SEED"}:
                if (
                    len(row) < 3
                    or not isinstance(row[1], str)
                    or type(row[2]) is not int
                ):
                    raise ValueError("quantity market row is malformed")
            elif op in {"HIRE", "BUY_LAND"}:
                pass
            else:
                raise ValueError("unsupported market opcode at recovered boundary")

    @staticmethod
    def _validate_post_unit_shed(post_unit_shed: Any) -> dict[str, int]:
        if not isinstance(post_unit_shed, dict):
            raise ValueError("post_unit_shed must be dict")
        for item in PRODUCTS:
            if (
                item not in post_unit_shed
                or not _plain_nonnegative_int(post_unit_shed[item])
            ):
                raise ValueError(
                    "complete nonnegative post-unit product shed is required"
                )
        return post_unit_shed

    @classmethod
    def _validate_future_action(cls, action: Any) -> None:
        cls._validate_action(action, workers=None)

    @classmethod
    def _future_range(
        cls, future_actions: Any, start: int, end: int
    ) -> dict[int, dict[str, Any]]:
        if not isinstance(future_actions, Mapping):
            raise ValueError("future authored actions must be a mapping")
        result: dict[int, dict[str, Any]] = {}
        for due in range(start, end + 1):
            if due not in future_actions:
                raise ValueError(f"missing future authored action at step {due}")
            action = future_actions[due]
            cls._validate_future_action(action)
            result[due] = action
        return result

    @staticmethod
    def _queued_commands(queued_commands: Any) -> list[list[Any]]:
        if not isinstance(queued_commands, list):
            raise ValueError("queued_commands must be an explicit list")
        clean = []
        for command in queued_commands:
            if not isinstance(command, list) or not command:
                raise ValueError("queued command must be a nonempty list")
            clean.append(command)
        return clean

    @staticmethod
    def _inventories(
        observation: dict[str, Any], workers: int
    ) -> list[dict[str, int]]:
        private = observation.get("private")
        if (
            not isinstance(private, dict)
            or not isinstance(private.get("inventories"), list)
        ):
            raise ValueError("private inventories are required for PLACE safety")
        inventories = private["inventories"]
        if len(inventories) != workers or any(
            not isinstance(inventory, dict) for inventory in inventories
        ):
            raise ValueError("inventory cardinality must match current workers")
        return inventories

    # ---- exact public-opening rival gate ----------------------------------------

    def _rival_gate(
        self, observation: dict[str, Any], step: int, player: int
    ) -> bool:
        gate = self._rivals.setdefault(player, _RivalGateState())
        previous = gate.last
        if step <= previous:
            gate = self._rivals[player] = _RivalGateState()
            previous = -1

        if gate.decision is not None and step >= RIVAL_GATE_WINDOW[1]:
            gate.last = step
            return gate.decision

        if previous == -1:
            if step not in (0, RIVAL_GATE_WINDOW[0]):
                gate.valid = False
        elif step != previous + 1:
            gate.valid = False
        gate.last = step

        if step < RIVAL_GATE_WINDOW[0] or step >= RIVAL_GATE_WINDOW[1]:
            return True

        farms = observation.get("farms")
        try:
            ours = farms[player]["farmer"]
            theirs = farms[1 - player]["farmer"]
        except (TypeError, KeyError, IndexError):
            gate.valid = False
            return True
        if (
            type(ours) is not list
            or type(theirs) is not list
            or len(ours) != 2
            or len(theirs) != 2
            or any(type(value) is not int for value in [*ours, *theirs])
        ):
            gate.valid = False
            return True

        gate.seen += 1
        gate.same += tuple(ours) == tuple(theirs)
        if step == RIVAL_GATE_WINDOW[1] - 1:
            if gate.valid and gate.seen == RIVAL_GATE_REQUIRED_SEEN:
                gate.decision = gate.same >= RIVAL_GATE_SHARE * gate.seen
                return gate.decision
        return True

    # ---- debt and sale-window mechanics -----------------------------------------

    @staticmethod
    def _subtract_quantity_from_sells(
        market: list[list[Any]], remaining: dict[str, int]
    ) -> None:
        for order in market:
            if len(order) >= 3 and order[0] == "SELL":
                item = order[1]
                requested = max(0, order[2])
                removed = min(requested, remaining.get(item, 0))
                if removed:
                    order[2] -= removed
                    remaining[item] = remaining.get(item, 0) - removed

    def _settle_due(
        self, action: dict[str, Any], state: _PlayerState, step: int
    ) -> None:
        market = action["market"]
        if state.sale_due_step == step:
            remaining = dict(state.advanced_sales)
            self._subtract_quantity_from_sells(market, remaining)

        if step >= ADVANCE_START:
            debts = deepcopy(state.sale_window_debts)
            due = debts.pop(step, {})
            self._subtract_quantity_from_sells(market, due)
            state.sale_window_debts = {
                due_step: items
                for due_step, items in debts.items()
                if due_step > step
            }

        state.advanced_sales = {}
        state.sale_due_step = -1

    @staticmethod
    def _current_commands(action: dict[str, Any]) -> list[list[Any]]:
        return [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]

    def _animal_place_uncertain(
        self, action: dict[str, Any], inventories: list[dict[str, int]]
    ) -> bool:
        commands = self._current_commands(action)
        for actor, command in enumerate(commands):
            if (
                len(command) > 1
                and command[0] == "PLACE"
                and command[1] in ANIMALS
                and inventories[actor].get(command[1], 0) > 0
            ):
                return True
        return False

    def _native_advance(
        self,
        action: dict[str, Any],
        state: _PlayerState,
        step: int,
        prices: dict[str, int],
        shed: dict[str, int],
        future_actions: Any,
    ) -> tuple[bool, str]:
        next_step = step + 1
        if (
            next_step > LAST_STEP
            or next_step % 72 == 0
            or (step % 4 == 0 and step < 144)
        ):
            return False, "native_boundary"
        future = self._future_range(
            future_actions, next_step, next_step
        )[next_step]

        planned: dict[str, int] = {}
        for order in future["market"]:
            if (
                order[0] == "SELL"
                and len(order) >= 3
                and order[1] in PRODUCTS
                and order[2] > 0
            ):
                planned[order[1]] = planned.get(order[1], 0) + order[2]

        already_selling = {
            order[1]
            for order in action["market"]
            if order[0] == "SELL" and len(order) > 1
        }
        changed = False
        for item in PRODUCTS:
            if item in ("WHEAT", "FERTILIZER") or item in already_selling:
                continue
            quantity = min(shed.get(item, 0), planned.get(item, 0))
            if quantity <= 0 or prices[item] < 2:
                continue
            if len(action["market"]) >= MAX_ORDERS:
                break
            action["market"].append(["SELL", item, quantity])
            state.advanced_sales[item] = quantity
            changed = True
        if state.advanced_sales:
            state.sale_due_step = next_step
        return changed, "native_one_turn"

    def _reserve_e184(
        self,
        action: dict[str, Any],
        state: _PlayerState,
        step: int,
        prices: dict[str, int],
        shed: dict[str, int],
        future_actions: Any,
        queued_commands: Any,
        inventories: list[dict[str, int]],
    ) -> tuple[bool, str]:
        end = min(
            LAST_STEP,
            step + SALE_HORIZON,
            (step // 72 + 1) * 72 - 1,
        )
        if end <= step:
            return False, "e184_boundary"
        future = self._future_range(future_actions, step + 1, end)
        queued = self._queued_commands(queued_commands)

        market = action["market"]
        blocked = {
            order[1]
            for order in market
            if len(order) > 1 and order[0] in ("SELL", "BUY_PRODUCT")
        }
        blocked.update(
            command[1]
            for command in queued
            if len(command) > 1 and command[0] == "PICKUP"
        )
        blocked.update(
            command[1]
            for command in self._current_commands(action)
            if len(command) > 1 and command[0] == "PICKUP"
        )

        if self._animal_place_uncertain(action, inventories):
            return False, "animal_place_uncertain"

        excluded = {"WHEAT"} if self.sale_fertilizer else {
            "WHEAT", "FERTILIZER"
        }
        debts = state.sale_window_debts
        changed = False
        for item in PRODUCTS:
            if item in excluded or item in blocked or prices[item] < 2:
                continue
            available = shed[item]
            if not available or len(market) >= MAX_ORDERS:
                continue
            reservations: list[tuple[int, int]] = []
            for due_step in range(step + 1, end + 1):
                authored = future[due_step]
                work = self._current_commands(authored)
                if any(
                    len(command) > 1
                    and command[0] == "PICKUP"
                    and command[1] == item
                    for command in work
                ):
                    break
                if any(
                    len(order) > 1
                    and order[0] == "BUY_PRODUCT"
                    and order[1] == item
                    for order in authored["market"]
                ):
                    break
                planned = sum(
                    max(0, order[2])
                    for order in authored["market"]
                    if (
                        len(order) >= 3
                        and order[0] == "SELL"
                        and order[1] == item
                    )
                )
                remaining = max(
                    0, planned - debts.get(due_step, {}).get(item, 0)
                )
                amount = min(available, remaining)
                if amount:
                    reservations.append((due_step, amount))
                    available -= amount
                if not available:
                    break
            quantity = sum(amount for _, amount in reservations)
            if quantity:
                market.append(["SELL", item, quantity])
                changed = True
                for due_step, amount in reservations:
                    debt = debts.setdefault(due_step, {})
                    debt[item] = debt.get(item, 0) + amount
        state.sale_window_debts = debts
        return changed, "e184_h8"

    @staticmethod
    def _sales_first(action: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Exact V224 positive-row sale-first transform on an admitted envelope."""
        original = action["market"][:MAX_ORDERS]
        # The historical implementation silently compacted falsey/nonpositive
        # rows. Current ABI tightens that envelope: such evidence fails closed
        # before we are allowed to move a live SELL across it.
        for row in original:
            if row[0] not in {"HIRE", "BUY_LAND"} and row[2] <= 0:
                raise ValueError(
                    "nonpositive market row is unsafe for V224 recovery"
                )
        orders = [list(row) for row in original]
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

    # ---- public transforms -------------------------------------------------------

    def sale_window_transform(
        self,
        observation: Any,
        configuration: Any,
        selected_action: Any,
        *,
        post_unit_shed: Any,
        future_actions: Any = None,
        queued_commands: Any = None,
    ):
        """Apply the recovered pre-H4 market stage; return ``(action, report)``."""
        fallback = deepcopy(selected_action)
        report = {
            "stage": "sale_window",
            "changed": False,
            "reason": "disabled",
            "on_tape": True,
            "l3_suppressed": False,
            "debts_after": {},
        }

        try:
            self._standard_configuration(configuration)
            step, player, farm = self._identity(observation)
            prices = self._market_prices(observation)
            workers = 1 + len(farm.get("hands", []))
            self._validate_action(selected_action, workers=workers)
            shed = self._validate_post_unit_shed(post_unit_shed)
            inventories = self._inventories(observation, workers)

            on_tape = self._rival_gate(observation, step, player)
            report["on_tape"] = on_tape
            if not self.sale_window:
                return fallback, report
            if step >= LAST_STEP:
                report["reason"] = "terminal_identity"
                return fallback, report

            original_state = deepcopy(
                self._players.get(player, _PlayerState())
            )
            work = deepcopy(original_state)
            if step <= work.last_step:
                work = _PlayerState()
            work.last_step = step

            action = deepcopy(selected_action)
            self._settle_due(action, work, step)

            changed_advance = False
            reason = "settle_only"
            evidence_missing = False
            if step < ADVANCE_START:
                try:
                    changed_advance, reason = self._native_advance(
                        action, work, step, prices, shed, future_actions
                    )
                except ValueError:
                    evidence_missing = True
                    reason = "future_evidence_missing"
            else:
                suppress = (
                    self.no_late_sale_advance
                    and step >= L3_THRESHOLD
                    and not on_tape
                )
                report["l3_suppressed"] = suppress
                if suppress:
                    reason = "l3_suppressed"
                else:
                    try:
                        changed_advance, reason = self._reserve_e184(
                            action,
                            work,
                            step,
                            prices,
                            shed,
                            future_actions,
                            queued_commands,
                            inventories,
                        )
                    except ValueError:
                        evidence_missing = True
                        reason = "future_or_queue_evidence_missing"

            sales_first_changed = False
            if step >= 144:
                action, sales_first_changed = self._sales_first(action)

            self._players[player] = work
            report.update(
                changed=action != fallback,
                reason=reason,
                advance_changed=changed_advance,
                sales_first_changed=sales_first_changed,
                evidence_missing=evidence_missing,
                debts_after=deepcopy(work.sale_window_debts),
                native_due_step=work.sale_due_step,
            )
            return action, report
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

    def evening_flush_transform(
        self,
        observation: Any,
        configuration: Any,
        selected_action: Any,
        *,
        post_unit_shed: Any,
    ):
        """Apply submitted evening flush after H4/row-shed; return action/report."""
        fallback = deepcopy(selected_action)
        report = {
            "stage": "evening_flush",
            "changed": False,
            "reason": "disabled",
        }
        if not self.evening_flush:
            return fallback, report

        try:
            self._standard_configuration(configuration)
            step, _, farm = self._identity(observation)
            prices = self._market_prices(observation)
            workers = 1 + len(farm.get("hands", []))
            self._validate_action(selected_action, workers=workers)
            stock = self._validate_post_unit_shed(post_unit_shed)
            if (
                step >= LAST_STEP
                or step < 24
                or step % 24 not in FLUSH_HOURS
            ):
                report["reason"] = "outside_flush_window"
                return fallback, report

            market = [list(row) for row in selected_action["market"]]
            selling: dict[str, int] = {}
            for order in market:
                if order[0] == "SELL" and len(order) >= 3:
                    selling[order[1]] = selling.get(order[1], 0) + max(
                        0, order[2]
                    )

            extra = []
            for item in FLUSH_ITEMS:
                quantity = stock[item] - selling.get(item, 0)
                if quantity > 0 and prices[item] >= 2:
                    extra.append(["SELL", item, quantity])
            room = MAX_ORDERS - len(market)
            if not extra or room <= 0:
                report["reason"] = "no_flush_room_or_stock"
                return fallback, report

            extra.sort(key=lambda order: -prices[order[1]] * order[2])
            result = deepcopy(selected_action)
            result["market"] = extra[:room] + market
            report.update(
                changed=result != fallback,
                reason="evening_flush",
                inserted=deepcopy(extra[:room]),
            )
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
