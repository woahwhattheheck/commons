#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Policy-inert Gemini E11/O01 salvage certificate for TITAN V4.

This module deliberately does *not* mutate an action.  It upgrades the old
Gemini E11 rival-aware SELL deferral and O01 rival-archetype ideas into public,
source-bound evidence that an existing V4 seller/order owner may consume after
current-native replay.

The public-supply theorem is conservative.  Between two consecutive public
market observations, for one product::

    delta_inventory = own_sell + rival_sell - own_buy - rival_buy - town_consume

Because executed own SELL cannot exceed our requested SELL quantity and executed
own BUY is non-negative::

    rival_sell - rival_buy
      >= current_inventory - previous_inventory
         + town_consume - own_sell_requested_upper_bound

A positive lower bound proves already-realized rival net supply.  A non-positive
bound does *not* prove absence of rival flow.  The deferral certificate therefore
never authorizes a gameplay transform: it only classifies whether an already-
intended SELL is worth replaying through the existing TOWNSELL owner under a
strict set of external custody/funding/queue/horizon guards.

No opponent identity, private stock, private order, inferred archetype, new
controller, release key, default, or Kaggle activation appears here.
"""
from __future__ import annotations

from typing import Any, Mapping


def _json_int(value: Any, label: str) -> int:
    """Require a JSON-style integer; bool must not alias int in evidence logic."""
    if type(value) is not int:
        raise ValueError(f"{label} must be a JSON integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    value = _json_int(value, label)
    if value < 0:
        raise ValueError(f"{label} must be nonnegative")
    return value


def _strict_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be boolean")
    return value


def rival_net_supply_lower_bound(
    *,
    previous_inventory: int,
    current_inventory: int,
    previous_town_consume: int,
    previous_own_sell_requested_upper: int,
) -> int:
    """Conservative lower bound on rival SELL minus rival BUY for one product."""
    previous_inventory = _nonnegative_int(previous_inventory, "previous_inventory")
    current_inventory = _nonnegative_int(current_inventory, "current_inventory")
    previous_town_consume = _nonnegative_int(previous_town_consume, "previous_town_consume")
    previous_own_sell_requested_upper = _nonnegative_int(
        previous_own_sell_requested_upper,
        "previous_own_sell_requested_upper",
    )
    return (
        current_inventory
        - previous_inventory
        + previous_town_consume
        - previous_own_sell_requested_upper
    )


def public_supply_certificate(
    *,
    item: str,
    previous_inventory: int,
    current_inventory: int,
    previous_town_consume: int,
    previous_own_sell_requested_upper: int,
) -> dict[str, Any]:
    """Return a public-only rival-flow certificate for one product transition."""
    if type(item) is not str or not item:
        raise ValueError("item must be a non-empty string")
    lower = rival_net_supply_lower_bound(
        previous_inventory=previous_inventory,
        current_inventory=current_inventory,
        previous_town_consume=previous_town_consume,
        previous_own_sell_requested_upper=previous_own_sell_requested_upper,
    )
    return {
        "schema": "titan.v4.gemini.public-supply-certificate.v1",
        "item": item,
        "rival_net_supply_lower_bound": lower,
        "proved_prior_rival_net_supply": lower > 0,
        "status": (
            "PROVED_PRIOR_RIVAL_NET_SUPPLY"
            if lower > 0
            else "NO_POSITIVE_RIVAL_SUPPLY_PROOF"
        ),
        "limits": [
            "positive lower bound proves only already-realized prior rival net supply",
            "non-positive lower bound does not prove zero rival flow",
            "certificate uses no opponent identity, private inventory, or private orders",
        ],
    }


def sell_deferral_replay_certificate(
    *,
    item: str,
    has_existing_sell: bool,
    town_drain_units: int,
    deterministic_post_drain_premium: int,
    rival_supply_lower_bound: int,
    queue_safe: bool,
    custody_safe: bool,
    financing_safe: bool,
    row_budget_safe: bool,
    horizon_safe: bool,
    evidence_complete: bool = True,
) -> dict[str, Any]:
    """Classify a Gemini-E11-style deferral as replay-worthy or fail closed.

    This function does not return or edit an action.  Even the strongest result,
    ``CANDIDATE_FOR_OWNER_REPLAY``, means only that the existing TOWNSELL/seller
    owner has a source-grounded candidate to test on current-native traces.
    """
    if type(item) is not str or not item:
        raise ValueError("item must be a non-empty string")
    has_existing_sell = _strict_bool(has_existing_sell, "has_existing_sell")
    queue_safe = _strict_bool(queue_safe, "queue_safe")
    custody_safe = _strict_bool(custody_safe, "custody_safe")
    financing_safe = _strict_bool(financing_safe, "financing_safe")
    row_budget_safe = _strict_bool(row_budget_safe, "row_budget_safe")
    horizon_safe = _strict_bool(horizon_safe, "horizon_safe")
    evidence_complete = _strict_bool(evidence_complete, "evidence_complete")
    town_drain_units = _nonnegative_int(town_drain_units, "town_drain_units")
    deterministic_post_drain_premium = _json_int(
        deterministic_post_drain_premium,
        "deterministic_post_drain_premium",
    )
    rival_supply_lower_bound = _json_int(
        rival_supply_lower_bound,
        "rival_supply_lower_bound",
    )

    guards: Mapping[str, bool] = {
        "queue_safe": queue_safe,
        "custody_safe": custody_safe,
        "financing_safe": financing_safe,
        "row_budget_safe": row_budget_safe,
        "horizon_safe": horizon_safe,
    }

    if not evidence_complete:
        status = "FAIL_CLOSED_MISSING_EVIDENCE"
    elif not has_existing_sell:
        status = "NO_EXISTING_SELL_TO_RETIME"
    elif not all(guards.values()):
        status = "FAIL_CLOSED_OWNER_CONSTRAINT"
    elif town_drain_units <= 0 or deterministic_post_drain_premium <= 0:
        status = "NO_DETERMINISTIC_POST_DRAIN_PREMIUM"
    elif rival_supply_lower_bound > 0:
        # TOWNSELL's deterministic theorem assumes zero intervening rival flow.
        # Prior proved supply does not prove future supply, but it is sufficient
        # reason to refuse a generic Gemini-E11 deferral and demand replay.
        status = "VETO_PROVED_PRIOR_RIVAL_SUPPLY"
    else:
        status = "CANDIDATE_FOR_OWNER_REPLAY"

    return {
        "schema": "titan.v4.gemini.sell-deferral-replay-certificate.v1",
        "item": item,
        "status": status,
        "policy_authorized": False,
        "has_existing_sell": has_existing_sell,
        "town_drain_units": town_drain_units,
        "deterministic_post_drain_premium": deterministic_post_drain_premium,
        "rival_supply_lower_bound": rival_supply_lower_bound,
        "proved_prior_rival_net_supply": rival_supply_lower_bound > 0,
        "guards": dict(guards),
        "limits": [
            "never creates, deletes, reorders, resizes, or delays a market row",
            "candidate status requires current-native owner replay before any policy use",
            "non-positive rival lower bound is not evidence that the rival is inactive",
            "opponent-ID/archetype classification is intentionally excluded",
        ],
    }
