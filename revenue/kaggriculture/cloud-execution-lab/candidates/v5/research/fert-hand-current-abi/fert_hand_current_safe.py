# SPDX-License-Identifier: Apache-2.0
"""Retry-safe public surface for the V3.1 fertilizer-hand current-ABI adapter.

The base adapter deliberately caches a same-step candidate decision so repeated
agent calls are deterministic.  A refreshed parent route is stronger authority,
though: if the current parent action or its authenticated remaining-day route
now contains a HIRE, replaying the cached candidate HIRE would violate the
single-producer / no-double-hire theorem.

This tiny public surface closes that boundary without rewriting the recovered
mechanism.  New consumers should import ``FertHandCurrentABI`` from this module.
"""
from __future__ import annotations

from typing import Any, Mapping

from fert_hand_current import (
    FertHandCurrentABI as _BaseFertHandCurrentABI,
    _future_hire,
    _identity,
)


class FertHandCurrentABI(_BaseFertHandCurrentABI):
    """Base adapter plus fail-closed same-step parent-HIRE revalidation."""

    @staticmethod
    def _retire_cached_hire(state: Any) -> None:
        """Permanently retire a candidate HIRE after refreshed parent conflict."""
        state.pending = None
        state.hire_step = None
        state.hire_buy = 0
        state.want = 0
        state.tried = True

    def _consider_hire(
        self,
        observation: Mapping[str, Any],
        selected: Mapping[str, Any],
        state: Any,
        rest: list[Mapping[str, Any]],
    ):
        # Only the retry path needs an extra preflight.  Fresh decisions retain
        # the base adapter's full economic, route, capacity and shape gates.
        parsed = observation.get("step") if isinstance(observation, Mapping) else None
        retry = type(parsed) is int and state.hire_step == parsed
        if not retry:
            return super()._consider_hire(observation, selected, state, rest)

        market = selected.get("market")
        if not isinstance(market, list):
            self._retire_cached_hire(state)
            return _identity(selected, "malformed_market_retry")
        if any(order and not isinstance(order, list) for order in market):
            self._retire_cached_hire(state)
            return _identity(selected, "malformed_market_retry")
        if any(
            isinstance(order, list) and order and order[0] == "HIRE"
            for order in market
        ):
            self._retire_cached_hire(state)
            return _identity(selected, "parent_hire_collision_retry")
        if _future_hire(rest):
            self._retire_cached_hire(state)
            return _identity(selected, "future_parent_hire_retry")

        return super()._consider_hire(observation, selected, state, rest)
