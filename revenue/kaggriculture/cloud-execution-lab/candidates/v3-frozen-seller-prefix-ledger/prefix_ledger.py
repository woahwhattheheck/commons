# SPDX-License-Identifier: Apache-2.0
"""Exact-prefix reconciliation for FrozenSelected's completed seller state.

The official market executes only ``market[:maxMarketOrdersPerTurn]``.  The
canonical seller currently computes its final ``pending`` values from the full
returned list, so an inactive suffix SELL can be checkpointed as though stock
left the shed.  This module changes no action.  It repairs only the seller state
before TitanAgent snapshots it, and restores only future rows already owned by
the pre-transform or newly chosen seller plan.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

DEFAULT_MAX_ORDERS = 10
TRACKED_PRODUCTS = (
    "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL",
)


def _uint(value: Any, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"expected integer >= {minimum}")
    return value


def observation_step(observation: Mapping[str, Any],
                     configuration: Mapping[str, Any] | None = None) -> int:
    cfg = dict(configuration or {})
    explicit = observation.get("step")
    if explicit is not None:
        return _uint(explicit)
    turns = _uint(cfg.get("turnsPerDay", 24), minimum=1)
    return _uint(observation.get("day")) * turns + _uint(observation.get("hour"))


def _engine_quantity(order: Any) -> int:
    """Match the official parser's quantity acceptance for SELL rows."""
    if not (isinstance(order, list) and len(order) >= 3 and order[0] == "SELL"):
        return 0
    try:
        quantity = int(order[2])
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, quantity)


def executable_sales(market: Sequence[Any], shed: Mapping[str, Any],
                     max_orders: int) -> dict[str, int]:
    """Return physically fillable own SELL units in the official first-N prefix.

    Price and the rival queue cannot reduce an own SELL's unit count.  The only
    own-side fill bound is current shed stock, consumed in queue order.  Unknown
    products and malformed rows contribute no invented fill.
    """
    limit = _uint(max_orders, minimum=1)
    remaining: dict[str, int] = {}
    for product in TRACKED_PRODUCTS:
        raw = dict(shed or {}).get(product, 0)
        remaining[product] = _uint(raw)
    sold: Counter[str] = Counter()
    for order in list(market or ())[:limit]:
        if not (isinstance(order, list) and len(order) >= 2
                and order[0] == "SELL" and order[1] in remaining):
            continue
        product = order[1]
        fill = min(_engine_quantity(order), remaining[product])
        if fill:
            sold[product] += fill
            remaining[product] -= fill
    return dict(sold)


def _future_rows(rows: Iterable[Any], now: int, capacity: int) -> list[tuple[int, int]]:
    """Validate and retain an owned future plan, clipped to unsold stock."""
    left = _uint(capacity)
    result: list[tuple[int, int]] = []
    last_when = now
    for raw in list(rows or ()):
        if not (isinstance(raw, (list, tuple)) and len(raw) == 2):
            raise ValueError("malformed planned sale row")
        when, quantity = _uint(raw[0]), _uint(raw[1])
        if when <= now or quantity <= 0:
            continue
        if when < last_when:
            raise ValueError("planned sale rows are not chronological")
        last_when = when
        if left <= 0:
            continue
        take = min(quantity, left)
        result.append((when, take))
        left -= take
    return result


def _chosen_plan(diagnostics: Mapping[str, Any] | None, product: str) -> tuple[bool, Sequence[Any]]:
    chosen = dict(diagnostics or {}).get("chosen")
    if not isinstance(chosen, Mapping):
        return False, ()
    plans = chosen.get("plans")
    if isinstance(plans, Mapping) and product in plans:
        return True, plans[product]
    if chosen.get("item") == product:
        return True, chosen.get("plan") or ()
    return False, ()


