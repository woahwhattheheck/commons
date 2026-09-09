# SPDX-License-Identifier: Apache-2.0
"""Contracts for the TITAN active-prefix seed dependency adapter."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import inspect
import os
from pathlib import Path
import random
import sys
from types import ModuleType, SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
for path in (HERE, LAB, LAB.parent / "cloud-runtime-pulse", LAB.parent / "cloud-quickstep"):
    if path.is_dir() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

import seed_prefix_dependency as prefix


try:
    import scheduler as _scheduler_probe  # noqa: F401
except ModuleNotFoundError:
    # Source-independent installer contracts exercise the selected-post-unit
    # path, so post_units must never be called. Supply only the two names the
    # exact current method imports; repository CI resolves the real module.
    scheduler_stub = ModuleType("scheduler")
    scheduler_stub.m = object()

    def _unexpected_post_units(*_args, **_kwargs):
        raise AssertionError("selected_post_units snapshot should avoid post_units")

    scheduler_stub.post_units = _unexpected_post_units
    sys.modules["scheduler"] = scheduler_stub


def _selected(market):
    return {"farmer": ["PASS"], "hands": [], "market": deepcopy(market)}


def _proposal(action, edits):
    result = deepcopy(action)
    for slot, order in edits.items():
        result["market"][slot] = deepcopy(order)
    return result


def _observation(step=600):
    farm = {
        "money": 10,
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
        "farmer": [4, 4],
        "hands": [],
        "tiles": [[None] * 10 for _ in range(10)],
    }
    private = {"seeds": {"WHEAT": 0}, "shed": {}, "inventories": [{}]}
    return {
        "step": step,
        "player": 0,
        "farms": [deepcopy(farm), deepcopy(farm)],
        "private": deepcopy(private),
    }


class _Budget:
    def __init__(self, proposed):
        self.proposed = deepcopy(proposed)
        self.calls = 0

    def apply(self, *_args, **_kwargs):
        self.calls += 1
        return deepcopy(self.proposed)


class _Funding:
    def __init__(self, *, chosen="baseline", raises=False):
        self.chosen = chosen
        self.raises = raises
        self.calls = 0

    def select_seed_queue(
        self, _mechanics, _post, baseline, proposed, _configuration, **_kwargs
    ):
        self.calls += 1
        if self.raises:
            raise RuntimeError("selector sentinel")
        chosen = proposed if self.chosen == "proposed" else baseline
        return deepcopy(chosen), {
            "status": "certified" if self.chosen == "proposed" else "not_certified",
            "reason": "dummy",
        }


class _DummyAgent:
    """Small current-dispatch double used to exercise the instance wrapper."""

    def __init__(self, proposed, funding=None):
        self.features = SimpleNamespace(seed=True, funding=True)
        self.consumer = SimpleNamespace(
            selected_post_units=(
                {"money": 10, "hires_today": 0, "unlocked_quadrants": ["NW"]},
                {"seeds": {"WHEAT": 0}},
            )
        )
        self.controller = SimpleNamespace(cur="MAIN")
        self.spatial = None
        self.seed_budget = _Budget(proposed)
        self.funding_module = funding or _Funding()
        self.diagnostics = {}

    def _seed_selected(self, obs, cfg, selected):
        if not self.features.seed or not any(
            o and o[0] == "BUY_SEED" for o in selected["market"]
        ):
            return selected
        proposed = self.seed_budget.apply(
            selected,
            self.consumer.selected_post_units[1]["seeds"],
            int(obs["step"]),
            self.controller.cur,
            int(cfg.get("maxMarketOrdersPerTurn", 10)),
            extra_requests={},
        )
        edits = [
            i
            for i, (a, b) in enumerate(
                zip(selected["market"], proposed["market"])
            )
            if a != b
        ]
        dependent = any(
            o and o[0] in ("HIRE", "BUY_LAND", "BUY_PRODUCT", "BUY_ANIMAL")
            for i in edits
            for o in selected["market"][i + 1 :]
        )
        if not dependent:
            return proposed
        if not self.features.funding:
            return selected
        result, report = self.funding_module.select_seed_queue(
            None, obs, deepcopy(selected), deepcopy(proposed), deepcopy(cfg)
        )
        self.diagnostics["seed_funding"] = report
        return result


def _dummy_hash(agent):
    return hashlib.sha256(
        inspect.getsource(agent._seed_selected.__func__).encode("utf-8")
    ).hexdigest()
