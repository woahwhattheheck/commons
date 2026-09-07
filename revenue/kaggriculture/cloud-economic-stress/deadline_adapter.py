# SPDX-License-Identifier: Apache-2.0
"""One-second wall-clock guard for an IntegratedSelectedAgent.

The guard preserves the one-controller contract.  Before selection, the only
universally legal fallback is PASS for every observed worker.  Once the producer
has selected an action, that exact action becomes the fallback while the ordered
SELL transform runs.  No parent/controller method is called a second time.
"""
from __future__ import annotations

import copy
import signal
import time


class DeadlineExceeded(Exception):
    pass


def _alarm(_signum, _frame):
    raise DeadlineExceeded("action deadline exhausted")


def legal_pass(observation):
    seat = int(observation["player"])
    hands = observation["farms"][seat].get("hands", [])
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in hands], "market": []}


def terminal_liquidation_fallback(observation, configuration=None):
    """Visible-state final action: place reachable cargo, then sell every shed lot.

    Kaggriculture has nine products and a ten-order market limit, so the fallback
    can liquidate every positive post-unit shed lot without pruning.  Workers not
    already on a shed-access tile PASS; there is no speculative movement.
    """
    obs = observation; cfg = dict(configuration or {})
    seat = int(obs["player"]); farm = obs["farms"][seat]; private = obs["private"]
    board = int(cfg.get("boardSize", len(farm["tiles"])))
    half = board // 2
    access = {(half-1, half-1), (half, half-1), (half-1, half), (half, half)}
    shed = {p: max(0, int(q)) for p, q in private["shed"].items()}
    free = max(0, int(cfg.get("shedCapacity", 100)) - sum(shed.values()))
    positions = [farm["farmer"], *farm.get("hands", [])]
    inventories = private.get("inventories", [])
    units = []
    for index, position in enumerate(positions):
        action = ["PASS"]
        inventory = inventories[index] if index < len(inventories) else {}
        if tuple(position) in access and any(int(q) > 0 for q in inventory.values()):
            # DROP is the engine's multi-product terminal transfer. Preserve the
            # observation's inventory order and capacity clamp exactly.
            action = ["DROP"]
            for product, quantity in inventory.items():
                placed = min(free, max(0, int(quantity)))
                shed[product] = shed.get(product, 0) + placed
                free -= placed
        units.append(action)
    market = [["SELL", product, quantity] for product, quantity in shed.items()
              if quantity > 0]
    maximum = int(cfg.get("maxMarketOrdersPerTurn", 10))
    return {"farmer": units[0], "hands": units[1:], "market": market[:maximum]}


class DeadlineFallbackAgent:
    """Deadline-enforce one already-created IntegratedSelectedAgent.

    SIGALRM is supported by the Linux hosted runner and acts on the main thread.
    A caller on another platform must supply its own process-level timeout rather
    than silently claiming this guard ran.
    """
    def __init__(self, integrated, budget_seconds=1.0, reserve_seconds=0.002,
                 before_transform=None):
        if budget_seconds <= reserve_seconds or reserve_seconds < 0:
            raise ValueError("budget_seconds must exceed non-negative reserve_seconds")
        self.integrated = integrated
        self.budget_seconds = float(budget_seconds)
        self.reserve_seconds = float(reserve_seconds)
        self.before_transform = before_transform
        self.diagnostics = {}

    def act(self, observation, configuration=None):
        obs = copy.deepcopy(dict(observation)); cfg = dict(configuration or {})
        step = obs.get("step")
        if step is None:
            step = int(obs["day"])*int(cfg.get("turnsPerDay", 24)) + int(obs["hour"])
        step = int(step)
        last = int(cfg.get("episodeSteps", 720)) - 2
        fallback = (terminal_liquidation_fallback(obs, cfg)
                    if step == last else legal_pass(obs))
        stage = "production"
        started = time.perf_counter()
        previous = signal.signal(signal.SIGALRM, _alarm)
        signal.setitimer(signal.ITIMER_REAL, self.budget_seconds - self.reserve_seconds)
        try:
            selected = self.integrated.production.act(obs)
            fallback = copy.deepcopy(selected)
            stage = "transform"
            if self.before_transform is not None:
                self.before_transform(obs, cfg, selected)
            output = self.integrated.transform(obs, cfg, selected, fallback_action=selected)
            self.diagnostics = {
                "status": "completed", "fallback_stage": None,
                "elapsed_seconds": time.perf_counter() - started,
                "inner": copy.deepcopy(self.integrated.diagnostics),
            }
            return output
        except DeadlineExceeded:
            self.diagnostics = {
                "status": "deadline_fallback", "fallback_stage": stage,
                "elapsed_seconds": time.perf_counter() - started,
                "inner": copy.deepcopy(getattr(self.integrated, "diagnostics", {})),
            }
            return fallback
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)

    __call__ = act
