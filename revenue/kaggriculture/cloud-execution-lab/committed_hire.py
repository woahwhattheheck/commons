# SPDX-License-Identifier: Apache-2.0
"""Exact observed-fill reconciliation for a partially fulfilled HIRE prefix.

The producer may request several HIRE orders while the engine can afford only a
prefix. A following route can still contain commands for the missing hand. This
module remembers only a HIRE target that was actually returned, compares it
with the next public observation, and retries one missing hand only while that
same route is visibly issuing a non-PASS command for the absent index.

No sale receipt is credited. When cash is exactly one configured hire-cost unit
short, paid acquisitions are replaced by inert zero-quantity sales for that turn
so the observed cash cannot be consumed before the retry. Existing sales and
unit actions are preserved.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


_PAID = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL"}
_PASS = ["PASS"]
_INERT = ["SELL", "WHEAT", 0]


def _fib(n: int) -> int:
    a, b = 1, 1
    for _ in range(max(0, n)):
        a, b = b, a + b
    return a


def hire_cost(hires_today: int, multiplier: int = 1) -> int:
    """Mirror the official engine's 1, 1, 2, 3, 5... daily HIRE cost."""
    return max(0, int(multiplier)) * _fib(max(0, int(hires_today)))


def _op(order: Any) -> str | None:
    return order[0] if isinstance(order, list) and order and isinstance(order[0], str) else None


def _positive_hires(market: Any) -> int:
    if not isinstance(market, list):
        return 0
    return sum(1 for row in market if _op(row) == "HIRE")


def _nonpass_missing_commands(action: dict[str, Any], actual_hands: int, target: int) -> list[int]:
    hands = action.get("hands", [])
    if not isinstance(hands, list):
        return []
    stop = min(len(hands), target)
    return [i for i in range(actual_hands, stop) if hands[i] != _PASS]


@dataclass
class HireIntent:
    target_hands: int
    route_id: str
    origin_step: int
    last_step: int


