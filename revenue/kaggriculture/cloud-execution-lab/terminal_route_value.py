# SPDX-License-Identifier: Apache-2.0
"""P21: conservative terminal route/value certificate over an existing route tape.

It never calls a producer or invents rival state. Candidate work is admitted only
in PASS-owned actor slots, must physically harvest/carry, reach the shed, deposit
before market execution, and obtain a positive quiet-rival terminal receipt by
the real final action. Integration must still use the scenario-aware seller.
"""
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from terminal_route_value_primitives import (distance, harvest_lot, integer, other_shed_collision,
    path, positive, preterminal_market_clear, route_row, shed_access, worker_idle)
from terminal_route_value_market import append_after_commitments, quiet_sale_receipts, sale_only

@dataclass(frozen=True)
class Candidate:
    worker: int
    source: str
    product: str
    quantity: int
    start_step: int
    terminal_step: int
    unit_actions: tuple
    market: tuple
    sale_slot: int
    quiet_incremental_cash: int
    target: tuple | None
    shed_target: tuple

    def as_dict(self):
        return {"worker": self.worker, "source": self.source, "product": self.product,
                "quantity": self.quantity, "start_step": self.start_step,
                "terminal_step": self.terminal_step,
                "unit_actions": [list(a) for a in self.unit_actions],
                "market": [list(o) if o else [] for o in self.market],
                "sale_slot": self.sale_slot, "quiet_incremental_cash": self.quiet_incremental_cash,
                "target": None if self.target is None else list(self.target),
                "shed_target": list(self.shed_target)}


def certify_candidate(mechanics, observation, configuration, route, *, worker,
                      target=None, carried_product=None):
    """Certify one idle-worker final-day harvest/delivery/sale opportunity."""
    if (target is None) == (carried_product is None):
        raise ValueError("supply exactly one of target or carried_product")
    seat = integer(observation.get("player"), "player", 0, 1)
    now = integer(observation.get("step"), "step")
    last = integer((configuration or {}).get("episodeSteps", 720), "episodeSteps", 2) - 2
    if now > last:
        return None, {"certified": False, "reason": "past_terminal_step"}
    farm = observation["farms"][seat]; private = observation["private"]
    positions = [farm["farmer"], *farm.get("hands", [])]; inventories = private.get("inventories", [])
    if not 0 <= worker < len(positions) or worker >= len(inventories):
        return None, {"certified": False, "reason": "worker_not_observed"}
    current_inventory = positive(inventories[worker]); start = tuple(positions[worker])
    turns = integer((configuration or {}).get("turnsPerDay", 24), "turnsPerDay", 1)
    day = now // turns
    if target is not None:
        if current_inventory:
            return None, {"certified": False, "reason": "worker_inventory_not_empty"}
        target = (int(target[0]), int(target[1])); lot, error = harvest_lot(mechanics, farm, day, target)
        if lot is None:
            return None, {"certified": False, "reason": error}
        product, quantity = lot; actions = path(start, target) + [["HARVEST"]]
        source = "harvest"; after_source = target
    else:
        product = carried_product
        if not isinstance(product, str) or current_inventory.get(product, 0) <= 0:
            return None, {"certified": False, "reason": "carried_product_not_observed"}
        if len(current_inventory) != 1:
            return None, {"certified": False, "reason": "mixed_carried_inventory_out_of_scope"}
        quantity = current_inventory[product]; actions = []; source = "carried"; after_source = start
    board = integer((configuration or {}).get("boardSize", len(farm.get("tiles", []))), "boardSize", 2, 100)
    shed_target = min(shed_access(board), key=lambda p: (distance(after_source, p), p))
    actions += path(after_source, shed_target) + [["DROP"]]
    terminal_step = now + len(actions) - 1
    if terminal_step > last:
        return None, {"certified": False, "reason": "route_finishes_after_terminal",
                      "required_terminal_step": terminal_step, "last_action_step": last}
    idle, conflict_step, conflict_action = worker_idle(route, worker, now, terminal_step)
    if not idle:
        return None, {"certified": False, "reason": "worker_has_existing_commitment",
                      "conflict_step": conflict_step, "conflict_action": deepcopy(conflict_action)}
    collision = other_shed_collision(route, worker, now, terminal_step)
    if collision is not None:
        step, index, action = collision
        return None, {"certified": False, "reason": "other_actor_shed_collision",
                      "conflict_step": step, "conflict_worker": index,
                      "conflict_action": deepcopy(action)}
    limit = integer((configuration or {}).get("maxMarketOrdersPerTurn", 10),
                 "maxMarketOrdersPerTurn", 1, 64)
    clear, market_step = preterminal_market_clear(route, now, terminal_step, limit)
    if not clear:
        return None, {"certified": False, "reason": "preterminal_market_mutation_out_of_scope",
                      "conflict_step": market_step}
    shed = positive(private.get("shed", {})); capacity = integer((configuration or {}).get("shedCapacity", 100), "shedCapacity", 1)
    if sum(shed.values()) + quantity > capacity:
        return None, {"certified": False, "reason": "drop_would_overflow_before_market",
                      "shed_total": sum(shed.values()), "incoming": quantity, "capacity": capacity}
    post_drop = dict(shed); post_drop[product] = post_drop.get(product, 0) + quantity
    final_market = list(route_row(route, terminal_step).get("market", []))
    if not sale_only(final_market, limit):
        return None, {"certified": False, "reason": "final_market_has_non_sale_commitment"}
    candidate_market, slot = append_after_commitments(final_market, product, quantity, limit)
    if candidate_market is None:
        return None, {"certified": False, "reason": "no_trailing_terminal_market_slot"}
    baseline = quiet_sale_receipts(mechanics, observation["market"], shed, final_market, limit)
    candidate = quiet_sale_receipts(mechanics, observation["market"], post_drop, candidate_market, limit)
    if baseline is None or candidate is None:
        return None, {"certified": False, "reason": "unsupported_terminal_market_prefix"}
    incremental = candidate["cash"] - baseline["cash"]
    extra_fill = candidate["filled"].get(product, 0) - baseline["filled"].get(product, 0)
    if extra_fill <= 0 or incremental <= 0:
        return None, {"certified": False, "reason": "candidate_terminal_sale_has_nopositive_quiet_receipt",
                      "extra_fill": extra_fill, "quiet_incremental_cash": incremental}
    result = Candidate(worker, source, product, quantity, now, terminal_step,
                       tuple(tuple(a) for a in actions),
                       tuple(tuple(o) if o else tuple() for o in candidate_market),
                       slot, incremental, target, shed_target)
    return result, {"certified": True, "reason": "complete_terminal_route",
                    "worker": worker, "source": source, "product": product,
                    "quantity": quantity, "terminal_step": terminal_step,
                    "last_action_step": last, "quiet_incremental_cash": incremental,
                    "sale_slot": slot,
                    "scope": "idle-worker current-yield/carried-good; static preterminal own market; quiet-rival receipt diagnostic"}