def reconcile_prefix_ledger(*,
                            planned_before: Mapping[str, Sequence[Any]],
                            planned_after: Mapping[str, Sequence[Any]],
                            pending_after: Mapping[str, Any],
                            diagnostics: Mapping[str, Any] | None,
                            shed: Mapping[str, Any],
                            market: Sequence[Any],
                            step: int,
                            max_orders: int) -> tuple[
                                dict[str, list[tuple[int, int]]],
                                dict[str, int],
                                dict[str, Any],
                            ]:
    """Return a checkpoint matching the action the official engine can execute.

    The function is pure and transactional.  A caller commits the returned
    copies only after all products and rows validate.  It never creates a sale
    date: future rows come from either the seller's newly chosen plan, its
    already-retained post-transform plan, or the exact pre-transform plan.
    """
    now = _uint(step)
    limit = _uint(max_orders, minimum=1)
    if not isinstance(market, Sequence) or isinstance(market, (str, bytes, bytearray)):
        raise ValueError("market must be a sequence")
    if not isinstance(planned_before, Mapping) or not isinstance(planned_after, Mapping):
        raise ValueError("planned ledgers must be mappings")
    if not isinstance(pending_after, Mapping) or not isinstance(shed, Mapping):
        raise ValueError("pending and shed must be mappings")

    active = executable_sales(market, shed, limit)
    whole = executable_sales(market, shed, max(limit, len(market)))
    new_planned: dict[str, list[tuple[int, int]]] = {
        str(product): [tuple(row) for row in list(rows)]
        for product, rows in planned_after.items()
    }
    new_pending: dict[str, int] = {
        str(product): _uint(quantity)
        for product, quantity in pending_after.items()
    }
    changes: list[dict[str, Any]] = []

    for product in TRACKED_PRODUCTS:
        if product not in planned_before or not list(planned_before.get(product, ())):
            continue
        stock = _uint(dict(shed).get(product, 0))
        active_sold = min(stock, active.get(product, 0))
        whole_sold = min(stock, whole.get(product, 0))
        phantom = max(0, whole_sold - active_sold)
        expected_pending = stock - active_sold
        canonical_pending = new_pending.get(product, expected_pending)
        if phantom <= 0 or canonical_pending == expected_pending:
            continue

        chosen, chosen_rows = _chosen_plan(diagnostics, product)
        after_rows = list(planned_after.get(product, ()))
        before_rows = list(planned_before.get(product, ()))
        if chosen:
            source, source_rows = "chosen", chosen_rows
        elif after_rows:
            source, source_rows = "after", after_rows
        else:
            source, source_rows = "before", before_rows
        restored = _future_rows(source_rows, now, expected_pending)

        new_pending[product] = expected_pending
        if restored:
            new_planned[product] = restored
        else:
            new_planned.pop(product, None)
        changes.append({
            "product": product,
            "stock": stock,
            "active_sold": active_sold,
            "whole_queue_sold": whole_sold,
            "phantom_suffix_units": phantom,
            "pending_before_repair": canonical_pending,
            "pending_after_repair": expected_pending,
            "plan_source": source,
            "planned_before_transform": before_rows,
            "planned_after_transform": after_rows,
            "planned_after_repair": restored,
        })

    return new_planned, new_pending, {
        "changed": bool(changes),
        "reason": "reconciled" if changes else "already_prefix_coherent",
        "step": now,
        "first_n": limit,
        "active_sales": active,
        "whole_queue_sales": whole,
        "changes": changes,
        "action_changed": False,
    }


def _owned_tail_candidate(selected: Mapping[str, Any],
                          planned_before: Mapping[str, Sequence[Any]],
                          max_orders: int) -> bool:
    """Return whether a tracked inactive SELL can erase an existing future plan."""
    limit = _uint(max_orders, minimum=1)
    market = selected.get("market", [])
    if not isinstance(market, list) or len(market) <= limit:
        return False
    owned = {product for product, rows in planned_before.items()
             if product in TRACKED_PRODUCTS and bool(list(rows or ()))}
    if not owned:
        return False
    return any(isinstance(order, list) and len(order) >= 2
               and order[0] == "SELL" and order[1] in owned
               for order in market[limit:])


