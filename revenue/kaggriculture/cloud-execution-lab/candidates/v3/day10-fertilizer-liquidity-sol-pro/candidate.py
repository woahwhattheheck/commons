# SPDX-License-Identifier: Apache-2.0
"""Dependency-complete development entrypoint for the TITAN V3 liquidity arm.

For hosted panels this file is copied beside the canonical archive's ``main.py``
and complete runtime closure.  It keeps the canonical entrypoint, factory,
deadline, reset, and fallback code byte-exact and wraps only each newly created
runtime instance's final market boundary.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

from candidate_runtime import install_final_boundary
from fertilizer_liquidity import LiquiditySettings

HERE = Path(__file__).resolve().parent
BASE_MAIN = HERE / "main.py"
if not BASE_MAIN.is_file():
    raise RuntimeError("candidate must be materialized beside canonical main.py")

SETTINGS = LiquiditySettings(
    start_day=8,
    end_day=10,
    reserve_units=24,
    minimum_unit_price=55,
    max_units_per_turn=64,
    liquidity_target=12_000,
    rival_stress_units=32,
)

_SPEC = importlib.util.spec_from_file_location("_titan_day10_canonical_main", BASE_MAIN)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load canonical main.py")
_BASE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _BASE
_SPEC.loader.exec_module(_BASE)
_ORIGINAL_FACTORY = _BASE._new_instance


def _post_units(observation, selected, configuration):
    from scheduler import post_units

    return post_units(observation, selected, configuration)


def _quote(item, inventory, params):
    from scheduler import m

    return m.market_price(item, inventory, params)


def _new_instance(root, feature_data):
    instance = _ORIGINAL_FACTORY(root, feature_data)
    return install_final_boundary(
        instance,
        post_units=_post_units,
        quote=_quote,
        settings=SETTINGS,
    )


_BASE._new_instance = _new_instance


def agent(observation, configuration=None):
    return _BASE.agent(observation, configuration)


__all__ = ["agent"]
