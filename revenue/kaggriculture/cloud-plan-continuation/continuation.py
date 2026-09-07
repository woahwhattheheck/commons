# SPDX-License-Identifier: Apache-2.0
"""Optional continuation-aware consumer of T15's existing WholePlanSelector.

This adapter changes no optimizer, controller, probability, or source freeze.
It checks the selected plan's remaining schedule against current caller facts.
An emitted order is NOT a fill receipt; the caller still owns real feasibility.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

Validator = Callable[[dict[str, Any], dict[str, Any]], bool | None]


class ContinuationPlanSelector:
    """Wrap one fresh T15 selector for one actor/match; use it exclusively.

    ``continuation_feasible(remaining_plan, context)`` must return exactly True
    for a feasible continuation, False for infeasible, or None for unknown.
    Its inputs are detached copies. The context contains the current supplied
    observation, post-unit shed, reservations, configuration and lot metadata.
    The validator must use current caller-visible facts, not future truth.

    Only original ``feasible`` validates every constituent at commitment. This
    adapter additionally validates the selected remaining plan at every call.
    It neither infers fill receipts nor guarantees the supplied fallback legal.
    """

    def __init__(self, selector: Any):
        self.selector = selector
        self.last_decision: dict[str, Any] = {'reason': 'not_called'}
        self._key: Any = None
        self._last_step: int | None = None
        self._emitted: set[int] = set()

    @property
    def draws(self) -> int:
        return self.selector.draws

    @property
    def active(self) -> dict[str, Any] | None:
        return deepcopy(self.selector.active)

    @staticmethod
    def _step(observation: Mapping[str, Any], configuration: Mapping[str, Any]) -> int:
        if 'step' in observation:
            return int(observation['step'])
        return (int(observation.get('day', 0))
                * int(configuration.get('turnsPerDay', 24))
                + int(observation.get('hour', 0)))

    def _abort(self, reason: str, now: int, base_action: Any,
               **details: Any) -> Any:
        active = self.selector.active
        key = active['key'] if active is not None else self._key
        if active is not None:
            self.selector.completed.add(key)
            self.selector.active = None
        self.last_decision = {'reason': reason, 'key': key, 'step': now,
                              'fallback_preserved': True, **details}
        self.selector.last_decision = deepcopy(self.last_decision)
        self._key, self._last_step, self._emitted = None, None, set()
        return deepcopy(base_action)

    @staticmethod
    def _check(active: dict[str, Any], now: int, observation: Mapping[str, Any],
               configuration: Mapping[str, Any], post_unit_shed: Any,
               reservations: Any, validator: Validator | None) -> str | None:
        if validator is None:
            return 'continuation_unknown'
        remaining = deepcopy(active['plan'])
        remaining['sales'] = [[t, q] for t, q in remaining['sales'] if t >= now]
        context = deepcopy({
            'key': active['key'], 'item': active['item'], 'slot': active['slot'],
            'original_quantity': active['quantity'],
            'remaining_quantity': sum(q for t, q in remaining['sales']),
            'now': now, 'end': active['end'], 'decision_step': active['now'],
            'plan_index': active['plan_index'],
            'observation': observation, 'configuration': configuration,
            'post_unit_shed': post_unit_shed, 'reservations': reservations or {},
        })
        try:
            verdict = validator(remaining, context)
        except Exception:
            # Do not expose arbitrary callback exception text in public traces.
            return 'continuation_error'
        if verdict is True:
            return None
        if verdict is False:
            return 'continuation_infeasible'
        if verdict is None:
            return 'continuation_unknown'
        return 'continuation_invalid_verdict'

    def transform(self, observation: Mapping[str, Any], configuration: Any,
                  base_action: Any, *, continuation_feasible: Validator | None,
                  window: Any = None, post_unit_shed: Any = None,
                  reservations: Any = None, feasible: Any = None,
                  mode: str = 'mixed') -> Any:
        """Return one action; preserve fallback and retire invalidated keys.

        A repeat at the same decision step emits the same committed choice,
        subject to current feasibility, without another random draw. Missing
        a positive-quantity due date or going backward abandons the old window.
        Skipping dates with no due sale is allowed. No catch-up sale is invented.
        """
        cfg = configuration or {}
        now = self._step(observation, cfg)
        before = self.selector.active
        checked_key = object()  # None is a valid caller key.
        if before is not None:
            key = before['key']
            if self._key == key and self._last_step is not None and now < self._last_step:
                return self._abort('decision_time_reversed', now, base_action)
            emitted = self._emitted if self._key == key else set()
            missing = [t for t, q in before['plan']['sales']
                       if q > 0 and t < now and t not in emitted]
            if missing:
                return self._abort('due_step_not_emitted', now, base_action,
                                   missing_steps=missing)
            if any(q > 0 and t >= now for t, q in before['plan']['sales']):
                reason = self._check(before, now, observation, cfg, post_unit_shed,
                                     reservations, continuation_feasible)
                if reason:
                    return self._abort(reason, now, base_action)
                checked_key = key
        elif continuation_feasible is None:
            self.last_decision = {'reason': 'continuation_unknown', 'step': now,
                                  'fallback_preserved': True}
            return deepcopy(base_action)

        out = self.selector.transform(
            observation, configuration, base_action, window=window,
            post_unit_shed=post_unit_shed, reservations=reservations,
            feasible=feasible, mode=mode)
        active = self.selector.active
        if active is not None:
            key = active['key']
            if checked_key != key:
                reason = self._check(active, now, observation, cfg, post_unit_shed,
                                     reservations, continuation_feasible)
                if reason:
                    return self._abort(reason, now, base_action)
            if self._key != key:
                self._key, self._last_step, self._emitted = key, None, set()
            self._last_step = now
            decision = self.selector.last_decision
            if decision.get('reason') == 'executed' and decision.get('due', 0) > 0:
                self._emitted.add(now)
        else:
            self._key, self._last_step, self._emitted = None, None, set()
            if self.selector.last_decision.get('reason') == 'commitment_aborted':
                out = deepcopy(base_action)
        self.last_decision = deepcopy(self.selector.last_decision)
        return out
