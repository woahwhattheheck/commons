# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for exact joint transition oracle contracts."""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import unittest

import joint_transition as oracle

ENGINE = None
ENGINE_SOURCE = None
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
ANIMALS = ["GOOSE", "COW", "SHEEP"]
CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
CASE_COUNT = 0


def load_full_reference(path: Path):
    """Import the whole exact official module with only its framework import stubbed."""
    package = types.ModuleType("kaggle_environments")
    package.__path__ = []
    utils = types.ModuleType("kaggle_environments.utils")
    utils.resolve_episode_seed = lambda env: 0
    saved_package = sys.modules.get("kaggle_environments")
    saved_utils = sys.modules.get("kaggle_environments.utils")
    try:
        sys.modules["kaggle_environments"] = package
        sys.modules["kaggle_environments.utils"] = utils
        spec = importlib.util.spec_from_file_location("exact_kaggriculture_reference", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot_load_exact_reference")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if saved_package is None:
            sys.modules.pop("kaggle_environments", None)
        else:
            sys.modules["kaggle_environments"] = saved_package
        if saved_utils is None:
            sys.modules.pop("kaggle_environments.utils", None)
        else:
            sys.modules["kaggle_environments.utils"] = saved_utils


def farm(cash=0, *, hands=0, hires_today=0, unlocked=None, board_size=10):
    half = board_size // 2
    tiles = [
        [None if y < half and x < half else "LOCKED" for x in range(board_size)]
        for y in range(board_size)
    ]
    return {
        "money": float(cash),
        "tiles": tiles,
        "farmer": [half - 1, half - 1],
        "hands": [[half, half - 1] for _ in range(hands)],
        "unlocked_quadrants": list(unlocked or ["NW"]),
        "hires_today": hires_today,
    }


def private(*, hands=0, shed=None, seeds=None, carried=None):
    value = {
        "shed": {item: 0 for item in PRODUCTS + ANIMALS},
        "seeds": {item: 0 for item in CROPS},
        "inventories": [{} for _ in range(hands + 1)],
    }
    value["shed"].update(shed or {})
    value["seeds"].update(seeds or {})
    for index, inventory in enumerate(carried or []):
        value["inventories"][index].update(inventory)
    return value


def market(inventory=None):
    value = {
        "inventory": {item: ENGINE.MARKET_PARAMS[item]["I0"] for item in PRODUCTS},
        "prices": {item: ENGINE.MARKET_PARAMS[item]["base"] for item in PRODUCTS},
    }
    value["inventory"].update(inventory or {})
    ENGINE._refresh_prices(value)
    return value


def action(queue=None, *, farmer_action=None, hands=None):
    return {
        "farmer": copy.deepcopy(farmer_action or ["PASS"]),
        "hands": copy.deepcopy(hands or []),
        "market": copy.deepcopy(queue or []),
    }


def config(**updates):
    value = {
        "boardSize": 10,
        "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1,
        "shedCapacity": 100,
        "townShopSellInterval": 4,
        "townCenterSellInterval": 24,
    }
    value.update(updates)
    return value


def payload(*, seat=0, own_cash=0, rival_cash=0, own_shed=None, rival_shed=None,
            baseline=None, candidate=None, rival=None, inventory=None, shops=None,
            step=17, own_hands=0, own_hires=0, configuration=None, checkpoints=None):
    farms = [farm(rival_cash), farm(rival_cash)]
    privates = [private(shed=rival_shed), private(shed=rival_shed)]
    farms[seat] = farm(own_cash, hands=own_hands, hires_today=own_hires)
    privates[seat] = private(hands=own_hands, shed=own_shed)
    rival_action = action(rival)
    baseline_actions = [copy.deepcopy(rival_action), copy.deepcopy(rival_action)]
    candidate_actions = [copy.deepcopy(rival_action), copy.deepcopy(rival_action)]
    baseline_actions[seat] = action(baseline)
    candidate_actions[seat] = action(candidate)
    return {
        "step": step,
        "seat": seat,
        "farms": farms,
        "privates": privates,
        "market": market(inventory),
        "town": {"unlocked_shops": list(shops or [])},
        "baseline_actions": baseline_actions,
        "candidate_actions": candidate_actions,
        "configuration": config(**(configuration or {})),
        "checkpoints": copy.deepcopy(checkpoints or []),
    }


def compare(value, **overrides):
    global CASE_COUNT
    value = copy.deepcopy(value)
    value.update(overrides)
    before = copy.deepcopy(value)
    result = oracle.compare_joint_transition(ENGINE, **value)
    if result["status"] == "complete_conditional":
        CASE_COUNT += 1
    if "deadline" not in overrides:
        assert value == before, "oracle mutated caller input"
    return result


