# SPDX-License-Identifier: Apache-2.0
"""Execute offered controller continuations through the existing T04 oracle.

This is a physical execution consumer, not a route generator, selector, pricing
model or two-player simulator. Engine and simulate_bundle are injected unchanged.
Only speculative, independent controller snapshots receive action calls.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass
from hashlib import sha256
import json
from time import monotonic, perf_counter
from typing import Any, Callable, Mapping, Sequence


@dataclass(frozen=True)
class ReplayLimits:
    seconds: float = 5.0
    decisions: int = 5000


class ReplayBudgetExceeded(Exception):
    pass


def _encoded(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_encoded(value)).hexdigest()


class _Budget:
    def __init__(self, limits):
        self.deadline = monotonic() + max(0.0, float(limits.seconds))
        self.remaining = max(0, int(limits.decisions))
        self.used = 0

    def check(self):
        if monotonic() >= self.deadline:
            raise ReplayBudgetExceeded("time")

    def decision(self):
        self.check()
        if self.remaining == 0:
            raise ReplayBudgetExceeded("decisions")
        self.remaining -= 1
        self.used += 1


class _ObservedEngine:
    """Delegates every operation; no module-level monkey patch or price override."""
    def __init__(self, engine, budget):
        self.engine = engine
        self.budget = budget
        self.rows = []

    def __getattr__(self, key):
        return getattr(self.engine, key)

    def _apply_unit_action(self, *args, **kwargs):
        self.budget.check()
        return self.engine._apply_unit_action(*args, **kwargs)

    def _process_market(self, state, env):
        self.budget.check()
        observation = state[0].observation
        before_private = deepcopy(observation.private)
        before_cash = observation.farms[0]["money"]
        before_hires = observation.farms[0].get("hires_today")
        before_market = deepcopy(observation.market)
        returned = self.engine._process_market(state, env)
        self.rows.append({
            "step": int(observation.step),
            "orders": deepcopy(state[0].action.get("market", [])),
            "cash_before": before_cash,
            "cash_after": observation.farms[0]["money"],
            "cash_delta": observation.farms[0]["money"] - before_cash,
            "hires_before": before_hires,
            "hires_after": observation.farms[0].get("hires_today"),
            "private_before": before_private,
            "private_after": deepcopy(observation.private),
            "market_before": before_market,
            "market_after": deepcopy(observation.market),
        })
        return returned


def replay_routes(controller: Any, route_ids: Sequence[str],
                  observation: Mapping[str, Any], configuration: Mapping[str, Any],
                  engine: Any, simulate_bundle: Callable[..., dict], *,
                  scenarios: Mapping[str, Any], end_step: int,
                  fork_controller: Callable[[Any], Any] = deepcopy,
                  limits: ReplayLimits = ReplayLimits()) -> dict:
    """Run full current-controller continuations, once per route/scenario pair.

    Supply the existing producer BEFORE its current authoritative action. The
    original controller is never called or modified. The default deep copy suits
    the pinned Arlene controller; other controller families must provide a real
    independent fork with their own validated state contract. `cur` and `R` are
    the existing Arlene route seam, not a new generic controller protocol.

    The original `_switch_ok` decides structural compatibility. Existing future
    public-feature decisions and stock-sensitive action amendments run on each
    clone's projected observations, rather than following a stale market tape.
    No current route is selected and no feasibility probability is returned.

    T04's injected scenarios affect external inventory before the own market;
    they are not paired rival-order streams and cannot supply rival cash utility.
    The cooperative budget is shared across all pairs and cannot preempt a single
    dependency call. Overdue returns and partial pairs remain incomplete, never
    scored; completing a dependency is not itself proof of meeting the deadline.
    """
    started = perf_counter()
    routes = tuple(route_ids)
    if not routes or len(set(routes)) != len(routes):
        raise ValueError("Supply distinct offered route IDs")
    if not scenarios:
        raise ValueError("Supply explicit named scenarios")
    start = int(observation["step"])
    last = int(configuration.get("episodeSteps", 720)) - 2
    if not start <= int(end_step) <= last:
        raise ValueError("Replay ends at an executable decision")
    budget = _Budget(limits)
    cases = []
    for route_id in routes:
        for scenario_id, scenario in scenarios.items():
            case = {"offered_route": route_id, "scenario_id": scenario_id,
                    "status": "incomplete", "cash_gain": None,
                    "rival_cash_delta": None, "market_rows": []}
            cases.append(case)
            observed = None
            try:
                budget.check()
                clone = fork_controller(controller)
                if clone is controller:
                    raise ValueError("fork_controller returned the live producer")
                if route_id not in clone.R:
                    raise ValueError("Missing offered program")
                if clone.cur != route_id and not clone._switch_ok(route_id, start):
                    case.update(status="incompatible", reason="existing_prefix_differs")
                    continue
                program = clone.R[route_id]
                if len(program) <= int(end_step):
                    raise ValueError("Incomplete offered program")
                case["program_sha256"] = _digest(program)
                clone.cur = route_id
                observed = _ObservedEngine(engine, budget)
                route_trace = []

                def plan(view):
                    budget.decision()
                    action = clone.act(view)
                    route_trace.append({"step": int(view["step"]),
                                        "active_route": clone.cur})
                    return action

                result = simulate_bundle(observed, observation, configuration,
                                         plan, end_step=int(end_step),
                                         scenario=deepcopy(scenario), record_actions=True)
                budget.check()
                # Validate binding of the observer's cash to the delegated result;
                # net queue cash includes actual successful fixed-cost orders too.
                realized = sum(row["cash_delta"] for row in observed.rows)
                if realized != result["cash_gain"]:
                    raise ValueError("Observer cash does not match delegated result")
                completed = dict(status="complete", cash_gain=result["cash_gain"],
                            final_cash=result["farm"]["money"],
                            minimum_after_market_cash=min(
                                [observation["farms"][int(observation["player"])]["money"]]
                                + [row["cash_after"] for row in observed.rows]),
                            action_sha256=_digest(result["actions"]),
                            active_routes=route_trace, result=result)
                # Result encoding is cooperative work too; publish no scores
                # until the complete candidate has passed its final check.
                budget.check()
                case.update(completed)
            except ReplayBudgetExceeded as exc:
                case["reason"] = "budget:" + str(exc)
            except Exception as exc:
                case["reason"] = type(exc).__name__ + ": " + str(exc)
            finally:
                if observed is not None:
                    case["market_rows"] = observed.rows
    return {
        "schema": "titan.capital-physical-replay.v1",
        "complete": all(case["status"] == "complete" for case in cases),
        "observation_sha256": _digest(observation),
        "start_step": start, "end_step": int(end_step),
        "original_route": controller.cur,
        "scenarios": {name: asdict(value) if is_dataclass(value) else repr(value)
                      for name, value in scenarios.items()},
        "cases": cases, "decisions_executed": budget.used,
        "wall_seconds": perf_counter() - started,
        "scope": "conditional own-state execution via existing T04 oracle; not paired rival trading",
        "selection": None,
    }
