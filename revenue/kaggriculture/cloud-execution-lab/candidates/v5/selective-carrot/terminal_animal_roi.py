# SPDX-License-Identifier: Apache-2.0
"""Bounded terminal animal-purchase filter for the TITAN V5 production-v3 carrier.

This module is intentionally inert unless a materialized treatment entry calls
``filter_action``.  It observes only the current callback step and returned
action.  Unknown/malformed shapes fail to identity.
"""
from __future__ import annotations

_ANIMALS = frozenset(("GOOSE", "COW", "SHEEP"))


def _plain_positive_int(value) -> bool:
    return type(value) is int and value > 0


def _animal_buy(order) -> bool:
    return (
        isinstance(order, (list, tuple))
        and len(order) == 3
        and order[0] == "BUY_ANIMAL"
        and order[1] in _ANIMALS
        and _plain_positive_int(order[2])
    )


def filter_action(observation, action, *, min_step: int = 718):
    """Drop valid ``BUY_ANIMAL`` rows at/after ``min_step``; otherwise identity.

    The function never mutates the parent action.  It deliberately refuses to
    infer a step from day/hour or to reinterpret malformed market rows: if the
    outer production-v3 callback has not supplied an authoritative integer step,
    or any shape needed for the edit is uncertain, the exact parent object is
    returned unchanged.
    """
    if type(min_step) is not int or not 0 <= min_step <= 718:
        return action
    if not isinstance(observation, dict) or type(observation.get("step")) is not int:
        return action
    if observation["step"] < min_step:
        return action
    if not isinstance(action, dict):
        return action
    market = action.get("market")
    if not isinstance(market, list):
        return action

    filtered = [order for order in market if not _animal_buy(order)]
    if len(filtered) == len(market):
        return action

    changed = dict(action)
    changed["market"] = filtered
    return changed
