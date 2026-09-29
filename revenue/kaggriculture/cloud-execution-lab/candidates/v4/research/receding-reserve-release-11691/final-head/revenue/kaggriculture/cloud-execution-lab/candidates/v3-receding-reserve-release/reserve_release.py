# SPDX-License-Identifier: Apache-2.0
"""Receding-horizon release of Arlene's deliberate one-slot shed reserve.

The inherited seller intentionally targets 99/100 occupancy so the next unit
stage can deposit one item before market.  This candidate preserves that policy
unless the exact represented next stage proves the spare slot cannot be used:

* the current unbounded unit projection is exactly the real capacity;
* Titan's dynamic selected-unit producer is explicitly idle;
* a next action exists before the terminal boundary and no route checkpoint
  can replace it;
* no next actor action is DROP or PLACE;
* both executable market prefixes are structurally valid and contain no
  incoming product or animal purchase; and
* the inherited fixed 24-turn day semantics do not cross a day boundary.

Only then is the inherited feasibility calculation repeated with a synthetic
capacity of ``real_capacity + 1``.  Because the inherited predicate reserves
one slot, that changes its later bound from ``real_capacity - 1`` to exactly
``real_capacity``.  A separate current-unit overflow guard keeps the real
pre-market boundary unchanged.

This is an isolated, default-off score candidate.  It does not claim that the
99/100 policy is a bug, and it never mutates the canonical archive or config.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import scheduler as scheduling

_ORIGINAL_RECEIPT_PROFILE = scheduling.SellScheduler.receipt_profile
_PATCHED = False


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed != value:
        return None
    return parsed


def _active_market(action: Any, maximum: int) -> list[Any] | None:
    if not isinstance(action, Mapping):
        return None
    market = action.get("market", [])
    if not isinstance(market, list):
        return None
    return market[:maximum]


def _contains_incoming_shed_buy(action: Any, maximum: int) -> bool | None:
    market = _active_market(action, maximum)
    if market is None:
        return None
    for order in market:
        if order == []:
            continue
        if not isinstance(order, list) or not order:
            return None
        if order[0] in ("BUY_PRODUCT", "BUY_ANIMAL"):
            return True
    return False


def _unit_actions(action: Any) -> list[Any] | None:
    if not isinstance(action, Mapping):
        return None
    farmer = action.get("farmer", ["PASS"])
    hands = action.get("hands", [])
    if not isinstance(farmer, list) or not farmer or not isinstance(hands, list):
        return None
    actions = [farmer, *hands]
    if any(not isinstance(row, list) or not row for row in actions):
        return None
    return actions


def reserve_release_certificate(
    owner: scheduling.SellScheduler,
    obs: Mapping[str, Any],
    base: Mapping[str, Any],
    config: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Prove that carrying exactly a full shed is safe until the next replan.

    The agent is invoked again before the next represented unit stage.  A full
    shed is therefore safe for one receding-horizon step only when that stage
    cannot add shed load.  Unknown or malformed state fails closed.
    """
    report: dict[str, Any] = {
        "eligible": False,
        "reason": "malformed_input",
        "next_step": None,
        "capacity": None,
        "current_requested_total": None,
    }
    if not isinstance(obs, Mapping) or not isinstance(base, Mapping):
        return report

    cfg = dict(config or {})
    now = _integer(obs.get("step"))
    capacity = _integer(cfg.get("shedCapacity", 100))
    turns_per_day = _integer(cfg.get("turnsPerDay", 24))
    episode_steps = _integer(cfg.get("episodeSteps", 720))
    maximum = _integer(cfg.get("maxMarketOrdersPerTurn", 10))
    if (
        now is None
        or capacity is None
        or capacity < 1
        or turns_per_day is None
        or turns_per_day < 1
        or episode_steps is None
        or episode_steps < 2
        or maximum is None
        or maximum < 1
    ):
        return report
    # The inherited scheduler simulates route days with literal 24-turn
    # boundaries.  A non-24 configuration is outside the proven semantic
    # boundary, so preserve the predecessor policy rather than extrapolate.
    if turns_per_day != 24:
        report["reason"] = "unsupported_turns_per_day"
        return report

    next_step = now + 1
    last = episode_steps - 2
    report.update(next_step=next_step, capacity=capacity)
    if getattr(owner, "joint_producer_busy", None) is not False:
        report["reason"] = "dynamic_unit_producer_busy_or_unbound"
        return report
    if next_step > last:
        report["reason"] = "no_next_executable_step"
        return report

    # Keep the reserve across EOD/day-start transitions.  The inherited route
    # can replace hands and perform automatic deposits there; this candidate
    # intentionally does not model that larger state transition.
    if now // turns_per_day != next_step // turns_per_day:
        report["reason"] = "day_boundary"
        return report

    try:
        checkpoints = tuple(int(row[0]) for row in scheduling.parent.DECISIONS)
    except (AttributeError, TypeError, ValueError, IndexError):
        report["reason"] = "unknown_route_checkpoints"
        return report
    if next_step in checkpoints:
        report["reason"] = "route_checkpoint"
        return report

    try:
        route = owner.controller.R[owner.controller.cur]
        next_action = route[next_step]
    except (AttributeError, KeyError, IndexError, TypeError):
        report["reason"] = "unrepresented_next_action"
        return report

    actions = _unit_actions(next_action)
    if actions is None:
        report["reason"] = "malformed_next_unit_action"
        return report
    for action in actions:
        if action[0] in ("DROP", "PLACE"):
            report["reason"] = "next_unit_can_deposit"
            return report

    for name, action in (("current", base), ("next", next_action)):
        incoming = _contains_incoming_shed_buy(action, maximum)
        if incoming is None:
            report["reason"] = f"malformed_{name}_market"
            return report
        if incoming:
            report["reason"] = f"{name}_market_can_deposit"
            return report

    try:
        _, requested = scheduling.post_units(
            obs, base, cfg, shed_capacity=10**6
        )
        requested_total = sum(
            int(value) for value in requested["shed"].values()
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        report["reason"] = "current_projection_failed"
        return report
    report["current_requested_total"] = requested_total
    if requested_total > capacity:
        report["reason"] = "current_unit_overflow"
        return report
    if requested_total != capacity:
        report["reason"] = "current_not_exact_full"
        return report

    report.update(eligible=True, reason="next_pre_market_growth_zero")
    return report


def guarded_receipt_profile(
    self: scheduling.SellScheduler,
    obs: Mapping[str, Any],
    base: Mapping[str, Any],
    farm: Mapping[str, Any],
    private: Mapping[str, Any],
    end: int,
    item: str,
    config: Mapping[str, Any] | None,
):
    """Return inherited feasibility plus one narrowly certified exact-full case."""
    baseline = _ORIGINAL_RECEIPT_PROFILE(
        self, obs, base, farm, private, end, item, config
    )
    certificate = reserve_release_certificate(self, obs, base, config)
    diagnostics = getattr(self, "diagnostics", None)
    if isinstance(diagnostics, dict):
        diagnostics.setdefault("reserve_release", []).append(deepcopy(certificate))
    if not certificate["eligible"]:
        return baseline

    cfg = dict(config or {})
    capacity = int(certificate["capacity"])
    relaxed_cfg = dict(cfg)
    relaxed_cfg["shedCapacity"] = capacity + 1
    relaxed = _ORIGINAL_RECEIPT_PROFILE(
        self, obs, base, farm, private, end, item, relaxed_cfg
    )

    def feasible(plan):
        # Preserve every plan accepted by the deliberate 99/100 policy.  The
        # candidate only adds exact-full plans certified safe for this step.
        return baseline(plan) or relaxed(plan)

    return feasible


def install() -> None:
    """Install once, refusing to overwrite an unknown peer patch."""
    global _PATCHED
    current = scheduling.SellScheduler.receipt_profile
    if current is guarded_receipt_profile:
        _PATCHED = True
        return
    if current is not _ORIGINAL_RECEIPT_PROFILE:
        raise RuntimeError("SellScheduler.receipt_profile already has another owner")
    scheduling.SellScheduler.receipt_profile = guarded_receipt_profile
    _PATCHED = True


def restore() -> None:
    """Restore the exact predecessor method for tests or paired controls."""
    global _PATCHED
    current = scheduling.SellScheduler.receipt_profile
    if current is guarded_receipt_profile:
        scheduling.SellScheduler.receipt_profile = _ORIGINAL_RECEIPT_PROFILE
    elif current is not _ORIGINAL_RECEIPT_PROFILE:
        raise RuntimeError("refusing to restore over an unknown peer patch")
    _PATCHED = False


def installed() -> bool:
    return scheduling.SellScheduler.receipt_profile is guarded_receipt_profile


def predecessor_receipt_profile():
    """Expose the exact captured predecessor for discriminating tests."""
    return _ORIGINAL_RECEIPT_PROFILE