def best_candidate(mechanics, observation, configuration, route):
    """Return strongest certified opportunity by quiet cash, then shortest route."""
    seat = integer(observation.get("player"), "player", 0, 1); farm = observation["farms"][seat]
    private = observation["private"]; candidates = []
    inventories = private.get("inventories", [])
    count = 1 + len(farm.get("hands", []))
    if not isinstance(inventories, list) or len(inventories) < count:
        return None, {"certified": False, "reason": "worker_inventories_not_observed"}
    for worker in range(count):
        inventory = positive(inventories[worker])
        if len(inventory) == 1:
            product = next(iter(inventory))
            candidate, _ = certify_candidate(mechanics, observation, configuration, route,
                                              worker=worker, carried_product=product)
            if candidate is not None:
                candidates.append(candidate)
        if inventory:
            continue
        for y, row in enumerate(farm.get("tiles", [])):
            for x, tile in enumerate(row):
                if isinstance(tile, Mapping) and type(tile.get("yield_units")) is int and tile["yield_units"] > 0:
                    candidate, _ = certify_candidate(mechanics, observation, configuration, route,
                                                      worker=worker, target=(x, y))
                    if candidate is not None:
                        candidates.append(candidate)
    if not candidates:
        return None, {"certified": False, "reason": "no_complete_terminal_route"}
    winner = max(candidates, key=lambda c: (c.quiet_incremental_cash, -len(c.unit_actions),
                                             -c.quantity, -c.worker,
                                             tuple(-v for v in (c.target or c.shed_target))))
    return winner, {"certified": True, "reason": "best_complete_terminal_route",
                    "candidate_count": len(candidates), "winner": winner.as_dict()}
