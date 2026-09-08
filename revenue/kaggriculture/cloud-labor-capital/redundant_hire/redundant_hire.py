# SPDX-License-Identifier: Apache-2.0
"""Bounded selected-action proposal for economically redundant current hires.

This is a cheap T10 consumer, not another producer.  It changes only current
HIRE slots after proving that the removed trailing workers add no physical
value over the remaining route through the bounded current shift.
"""
from __future__ import annotations

import copy
import math

NO_ORDER = ["SELL", "WHEAT", 0]


def _absolute_step(observation, configuration):
    step = observation.get("step")
    if step is not None:
        return int(step)
    turns = int((configuration or {}).get("turnsPerDay", 24))
    return int(observation.get("day", 0)) * turns + int(observation.get("hour", 0))


def _position(tile):
    if isinstance(tile, (list, tuple)) and len(tile) >= 2:
        return (int(tile[0]), int(tile[1]))
    if isinstance(tile, dict):
        if "x" in tile and "y" in tile:
            return (int(tile["x"]), int(tile["y"]))
        if "position" in tile:
            return _position(tile["position"])
    return None


def _move(pos, action, size):
    if pos is None or not action:
        return pos
    verb = action[0]
    x, y = pos
    if verb == "NORTH":
        y = max(0, y - 1)
    elif verb == "SOUTH":
        y = min(size - 1, y + 1)
    elif verb == "WEST":
        x = max(0, x - 1)
    elif verb == "EAST":
        x = min(size - 1, x + 1)
    return (x, y)


def _units(private):
    # The engine stores farmer + hands in inventories/positions in the same order.
    inventories = private.get("inventories", [])
    positions = private.get("positions", [])
    count = max(len(inventories), len(positions))
    return [positions[i] if i < len(positions) else None for i in range(count)]


def _tile(farm, pos):
    if pos is None:
        return None
    x, y = pos
    try:
        return farm["tiles"][y][x]
    except (IndexError, KeyError, TypeError):
        return None


def _plant_safe_for_duplicate_water(tile, step, retained_water_step):
    if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
        return False
    end = tile.get("max_lifespan_step")
    if isinstance(end, (int, float)) and end >= 0 and end < retained_water_step:
        return False
    return True


def _all_hires_affordable(action, farm, config):
    money = farm.get("money")
    if isinstance(money, bool) or not isinstance(money, (int, float)) or not math.isfinite(money) or money < 0:
        return False
    mult = config.get("farmHandCostMult", 1)
    if isinstance(mult, bool) or not isinstance(mult, (int, float)) or not math.isfinite(mult) or mult <= 0:
        return False
    hires = sum(1 for order in action.get("market", []) if order and order[0] == "HIRE")
    spent = 0.0
    already = int(farm.get("hires_today", 0))
    for offset in range(hires):
        spent += float(mult) * (already + offset + 1)
    return money >= spent


def _has_active_nonhire_market(action):
    return any(order and order[0] != "HIRE" and not (
        order[0] == "SELL" and len(order) > 2 and int(order[2]) == 0)
        for order in action.get("market", []))