class CommittedHireReconciler:
    """Stateful, fail-closed reconciler for one producer-owned HIRE target."""

    def __init__(self) -> None:
        self.intent: HireIntent | None = None
        self.last_report: dict[str, Any] = {"changed": False, "reason": "cold"}

    @staticmethod
    def _farm(obs: dict[str, Any]) -> dict[str, Any]:
        return obs["farms"][int(obs["player"])]

    @staticmethod
    def _route_key(route_id: Any) -> str:
        return repr(route_id)

    def reset(self, reason: str = "reset") -> None:
        self.intent = None
        self.last_report = {"changed": False, "reason": reason, "pending": False}

    def transform(
        self,
        obs: dict[str, Any],
        cfg: dict[str, Any],
        selected: dict[str, Any],
        *,
        route_id: Any,
        commit: bool,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return a final-boundary action and an auditable decision report.

        ``commit`` must be true only for a producer action that will actually be
        returned. Deadline fallbacks are byte-preserved and cannot create,
        advance, or clear intent.
        """
        original = deepcopy(selected)
        if not commit:
            report = {
                "changed": False,
                "reason": "uncommitted_fallback",
                "pending": self.intent is not None,
            }
            self.last_report = report
            return original, report

        step = int(obs["step"])
        farm = self._farm(obs)
        actual = len(farm.get("hands", []))
        route = self._route_key(route_id)
        turns = max(1, int(cfg.get("turnsPerDay", 24)))
        limit = max(1, int(cfg.get("maxMarketOrdersPerTurn", 10)))
        mult = max(0, int(cfg.get("farmHandCostMult", 1)))
        money = int(farm.get("money", 0))
        hires_today = int(farm.get("hires_today", 0))

        intent = self.intent
        reconciliation = "none"
        if intent is not None:
            if step < intent.last_step:
                intent = None
                reconciliation = "step_rewind"
            elif route != intent.route_id:
                intent = None
                reconciliation = "route_changed"
            elif step - intent.origin_step > turns:
                intent = None
                reconciliation = "expired"
            elif step > intent.last_step and actual >= intent.target_hands:
                intent = None
                reconciliation = "target_observed"
            elif step > intent.last_step:
                intent.last_step = step
                reconciliation = "underfilled_observed"

        result = deepcopy(selected)
        changed = False
        reason = reconciliation
        inserted_at: int | None = None
        replaced_at: int | None = None
        suppressed: list[int] = []
        missing_commands: list[int] = []
        cost: int | None = None

        if intent is not None and actual < intent.target_hands:
            missing_commands = _nonpass_missing_commands(result, actual, intent.target_hands)
            if missing_commands:
                cost = hire_cost(hires_today, mult)
                market = result.get("market", [])
                if not isinstance(market, list):
                    market = []
                    result["market"] = market
                existing = [i for i, row in enumerate(market) if _op(row) == "HIRE"]
                if money >= cost:
                    if existing:
                        first = existing[0]
                        before_paid = next(
                            (i for i, row in enumerate(market) if _op(row) in _PAID),
                            len(market),
                        )
                        if first > before_paid:
                            row = market.pop(first)
                            market.insert(before_paid, row)
                            changed = True
                            inserted_at = before_paid
                            reason = "moved_existing_hire_before_paid"
                        else:
                            reason = "existing_hire_certified"
                    elif len(market) < limit:
                        before_paid = next(
                            (i for i, row in enumerate(market) if _op(row) in _PAID),
                            len(market),
                        )
                        market.insert(before_paid, ["HIRE"])
                        changed = True
                        inserted_at = before_paid
                        reason = "inserted_missing_hire"
                    else:
                        replace = next(
                            (i for i, row in enumerate(market) if _op(row) in _PAID),
                            None,
                        )
                        if replace is not None:
                            market[replace] = ["HIRE"]
                            changed = True
                            replaced_at = replace
                            reason = "replaced_paid_order_with_hire"
                        else:
                            reason = "full_sale_queue"
                elif 0 < cost - money <= max(1, mult):
                    # Do not assume a sale will fill. Preserve sales and remove
                    # only positive-cost acquisitions while a missing worker is
                    # demonstrably being commanded by the same route.
                    for i, row in enumerate(market):
                        if _op(row) in _PAID:
                            market[i] = list(_INERT)
                            suppressed.append(i)
                    changed = bool(suppressed)
                    reason = "reserved_observed_cash" if changed else "awaiting_cash"
                else:
                    reason = "cash_gap_too_large"
            else:
                reason = "no_nonpass_missing_command"

        # Bind a target only to HIRE rows in the exact final action. A retry of
        # an existing pending target never increases that target a second time.
        hires_returned = _positive_hires(result.get("market", []))
        if intent is None and hires_returned:
            intent = HireIntent(
                target_hands=actual + hires_returned,
                route_id=route,
                origin_step=step,
                last_step=step,
            )
            if reason in (
                "none",
                "target_observed",
                "route_changed",
                "expired",
                "step_rewind",
            ):
                reason = "recorded_returned_hire_target"
        elif intent is not None:
            if hires_returned:
                intent.target_hands = max(intent.target_hands, actual + hires_returned)
            intent.last_step = max(intent.last_step, step)

        self.intent = intent
        report = {
            "changed": changed,
            "reason": reason or "unchanged",
            "pending": intent is not None,
            "step": step,
            "route_id": route,
            "actual_hands": actual,
            "target_hands": None if intent is None else intent.target_hands,
            "origin_step": None if intent is None else intent.origin_step,
            "missing_command_indices": missing_commands,
            "hire_cost": cost,
            "money": money,
            "hires_today": hires_today,
            "inserted_at": inserted_at,
            "replaced_at": replaced_at,
            "suppressed_paid_indices": suppressed,
            "hires_returned": hires_returned,
        }
        self.last_report = report
        return result, report
