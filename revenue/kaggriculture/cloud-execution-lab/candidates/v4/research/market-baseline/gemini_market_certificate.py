#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Policy-inert Gemini E11/O01 salvage certificate for TITAN V4.

This module deliberately does *not* mutate an action. It upgrades the old
Gemini E11 rival-aware SELL deferral and O01 rival-archetype ideas into public,
source-bound evidence that an existing V4 seller/order owner may consume after
current-native replay.

The public-supply theorem is conservative. Between two consecutive public
market observations, for one product::

    delta_inventory = own_sell + rival_sell - own_buy - rival_buy - town_consume

Because executed own SELL cannot exceed our requested SELL quantity and executed
own BUY is non-negative::

    rival_sell - rival_buy
      >= current_inventory - previous_inventory
         + town_consume - own_sell_requested_upper_bound

A positive lower bound proves already-realized rival net supply. A non-positive
bound does *not* prove absence of rival flow.

The low-level algebra helpers accept already-custodied scalar inputs. For live
use, ``source_bound_public_supply_certificate`` is the stronger surface: it
requires adjacent public observations, derives the exact prior-callback town
drain from the canonical town oracle, and derives our SELL-request upper bound
from the official parser over the exact executable market prefix. This prevents
callers from manufacturing rival-flow proof by overstating town drain or
understating our own executable SELL request.

No opponent identity, private stock, private order, inferred archetype, new
controller, release key, default, or Kaggle activation appears here.
"""
from __future__ import annotations

from typing import Any, Mapping

from town_wheat_timing import town_demand_units

DEFAULT_MARKET_CAP = 10


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


def _observation_step(observation: Any, label: str) -> int:
    if not isinstance(observation, dict):
        raise ValueError(f"{label} must be an object")
    return _nonnegative_int(observation.get("step"), f"{label}.step")


def _public_inventory(observation: Any, item: str, label: str) -> int:
    if not isinstance(observation, dict):
        raise ValueError(f"{label} must be an object")
    market = observation.get("market")
    inventory = market.get("inventory") if isinstance(market, dict) else None
    if not isinstance(inventory, dict) or item not in inventory:
        raise ValueError(f"{label} public {item} inventory required")
    return _nonnegative_int(inventory[item], f"{label}.market.inventory.{item}")


def _market_cap(config: Any) -> int:
    """Mirror the official engine's max(1, int(maxMarketOrdersPerTurn))."""
    raw = DEFAULT_MARKET_CAP
    if isinstance(config, dict):
        raw = config.get("maxMarketOrdersPerTurn", DEFAULT_MARKET_CAP)
    else:
        getter = getattr(config, "get", None)
        if callable(getter):
            raw = getter("maxMarketOrdersPerTurn", DEFAULT_MARKET_CAP)
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        raise ValueError("maxMarketOrdersPerTurn must match official int coercion") from None


def executable_own_sell_requested_upper(
    engine: Any,
    previous_own_action: Any,
    *,
    item: str,
    config: Any = None,
) -> int:
    """Upper-bound our executed SELL units from the official executable prefix.

    The engine's parser intentionally accepts values coercible by ``int``. We
    therefore consume the engine parser directly instead of reimplementing a
    narrower grammar that could miss an executable own SELL and overstate rival
    supply. Rows beyond the official market cap are inert and do not contribute.
    """
    products = getattr(engine, "PRODUCTS", None)
    parser = getattr(engine, "_parse_order", None)
    if not isinstance(products, (list, tuple)) or item not in products:
        raise ValueError(f"unknown product: {item}")
    if not callable(parser):
        raise ValueError("official market parser required")

    action = previous_own_action if isinstance(previous_own_action, dict) else {}
    market = action.get("market", [])
    rows = list(market) if isinstance(market, list) else []
    rows = rows[: _market_cap(config)]

    upper = 0
    for row in rows:
        parsed = parser(row)
        if not isinstance(parsed, dict):
            continue
        if parsed.get("type") != "SELL" or parsed.get("item") != item:
            continue
        remaining = parsed.get("remaining")
        if type(remaining) is not int or remaining <= 0:
            raise ValueError("official SELL parser returned malformed remaining quantity")
        upper += remaining
    return upper


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


def source_bound_public_supply_certificate(
    engine: Any,
    *,
    item: str,
    previous_observation: Any,
    current_observation: Any,
    previous_own_action: Any,
    config: Any = None,
) -> dict[str, Any]:
    """Bind the public rival-flow theorem to one exact official transition.

    ``previous_observation`` is the state before callback ``s`` and
    ``current_observation`` is the state recorded after that callback at
    ``s+1``. The prior town state is deliberately used: end-of-day may unlock a
    shop after the callback's town-consumption phase, so using current shops at
    a day boundary would overstate the just-completed drain.
    """
    if type(item) is not str or not item:
        raise ValueError("item must be a non-empty string")
    products = getattr(engine, "PRODUCTS", None)
    if not isinstance(products, (list, tuple)) or item not in products:
        raise ValueError(f"unknown product: {item}")

    previous_step = _observation_step(previous_observation, "previous_observation")
    current_step = _observation_step(current_observation, "current_observation")
    if current_step != previous_step + 1:
        raise ValueError("public observations must be adjacent callback states")

    previous_inventory = _public_inventory(previous_observation, item, "previous_observation")
    current_inventory = _public_inventory(current_observation, item, "current_observation")
    previous_town = previous_observation.get("town")
    shops = previous_town.get("unlocked_shops", []) if isinstance(previous_town, dict) else []
    town_consume = town_demand_units(engine, previous_step, shops, config, item)
    own_sell_upper = executable_own_sell_requested_upper(
        engine,
        previous_own_action,
        item=item,
        config=config,
    )

    cert = public_supply_certificate(
        item=item,
        previous_inventory=previous_inventory,
        current_inventory=current_inventory,
        previous_town_consume=town_consume,
        previous_own_sell_requested_upper=own_sell_upper,
    )
    return {
        **cert,
        "schema": "titan.v4.gemini.source-bound-public-supply-certificate.v1",
        "previous_step": previous_step,
        "current_step": current_step,
        "previous_inventory": previous_inventory,
        "current_inventory": current_inventory,
        "derived_town_consume": town_consume,
        "derived_own_sell_requested_upper": own_sell_upper,
        "market_order_cap": _market_cap(config),
        "input_custody": "ADJACENT_PUBLIC_STATE_PLUS_OFFICIAL_MARKET_PREFIX",
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

    This function does not return or edit an action. Even the strongest result,
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
