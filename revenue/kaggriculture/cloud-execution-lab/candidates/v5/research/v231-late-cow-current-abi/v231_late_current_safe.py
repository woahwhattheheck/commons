# SPDX-License-Identifier: Apache-2.0
"""Retry-safe current-ABI envelope for submitted V231 late-COW recovery.

The historical router deliberately reset V231 state on ``step <= last`` because it
owned the whole producer call.  At a current selected-action seam, however, the
same public callback can be retried with either identical or refreshed selected
action bytes.  Reusing post-attempt state mixes two attempts; resetting to empty
forgets authority accumulated on earlier committed callbacks.

This wrapper makes one public ``(player, step)`` a transaction: capture the exact
pre-step V231 state once, and restore that snapshot before every same-step retry.
The base donor-semantic adapter then recomputes from one coherent preimage.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from v231_late_current import V231LateCurrentABI, _is_int


@dataclass
class V231LateCurrentABISafe:
    """Transactional retry envelope around :class:`V231LateCurrentABI`.

    This class does not add a producer/controller call and does not change the
    donor decision theorem.  It only owns retry custody for the adapter's private
    state.  Forward callbacks commit the prior attempt's post-state.  A same-step
    retry always starts from the same captured pre-step state.  A rewind clears
    candidate state and begins a new epoch, matching the historical reset intent.
    """

    enabled: bool = False
    cap: int = 4
    _base: V231LateCurrentABI = field(init=False, repr=False)
    _transactions: dict[int, dict[str, Any]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        # Base construction owns the exact-bool/cap validation contract.
        self._base = V231LateCurrentABI(enabled=self.enabled, cap=self.cap)

    @property
    def states(self) -> dict[int, dict[str, Any]]:
        """Detached snapshot for diagnostics/tests; callers cannot mutate custody."""
        return copy.deepcopy(self._base._states)

    def transform(self, observation: Any, selected: Any) -> Any:
        # Disabled identity belongs to the base and must not create retry state.
        if not self.enabled:
            return self._base.transform(observation, selected)

        if not isinstance(observation, dict):
            return self._base.transform(observation, selected)
        step = observation.get("step")
        seat = observation.get("player")
        if not _is_int(step) or not _is_int(seat) or seat < 0:
            return self._base.transform(observation, selected)

        prior = self._transactions.get(seat)
        if prior is not None and step < prior["step"]:
            # Episode rewind/reset: historical V231 intentionally drops memory.
            self._transactions.pop(seat, None)
            self._base._states.pop(seat, None)
            prior = None

        if prior is not None and step == prior["step"]:
            # Recompute every retry from the exact same pre-step candidate state.
            if prior["pre_exists"]:
                self._base._states[seat] = copy.deepcopy(prior["pre_state"])
            else:
                self._base._states.pop(seat, None)
        else:
            # A later callback commits the previous attempt.  Capture that committed
            # state as the immutable preimage for this new public step.
            exists = seat in self._base._states
            self._transactions[seat] = {
                "step": step,
                "pre_exists": exists,
                "pre_state": copy.deepcopy(self._base._states.get(seat)) if exists else None,
            }

        return self._base.transform(observation, selected)