def _matching_snapshot(consumer: Any, observation: Mapping[str, Any],
                       selected: Mapping[str, Any], configuration: Mapping[str, Any]):
    pair = getattr(consumer, "selected_post_units", None)
    binding = getattr(consumer, "selected_post_units_binding", None)
    if pair is None or binding is None or len(binding) != 4:
        return None
    try:
        expected = (
            observation_step(observation, configuration),
            int(observation["player"]),
            selected.get("farmer"),
            selected.get("hands", []),
        )
    except (KeyError, TypeError, ValueError):
        return None
    if tuple(binding[:2]) != expected[:2] or tuple(binding[2:]) != expected[2:]:
        return None
    if not (isinstance(pair, tuple) and len(pair) == 2
            and isinstance(pair[1], Mapping)):
        return None
    return pair


def _wrap_consumer(agent: Any, state: MutableMapping[str, Any]) -> None:
    consumer = getattr(agent, "consumer", None)
    if consumer is None or getattr(consumer, "_prefix_ledger_wrapped", False):
        return
    original = consumer.transform

    def transform(observation, configuration, selected):
        cfg = dict(configuration or {})
        planned_before = deepcopy(getattr(consumer, "planned", {}))
        candidate = False
        terminal = False
        try:
            step = observation_step(observation, cfg)
            episode_steps = _uint(cfg.get("episodeSteps", 720), minimum=2)
            limit = _uint(cfg.get("maxMarketOrdersPerTurn", DEFAULT_MAX_ORDERS), minimum=1)
            terminal = step >= episode_steps - 2
            candidate = (not terminal and _owned_tail_candidate(
                selected, planned_before, limit
            ))
        except (AttributeError, TypeError, ValueError, OverflowError):
            step = 0
            limit = DEFAULT_MAX_ORDERS

        previous_capture = bool(getattr(consumer, "capture_post_units", False))
        if candidate:
            consumer.capture_post_units = True
        try:
            returned = original(observation, configuration, selected)
        finally:
            consumer.capture_post_units = previous_capture

        report: dict[str, Any] = {
            "changed": False,
            "reason": ("terminal_state_unchanged" if terminal
                       else "no_owned_tail_plan_candidate" if not candidate
                       else "no_matching_completed_unit_snapshot"),
            "action_changed": False,
        }
        pair = (_matching_snapshot(consumer, observation, returned, cfg)
                if candidate else None)
        if pair is not None:
            try:
                planned, pending, report = reconcile_prefix_ledger(
                    planned_before=planned_before,
                    planned_after=getattr(consumer, "planned", {}),
                    pending_after=getattr(consumer, "pending", {}),
                    diagnostics=getattr(consumer, "diagnostics", {}),
                    shed=pair[1].get("shed", {}),
                    market=returned.get("market", []),
                    step=step,
                    max_orders=limit,
                )
            except (AttributeError, KeyError, TypeError, ValueError, OverflowError) as exc:
                report = {
                    "changed": False,
                    "reason": "reconciliation_failed_closed",
                    "error": f"{type(exc).__name__}: {exc}"[:500],
                    "action_changed": False,
                }
            else:
                if report["changed"]:
                    consumer.planned = planned
                    consumer.pending = pending
                    state["repaired_turns"] = int(state.get("repaired_turns", 0)) + 1
                    state["phantom_units"] = int(state.get("phantom_units", 0)) + sum(
                        int(row["phantom_suffix_units"]) for row in report["changes"])
        state["last_report"] = deepcopy(report)
        diagnostics = getattr(consumer, "diagnostics", None)
        if isinstance(diagnostics, dict):
            diagnostics["prefix_ledger"] = deepcopy(report)
        if isinstance(getattr(agent, "diagnostics", None), dict):
            agent.diagnostics["prefix_ledger"] = deepcopy(report)
        return returned

    consumer.transform = transform
    consumer._prefix_ledger_wrapped = True


def install(agent: Any) -> Any:
    """Install the state-only repair across every TitanAgent reconstruction."""
    if getattr(agent, "_prefix_ledger_installed", False):
        return agent
    state: dict[str, Any] = {"repaired_turns": 0, "phantom_units": 0}
    original_initialize = agent._initialize

    def initialize():
        original_initialize()
        _wrap_consumer(agent, state)

    agent._initialize = initialize
    agent._prefix_ledger_state = state
    agent._prefix_ledger_installed = True
    # Tests and unusual callers may install after initialization.
    _wrap_consumer(agent, state)
    return agent
