# SPDX-License-Identifier: Apache-2.0
"""Default-off day-6 town/rival portfolio over the existing Arlene route bank.

The adapter never authors an action or route. At the first usable day-6
observation it may move ``base.cur`` to an already-present route only when the
underlying frozen controller proves the target prefix-compatible at the current
step. Missing/malformed public evidence preserves the incumbent route.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

import mechanics as m

MODES = frozenset({"off", "town", "town_rival"})
SCHEMA = "titan.v5.town-route-portfolio/v1"
DAY6_STEP = 6 * 24
DAY6_END = 7 * 24
HORIZON = 8 * 24
MIN_EDGE = 0.025
RIVAL_PENALTY = 0.35
ANIMAL_PRODUCT = {name: data["product"] for name, data in m.ANIMALS.items()}
PRODUCTS = frozenset(m.TOWN_CENTER_PRODUCTS)


def normalize_mode(mode: Any) -> str:
    value = str(mode or "off").strip().lower()
    if value not in MODES:
        raise ValueError(f"unknown town route mode: {mode!r}")
    return value


def _positive_int(value: Any) -> int | None:
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return None
    return quantity if quantity > 0 else None


def _shop_names(observation: Any) -> tuple[str, ...] | None:
    if not isinstance(observation, dict):
        return None
    town = observation.get("town")
    pools: list[Any] = []
    if isinstance(town, dict):
        for key in ("unlocked_shops", "unlockedShops", "shops"):
            if key in town:
                pools.append(town[key])
    for key in ("unlocked_shops", "unlockedShops"):
        if key in observation:
            pools.append(observation[key])
    for raw in pools:
        names: list[str] = []
        if isinstance(raw, dict):
            names = [str(k).upper() for k, enabled in raw.items() if enabled]
        elif isinstance(raw, (list, tuple)):
            for row in raw:
                if isinstance(row, str):
                    names.append(row.upper())
                elif isinstance(row, dict):
                    name = row.get("name", row.get("kind", row.get("shop")))
                    if isinstance(name, str) and row.get("unlocked", True):
                        names.append(name.upper())
        known = tuple(sorted({name for name in names if name in m.SHOPS}))
        if known:
            return known
    return None


def town_demand(observation: Any) -> Counter:
    shops = _shop_names(observation)
    if not shops:
        return Counter()
    out: Counter[str] = Counter()
    for shop in shops:
        out.update(m.SHOPS[shop])
    return out


def _count_public_products(value: Any, out: Counter) -> None:
    if isinstance(value, str):
        token = value.upper()
        if token in PRODUCTS:
            out[token] += 1
        elif token in ANIMAL_PRODUCT:
            out[ANIMAL_PRODUCT[token]] += 1
        return
    if isinstance(value, dict):
        for key, child in value.items():
            token = str(key).upper()
            if token in PRODUCTS or token in ANIMAL_PRODUCT:
                q = _positive_int(child)
                if q is not None:
                    out[token if token in PRODUCTS else ANIMAL_PRODUCT[token]] += q
                    continue
            _count_public_products(child, out)
        return
    if isinstance(value, (list, tuple)):
        for child in value:
            _count_public_products(child, out)


def rival_pressure(observation: Any) -> Counter:
    if not isinstance(observation, dict):
        return Counter()
    farms = observation.get("farms")
    player = observation.get("player")
    if not isinstance(farms, list) or type(player) is not int or not (0 <= player < len(farms)):
        return Counter()
    out: Counter[str] = Counter()
    for seat, farm in enumerate(farms):
        if seat != player:
            _count_public_products(farm, out)
    return out


def _profile_action(action: Any, out: Counter) -> None:
    if not isinstance(action, dict):
        return
    market = action.get("market", [])
    if isinstance(market, list):
        for row in market:
            if not (isinstance(row, list) and len(row) >= 3):
                continue
            op, item, quantity = row[0], str(row[1]).upper(), _positive_int(row[2])
            if quantity is None:
                continue
            if op == "SELL" and item in PRODUCTS:
                out[item] += quantity
            elif op == "BUY_SEED" and item in m.CROPS:
                out[item] += 0.25 * quantity
            elif op == "BUY_ANIMAL" and item in ANIMAL_PRODUCT:
                out[ANIMAL_PRODUCT[item]] += 2.0 * quantity
    hands = action.get("hands", [])
    units = [action.get("farmer"), *hands] if isinstance(hands, list) else [action.get("farmer")]
    for row in units:
        if isinstance(row, list) and len(row) >= 2 and row[0] == "PLANT":
            item = str(row[1]).upper()
            if item in m.CROPS:
                out[item] += 1.0


def route_profile(route: Any, start: int, horizon: int = HORIZON) -> Counter:
    if not isinstance(route, (list, tuple)) or start < 0:
        return Counter()
    out: Counter[str] = Counter()
    for action in route[start:min(len(route), start + horizon)]:
        _profile_action(action, out)
    return out


def _shares(counter: Counter) -> dict[str, float]:
    total = sum(float(v) for k, v in counter.items() if k in PRODUCTS and float(v) > 0)
    if total <= 0:
        return {}
    return {k: float(v) / total for k, v in counter.items() if k in PRODUCTS and float(v) > 0}


def _score(profile: Counter, demand: Counter, rivals: Counter, mode: str) -> float | None:
    p, d = _shares(profile), _shares(demand)
    if not p or not d:
        return None
    score = sum(p.get(item, 0.0) * weight for item, weight in d.items())
    if mode == "town_rival":
        r = _shares(rivals)
        if not r:
            return None
        score -= RIVAL_PENALTY * sum(p.get(item, 0.0) * weight for item, weight in r.items())
    return score


class TownRoutePortfolioController:
    """Proxy around the canonical route controller; only ``cur`` may change."""

    def __init__(self, base: Any, mode: str = "town_rival"):
        self.base = base
        self.mode = normalize_mode(mode)
        self.decided = False
        self.last_report = {
            "schema": SCHEMA, "mode": self.mode, "status": "pending",
            "step": None, "incumbent": getattr(base, "cur", None),
            "selected": getattr(base, "cur", None),
        }

    def __getattr__(self, name: str) -> Any:
        return getattr(self.base, name)

    def _compatible(self, route_id: Any, step: int) -> bool:
        check = getattr(self.base, "_switch_ok", None)
        if not callable(check):
            return False
        try:
            return bool(check(route_id, step))
        except (TypeError, ValueError, KeyError, IndexError):
            return False

    def _consider(self, observation: Any) -> None:
        if self.decided or self.mode == "off":
            return
        try:
            step = int(observation.get("step"))
        except (AttributeError, TypeError, ValueError):
            return
        if step < DAY6_STEP:
            return
        if step >= DAY6_END:
            self.decided = True
            self.last_report.update(status="missed_day6", step=step)
            return

        demand = town_demand(observation)
        rivals = rival_pressure(observation)
        if not demand or (self.mode == "town_rival" and not rivals):
            self.decided = True
            self.last_report.update(status="insufficient_public_evidence", step=step)
            return

        routes = getattr(self.base, "R", None)
        incumbent = getattr(self.base, "cur", None)
        if not isinstance(routes, dict) or incumbent not in routes:
            self.decided = True
            self.last_report.update(status="invalid_route_bank", step=step)
            return

        scores: dict[Any, float] = {}
        for route_id, route in routes.items():
            if route_id != incumbent and not self._compatible(route_id, step):
                continue
            score = _score(route_profile(route, step), demand, rivals, self.mode)
            if score is not None:
                scores[route_id] = score

        incumbent_score = scores.get(incumbent)
        if incumbent_score is None:
            self.decided = True
            self.last_report.update(status="incumbent_unscorable", step=step)
            return

        selected = incumbent
        best = incumbent_score
        for route_id in sorted(scores, key=str):
            if scores[route_id] > best + MIN_EDGE:
                selected, best = route_id, scores[route_id]

        if selected != incumbent:
            self.base.cur = selected
            status = "switched"
        else:
            status = "incumbent"

        self.decided = True
        self.last_report = {
            "schema": SCHEMA, "mode": self.mode, "status": status, "step": step,
            "incumbent": incumbent, "selected": selected,
            "incumbent_score": round(incumbent_score, 8), "selected_score": round(best, 8),
            "shops": list(_shop_names(observation) or ()),
            "demand": dict(sorted(demand.items())), "rivals": dict(sorted(rivals.items())),
            "compatible_scored_routes": len(scores),
        }

    def act(self, observation: Any):
        self._consider(observation)
        return self.base.act(observation)


def make_agent(*, mode: str = "town_rival", seed: bool = True, committed: bool = True,
               sell: bool = True, horizon: int = 8, seed_queue_selector=None):
    """Build canonical selected agent with an opt-in portfolio proxy."""
    import integrated_selected

    mode = normalize_mode(mode)
    if mode == "off":
        return integrated_selected.make_agent(
            seed=seed, committed=committed, sell=sell, horizon=horizon,
            seed_queue_selector=seed_queue_selector,
        )
    production = integrated_selected.make_production()
    controller = TownRoutePortfolioController(production.agent, mode)
    production.agent = controller
    agent = integrated_selected.IntegratedSelectedAgent(
        production, seed=seed, committed=committed, sell=sell, horizon=horizon,
        seed_queue_selector=seed_queue_selector,
    )
    agent.route_portfolio = controller
    return agent