def propose_redundant_hires(
    mechanics,
    observation,
    configuration,
    selected_action,
    *,
    route,
    route_id=None,
    route_switch_steps=(),
    max_route_steps=None,
):
    """Return a detached selected action with provably redundant trailing hires removed.

    The proof is intentionally narrow.  It only accepts current HIRE-only market
    queues, a complete same-route remainder of the current day, and trailing new
    workers whose route contributes only movement/PASS or duplicate WATER tasks
    already supplied by retained workers before reset.  Any uncertainty preserves
    the original action.
    """
    cfg = dict(configuration or {})
    obs = copy.deepcopy(observation)
    action = copy.deepcopy(selected_action)
    now = _absolute_step(obs, cfg)
    obs["step"] = now
    turns = int(cfg.get("turnsPerDay", 24))
    episode_steps = int(cfg.get("episodeSteps", 720))
    last = episode_steps - 2
    shift_end = min(last, (now // turns + 1) * turns - 1)
    if max_route_steps is not None:
        shift_end = min(shift_end, now + int(max_route_steps))
    report = {
        "changed": False,
        "reason": None,
        "route_id": route_id,
        "step": now,
        "removed_workers": 0,
        "removed_order_indices": [],
        "immediate_wage_saving": 0,
        "watering_witnesses": [],
        "terminal_gain": None,
        "future_cash_compatibility": "not established; later purchases/opponent response require separate evaluation",
    }

    farm = obs["farms"][int(obs.get("player", 0))]
    private = obs.get("private", {})
    orders = action.get("market", [])
    hire_indices = [i for i, order in enumerate(orders) if order and order[0] == "HIRE"]
    if not hire_indices:
        report["reason"] = "no_current_hires"
        return action, report
    if _has_active_nonhire_market(action):
        report["reason"] = "current_market_has_nonhire_order"
        return action, report
    if not _all_hires_affordable(action, farm, cfg):
        report["reason"] = "current_hires_not_all_funded"
        return action, report
    if any(now < int(step) <= shift_end for step in route_switch_steps):
        report["reason"] = "possible_route_switch"
        return action, report
    if shift_end >= len(route):
        report["reason"] = "incomplete_route"
        return action, report
    if max_route_steps is not None and shift_end <= now and now < last:
        report["reason"] = "outside_bounded_shift"
        return action, report
    if any(route[t].get("market") and any(o and o[0] == "HIRE" for o in route[t].get("market", []))
           for t in range(now + 1, shift_end + 1)):
        report["reason"] = "later_hire_changes_cost_or_spawn"
        return action, report

    positions = _units(private)
    base_count = max(1, len(positions))
    board_size = int(cfg.get("boardSize", 10))
    current_actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
    while len(positions) < len(current_actions):
        positions.append(None)
    positions = [_move(_position(pos), current_actions[i] if i < len(current_actions) else ["PASS"], board_size)
                 for i, pos in enumerate(positions)]

    # Hires spawn after current unit actions.  New worker indices therefore form a
    # trailing suffix of the next route action's hands.
    new_count = len(hire_indices)
    total_after = base_count + new_count
    retained_total = total_after
    removable = []

    # Determine whether each newly hired trailing worker is independently redundant.
    for offset in range(new_count - 1, -1, -1):
        worker_index = base_count + offset
        witness = []
        worker_pos = None
        safe = True
        for t in range(now + 1, shift_end + 1):
            packet = route[t]
            hands = packet.get("hands", [])
            unit = hands[worker_index - 1] if worker_index > 0 and worker_index - 1 < len(hands) else ["PASS"]
            verb = unit[0] if unit else "PASS"
            if verb in ("PASS", "NORTH", "SOUTH", "EAST", "WEST"):
                worker_pos = _move(worker_pos, unit, board_size)
                continue
            if verb != "WATER":
                safe = False
                break
            tile = _tile(farm, worker_pos)
            if not _plant_safe_for_duplicate_water(tile, now, t):
                safe = False
                break
            if tile.get("watered_today"):
                witness.append({"worker": worker_index, "step": t, "position": worker_pos,
                                "retained_watering": []})
                continue
            found = []
            for earlier_t in range(now + 1, shift_end + 1):
                if earlier_t > t:
                    break
                other = route[earlier_t]
                candidates = [other.get("farmer", ["PASS"]), *other.get("hands", [])]
                for retained_index in range(min(retained_total - 1, len(candidates))):
                    if retained_index == worker_index:
                        continue
                    candidate = candidates[retained_index]
                    if candidate and candidate[0] == "WATER":
                        # Route-level duplicate-water proof: current source routes encode
                        # the worker target by its preceding movement tape.  We only accept
                        # an exact same tile after replaying the retained worker locally.
                        pos = None
                        for u in range(now + 1, earlier_t + 1):
                            p = route[u]
                            acts = [p.get("farmer", ["PASS"]), *p.get("hands", [])]
                            a = acts[retained_index] if retained_index < len(acts) else ["PASS"]
                            pos = _move(pos, a, board_size)
                        if pos == worker_pos:
                            found.append([earlier_t, retained_index])
                if found:
                    break
            if not found:
                safe = False
                break
            # Structural operations on this tile between the duplicate and retained
            # watering invalidate equivalence.
            for s in range(t, found[0][0] + 1):
                p = route[s]
                for ua in [p.get("farmer", ["PASS"]), *p.get("hands", [])]:
                    if ua and ua[0] in ("HARVEST", "FERTILIZE", "DIG", "PLANT"):
                        safe = False
                        break
                if not safe:
                    break
            if not safe:
                break
            witness.append({"worker": worker_index, "step": t, "position": worker_pos,
                            "retained_watering": found})
        if not safe:
            break
        removable.append(offset)
        report["watering_witnesses"].extend(witness)
        retained_total -= 1

    if not removable:
        report["reason"] = "new_workers_have_distinct_route_value"
        return action, report

    remove_offsets = set(removable)
    removed_indices = [hire_indices[i] for i in sorted(remove_offsets)]
    for idx in removed_indices:
        action["market"][idx] = list(NO_ORDER)
    already = int(farm.get("hires_today", 0))
    mult = float(cfg.get("farmHandCostMult", 1))
    saving = sum(mult * (already + i + 1) for i in remove_offsets)
    report.update(changed=True, reason="redundant_trailing_hires", removed_workers=len(remove_offsets),
                  removed_order_indices=removed_indices, immediate_wage_saving=saving)
    return action, report
