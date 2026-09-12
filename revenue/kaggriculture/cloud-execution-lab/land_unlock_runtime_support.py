# SPDX-License-Identifier: Apache-2.0
"""Recovery-safe live adapter for the P02 land-unlock timing certificate.

The certificate in :mod:`land_unlock_timing` reasons about one represented
``BUY_LAND``.  This adapter is deliberately smaller than a route controller:
it moves only that exact order, never calls the producer, and binds any later
suppression to an observed successful early fill.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

LAND_ORDER = ["BUY_LAND"]


def _step(observation, configuration):
    value = observation.get("step")
    if value is not None:
        return int(value)
    return (int(observation["day"]) * int(configuration.get("turnsPerDay", 24))
            + int(observation["hour"]))


def _unlocked_count(observation):
    player = int(observation["player"])
    return len(observation["farms"][player].get("unlocked_quadrants", ()))


def _land_slots(action, limit):
    market = action.get("market", []) if isinstance(action, dict) else []
    if not isinstance(market, list):
        return []
    return [index for index, order in enumerate(market[:limit])
            if isinstance(order, list) and order == LAND_ORDER]


def _append_slot(action, limit):
    market = action.get("market", []) if isinstance(action, dict) else []
    if not isinstance(market, list):
        return None
    prefix = market[:limit]
    last = max((index for index, order in enumerate(prefix) if order), default=-1)
    for index in range(last + 1, limit):
        if index >= len(market) or not market[index]:
            return index
    return None


def _set_slot(action, slot, order):
    result = deepcopy(action)
    market = list(result.get("market", []))
    while len(market) <= slot:
        market.append([])
    market[slot] = deepcopy(order)
    result["market"] = market
    return result


def _remove_unique_land(action, limit):
    slots = _land_slots(action, limit)
    if len(slots) != 1:
        return None, slots
    return _set_slot(action, slots[0], []), slots


def _busy_spatial(agent):
    spatial = getattr(agent, "spatial", None)
    if spatial is None:
        return False
    pending = getattr(spatial, "_pending", None) or {}
    return bool(
        getattr(spatial, "plans", None)
        or pending.get("plans")
        or getattr(spatial, "crop_intent", None) is not None
        or getattr(spatial, "sale_obligation", None) is not None
        or getattr(spatial, "_crop_repair", None) is not None
    )



class LandUnlockOverlaySupport:
    """Shared helpers for the public live overlay."""

    def __init__(self, *, analyzer=None, mechanics=None, max_shift=4,
                 mode="both", decision_steps=None, max_events=64):
        if mode not in ("advance", "both"):
            raise ValueError("mode must be advance or both")
        self._analyzer = analyzer
        self._mechanics = mechanics
        self.max_shift = int(max_shift)
        self.mode = mode
        self._decision_steps = (None if decision_steps is None
                                else tuple(int(value) for value in decision_steps))
        self.max_events = int(max_events)
        self.pending = None
        self.last_step = None
        self.events = []

    def reset(self):
        self.pending = None
        self.last_step = None
        self.events = []

    def _record(self, now, kind, **details):
        event = {"step": int(now), "kind": kind, **deepcopy(details)}
        self.events.append(event)
        if len(self.events) > self.max_events:
            del self.events[:-self.max_events]
        return event

    def _components(self):
        if self._analyzer is None:
            from land_unlock_timing import analyze_unlock_timing
            analyzer = analyze_unlock_timing
        else:
            analyzer = self._analyzer
        if self._mechanics is None:
            import mechanics
            mechanics_module = mechanics
        else:
            mechanics_module = self._mechanics
        return analyzer, mechanics_module

    def _decisions(self):
        if self._decision_steps is not None:
            return self._decision_steps
        from scheduler import parent
        self._decision_steps = tuple(int(row[0]) for row in parent.DECISIONS)
        return self._decision_steps

    @staticmethod
    def _route(agent):
        controller = getattr(agent, "controller", None)
        route_id = getattr(controller, "cur", None)
        routes = getattr(controller, "R", None)
        if route_id is None or not isinstance(routes, Mapping) or route_id not in routes:
            return None, None
        route = routes[route_id]
        if not isinstance(route, (list, tuple)):
            return None, None
        return route_id, route

    def _base_guard(self, agent):
        features = getattr(agent, "features", None)
        if features is not None:
            if getattr(features, "consumer", "frozen") != "frozen":
                return "non_frozen_consumer"
            if getattr(features, "terminal_route", False):
                return "terminal_route_owns_tape"
        if getattr(agent, "quadrant", None) is not None:
            return "quadrant_owner_active"
        if _busy_spatial(agent):
            return "spatial_owner_active"
        return None

    def _crosses_decision(self, now, certificate):
        end = max(int(certificate.original_step), int(certificate.recommended_step),
                  int(certificate.first_plant_step))
        return any(int(now) < point <= end for point in self._decisions())

    def _analyze(self, observation, configuration, route, action, now):
        analyzer, mechanics = self._components()
        virtual = list(route)
        if not 0 <= now < len(virtual):
            return None, {"certified": False, "reason": "step_outside_route"}
        virtual[now] = deepcopy(action)
        return analyzer(mechanics, observation, configuration, virtual,
                        max_shift=self.max_shift)

    def _certify_insertion(self, observation, configuration, route, action,
                           now, original_step, original_slot):
        limit = int(configuration.get("maxMarketOrdersPerTurn", 10))
        if _land_slots(action, limit):
            return None, None, {"certified": False, "reason": "current_action_already_has_land"}
        slot = _append_slot(action, limit)
        if slot is None:
            return None, None, {"certified": False, "reason": "no_trailing_executable_slack"}
        candidate = _set_slot(action, slot, LAND_ORDER)
        virtual = list(route)
        if not 0 <= now < len(virtual):
            return None, None, {"certified": False, "reason": "step_outside_route"}
        if 0 <= int(original_step) < len(virtual) and int(original_step) != now:
            old = deepcopy(virtual[int(original_step)])
            market = old.get("market", []) if isinstance(old, dict) else []
            if (not isinstance(market, list) or not 0 <= int(original_slot) < len(market)
                    or market[int(original_slot)] != LAND_ORDER):
                return None, None, {"certified": False,
                                    "reason": "represented_original_land_changed"}
            market = list(market)
            market[int(original_slot)] = []
            old["market"] = market
            virtual[int(original_step)] = old
        virtual[now] = deepcopy(candidate)
        analyzer, mechanics = self._components()
        certificate, report = analyzer(mechanics, observation, configuration,
                                       virtual, max_shift=0)
        if (certificate is None or int(certificate.original_step) != now
                or int(certificate.recommended_step) != now):
            return None, None, report
        return candidate, slot, report

    def _repeat_pending_action(self, action, now, limit):
        pending = self.pending
        if pending is None:
            return None
        if pending["phase"] == "defer_scheduled" and now == pending["original_step"]:
            result, slots = _remove_unique_land(action, limit)
            if result is not None:
                return result, "defer_replay", slots[0]
        if pending["phase"] == "await_fill" and now == pending["emitted_step"]:
            slot = int(pending["emitted_slot"])
            market = action.get("market", []) if isinstance(action, dict) else []
            if (isinstance(market, list)
                    and (slot >= len(market) or not market[slot])
                    and not _land_slots(action, limit)):
                return _set_slot(action, slot, LAND_ORDER), "insert_replay", slot
        return None

