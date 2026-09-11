"""TITAN V3.1 B6 practice arm: fail-closed dead-stock sweep.

The transform advances only projected shed stock that has no remaining authored farm
consumer. It is deliberately outside ``overlay/**`` and outside the deterministic V3
package; source/focused tests establish mechanics custody, not competitive economics or an
official 1:1 gate.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
OVERLAY = V3 / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_full_router as base  # noqa: E402


# Exact deterministic R04 settings in apply_v3.py at canonical base 508b342f.
V31_SALE_HORIZON = 8
V31_OPEN_ROUNDTRIP = 0
V31_ROW_ORDER = True
V31_EVENING_FLUSH = True
V31_SALE_FERTILIZER = True
V31_CATTLE_EARLY = True

# These are consumed by dynamic outer layers rather than only by the static active tape:
# V233 sheep service buys/picks up WHEAT; V219 tomato workers can buy/pick up FERTILIZER.
# Permanently reserve them rather than attempting to infer those dynamic future states.
DYNAMIC_CONSUMER_ITEMS = frozenset(("WHEAT", "FERTILIZER"))

B6_REPORT = {
    "calls": 0,
    "activations": 0,
    "sell_rows_added": 0,
    "units_advanced": 0,
    "posted_quote_value": 0,
    "capacity_declines": 0,
    "native_consumer_blocks": 0,
    "queued_consumer_blocks": 0,
    "same_turn_buy_blocks": 0,
}


def reset_b6_report() -> None:
    for key in B6_REPORT:
        B6_REPORT[key] = 0


def _pickup_item(command):
    if command and len(command) > 1 and command[0] == "PICKUP":
        item = command[1]
        if item in base.PRODUCTS:
            return item
    return None


def _commands(action):
    return [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]


def future_consumer_items(policy, state, step):
    """Return products with any remaining native/queued shed PICKUP obligation.

    Route truth after selection is deterministic for this purpose:
    * B6 does not run before ``ROUTE_STEP`` (144), when the post-selection plan is unknown;
    * from 144 through 647, ``state.plan`` is fixed by the observed shop pair;
    * at ``FINAL_PLAN_STEP`` (648), R04 forces plan 2 for the remainder.

    Weed repair can delay a previously-authored command beyond its tape turn. Those delayed
    commands live in ``state.queues``, so they are checked explicitly in addition to the
    future tape. A single possible consumer vetoes the entire current stock of that item;
    this intentionally prefers false negatives over selling a unit a future farm action needs.
    """
    step = int(step)
    queued = set()
    for queue in getattr(state, "queues", {}).values():
        for command in queue:
            item = _pickup_item(command)
            if item is not None:
                queued.add(item)

    native = set()
    if step >= base.ROUTE_STEP:
        for future_step in range(step + 1, base.LAST_STEP + 1):
            plan = 2 if future_step >= base.FINAL_PLAN_STEP else int(state.plan)
            planned = policy.tapes[plan][future_step]
            for command in _commands(planned):
                item = _pickup_item(command)
                if item is not None:
                    native.add(item)

    blocked = set(DYNAMIC_CONSUMER_ITEMS)
    blocked.update(queued)
    blocked.update(native)
    return blocked, queued, native


def dead_stock_sweep(observation, action, *, policy, state, enabled=True):
    """Sell projected stock only when no remaining farm consumer can claim that product.

    This changes market timing, not production routing. It never removes/reorders a parent
    row, never changes a parent row's market index, never exceeds ``MAX_ORDERS``, blocks
    same-turn ``BUY_PRODUCT`` rows to avoid an accidental round trip, and subtracts quantities
    the parent is already selling. New B6 rows use only currently unused trailing slots.

    ``posted_quote_value`` is displayed quote * quantity, not realized proceeds.
    """
    B6_REPORT["calls"] += 1
    if not enabled:
        return action

    step = int(observation["step"])
    if step < base.ROUTE_STEP or step >= base.LAST_STEP:
        return action

    blocked, queued, native = future_consumer_items(policy, state, step)
    B6_REPORT["queued_consumer_blocks"] += len(queued)
    B6_REPORT["native_consumer_blocks"] += len(native)

    # Preserve every parent row exactly, including defensive empty placeholders. Appending
    # after them also preserves their cross-player market row indices.
    market = [list(order) if order else order for order in action.get("market") or []]
    same_turn_buys = {
        order[1]
        for order in market
        if order and len(order) >= 2 and order[0] == "BUY_PRODUCT" and order[1] in base.PRODUCTS
    }
    B6_REPORT["same_turn_buy_blocks"] += len(same_turn_buys)
    blocked.update(same_turn_buys)

    selling = {}
    for order in market:
        if order and len(order) >= 3 and order[0] == "SELL":
            selling[order[1]] = selling.get(order[1], 0) + max(0, int(order[2]))

    view = base.FarmView(observation)
    stock = base.projected_shed(action, view)
    extra = []
    for item in base.PRODUCTS:
        if item in blocked:
            continue
        quantity = max(0, int(stock.get(item, 0)) - selling.get(item, 0))
        if quantity > 0 and int(view.prices.get(item, 0)) >= 2:
            extra.append(["SELL", item, quantity])
    if not extra:
        return action

    room = base.MAX_ORDERS - len(market)
    if room <= 0:
        B6_REPORT["capacity_declines"] += 1
        return action

    # When several safe extras compete for the remaining trailing slots, use the same
    # deterministic current displayed quote * quantity priority as shipped EVENING_FLUSH.
    extra.sort(key=lambda order: -int(view.prices.get(order[1], 0)) * int(order[2]))
    selected = extra[:room]
    if not selected:
        B6_REPORT["capacity_declines"] += 1
        return action

    result = dict(action)
    result["market"] = market + selected
    B6_REPORT["activations"] += 1
    B6_REPORT["sell_rows_added"] += len(selected)
    B6_REPORT["units_advanced"] += sum(int(order[2]) for order in selected)
    B6_REPORT["posted_quote_value"] += sum(
        int(view.prices.get(order[1], 0)) * int(order[2]) for order in selected
    )
    if len(selected) < len(extra):
        B6_REPORT["capacity_declines"] += 1
    return result


# Raw evaluator/practice entrypoint: exact shipped V3.1 R04 baseline plus B6 only.
_BASE_AGENT = base.install(
    None,
    V31_SALE_HORIZON,
    V31_OPEN_ROUNDTRIP,
    V31_ROW_ORDER,
    V31_EVENING_FLUSH,
    V31_SALE_FERTILIZER,
    V31_CATTLE_EARLY,
)


def agent(observation, configuration=None):
    action = _BASE_AGENT(observation, configuration)
    policy = base._POLICY
    if policy is None:
        return action
    state = policy.players.get(int(observation["player"]))
    if state is None:
        return action
    return dead_stock_sweep(
        observation,
        action,
        policy=policy,
        state=state,
        enabled=True,
    )


agent.telemetry = B6_REPORT
