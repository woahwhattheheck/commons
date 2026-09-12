# SPDX-License-Identifier: Apache-2.0
"""Retry-safe public current ABI for submitted V231 late-COW recovery.

The donor core in :mod:`v231_late_current` deliberately preserves the historical
whole-router ``step <= last`` reset.  That reset is unsafe at a selected-action
seam where one public callback can be retried.  This envelope owns only retry
custody: one immutable pre-step candidate snapshot per player/step, with no
producer/controller call and no change to the late-V231 decision theorem.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from v231_late_current import V231LateCurrentABI, _shape


@dataclass
class V231LateCurrentABISafe:
    """Transactional envelope around :class:`V231LateCurrentABI`.

    Identical valid retries return the exact recorded action/post-state.  Changed
    valid retries recompute from the same immutable pre-step candidate state.
    Malformed retries are detached identity and cannot touch candidate or retry
    custody.  A rewind clears the candidate epoch before the donor core runs.
    """

    enabled: bool = False
    cap: int = 4
    _base: V231LateCurrentABI = field(init=False, repr=False)
    _transactions: dict[int, dict[str, Any]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        # The donor core owns exact-bool/cap validation.
        self._base = V231LateCurrentABI(enabled=self.enabled, cap=self.cap)

    @property
    def states(self) -> dict[int, dict[str, Any]]:
        """Detached candidate-state snapshot for diagnostics/tests."""
        return copy.deepcopy(self._base._states)

    def _restore(self, seat: int, exists: bool, state: Any) -> None:
        if exists:
            self._base._states[seat] = copy.deepcopy(state)
        else:
            self._base._states.pop(seat, None)

    def transform(self, observation: Any, selected: Any) -> Any:
        if not self.enabled:
            return self._base.transform(observation, selected)

        # Validate the complete current envelope before transaction mutation.
        # This is stronger than the historical whole-router boundary and is what
        # makes a malformed same-step retry truly detached.
        if not _shape(observation, selected):
            return copy.deepcopy(selected)

        step = observation["step"]
        seat = observation["player"]
        prior = self._transactions.get(seat)

        if prior is not None and step < prior["step"]:
            # True rewind/reset: begin a fresh V231 epoch.
            self._transactions.pop(seat, None)
            self._base._states.pop(seat, None)
            prior = None

        if prior is not None and step == prior["step"]:
            if (
                observation == prior["observation"]
                and selected == prior["selected"]
            ):
                # Exact replay: do not re-enter the donor core.  Re-establish the
                # recorded post-state so outside test/diagnostic reads are stable.
                self._restore(
                    seat,
                    prior["post_exists"],
                    prior["post_state"],
                )
                return copy.deepcopy(prior["result"])

            # Refreshed valid evidence for the same public callback.  Discard the
            # abandoned attempt and recompute from the original pre-step authority.
            self._restore(seat, prior["pre_exists"], prior["pre_state"])
            transaction = {
                "step": step,
                "pre_exists": prior["pre_exists"],
                "pre_state": copy.deepcopy(prior["pre_state"]),
            }
        else:
            # A forward callback commits the prior post-state.  Capture that exact
            # state once as this step's immutable transaction preimage.
            exists = seat in self._base._states
            transaction = {
                "step": step,
                "pre_exists": exists,
                "pre_state": (
                    copy.deepcopy(self._base._states[seat]) if exists else None
                ),
            }

        result = self._base.transform(observation, selected)
        transaction.update(
            observation=copy.deepcopy(observation),
            selected=copy.deepcopy(selected),
            result=copy.deepcopy(result),
            post_exists=seat in self._base._states,
            post_state=(
                copy.deepcopy(self._base._states[seat])
                if seat in self._base._states
                else None
            ),
        )
        self._transactions[seat] = transaction
        return result

    act = transform
