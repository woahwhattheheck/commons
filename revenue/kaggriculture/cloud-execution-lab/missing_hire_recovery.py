# SPDX-License-Identifier: Apache-2.0
"""Bounded recovery for a route whose next unit stage needs one missing hand.

The adapter never changes the route and never speculates about future income. It
may replace one physically inert market row (an empty row or a zero-unit SELL),
or append within the current market limit, with one HIRE. A caller-supplied
prefix executor must prove that the inserted order completes from the exact
post-unit state. A separate payback certificate must then admit its represented,
realized value before the action is returned.
"""
from __future__ import annotations

import copy
from typing import Any, Callable, Mapping, Sequence


def _is_nonpass(action: Any) -> bool:
    return isinstance(action, list) and bool(action) and action[0] != "PASS"


def _required_hands(action: Mapping[str, Any]) -> int:
    """Highest one-based hand slot with represented non-PASS work."""
    required = 0
    hands = action.get("hands", [])
    if not isinstance(hands, list):
        return 0
    for index, command in enumerate(hands, start=1):
        if _is_nonpass(command):
            required = index
    return required


def _idle_market_row(row: Any) -> bool:
    """Rows whose replacement cannot remove a requested physical transaction."""
    if not row:
        return True
    return (
        isinstance(row, list)
        and len(row) == 3
        and row[0] == "SELL"
        and isinstance(row[2], int)
        and not isinstance(row[2], bool)
        and row[2] == 0
    )


def recover_missing_hire(
    observation: Mapping[str, Any],
    configuration: Mapping[str, Any] | None,
    selected_action: Mapping[str, Any],
    *,
    route: Sequence[Mapping[str, Any]],
    certify_prefix: Callable[[list, int], Mapping[str, Any]],
    certify_payback: (
        Callable[[list, list, int, Mapping[str, Any]], Mapping[str, Any]] | None
    ) = None,
) -> tuple[dict, dict]:
    """Insert one executable HIRE when next-turn route work has one missing hand.

    ``certify_prefix(queue, stop_index)`` must execute the exact current market
    prefix from the caller's exact post-unit state and return the same compact
    shape as ``frozen_selected._market_prefix_state``: ``outcomes`` keyed by
    order index, optional ``unsupported_index``, and terminal ``money``.

    ``certify_payback(baseline_queue, candidate_queue, inserted_index,
    hire_outcome)`` is mandatory for mutation. It must return a mapping whose
    ``admit`` member is exactly ``True``; every other result fails closed.
    """
    out = copy.deepcopy(dict(selected_action))
    report = {
        "changed": False,
        "reason": "not_evaluated",
        "scope": (
            "one-turn route-cardinality recovery; prefix-certified HIRE plus "
            "mandatory realized-payback certificate; no route mutation"
        ),
    }
    cfg = dict(configuration or {})
    try:
        step = observation.get("step")
        if step is None:
            step = int(observation["day"]) * int(cfg.get("turnsPerDay", 24)) + int(observation["hour"])
        step = int(step)
        player = int(observation["player"])
        active = len(observation["farms"][player].get("hands", []))
        limit = int(cfg.get("maxMarketOrdersPerTurn", 10))
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        report.update(reason="invalid_observation", error=f"{type(exc).__name__}: {exc}"[:300])
        return out, report

    next_step = step + 1
    if limit <= 0 or next_step >= len(route):
        report.update(reason="no_represented_next_step", step=step, next_step=next_step)
        return out, report
    next_action = route[next_step]
    if not isinstance(next_action, Mapping):
        report.update(reason="unsupported_route_row", step=step, next_step=next_step)
        return out, report
    required = _required_hands(next_action)
    queue = out.get("market", [])
    if not isinstance(queue, list):
        report.update(reason="unsupported_market_queue", step=step, next_step=next_step)
        return out, report
    if len(queue) > limit:
        report.update(reason="over_limit_market_queue", step=step, next_step=next_step,
                      active_hands=active, required_hands=required, market_limit=limit)
        return out, report

    try:
        baseline = certify_prefix(copy.deepcopy(queue), max(-1, len(queue) - 1))
    except Exception as exc:
        report.update(reason="baseline_certificate_error", step=step, next_step=next_step,
                      error=f"{type(exc).__name__}: {exc}"[:300])
        return out, report
    outcomes = baseline.get("outcomes", {}) if isinstance(baseline, Mapping) else {}
    funded_existing = 0
    for index, order in enumerate(queue[:limit]):
        if isinstance(order, list) and order and order[0] == "HIRE":
            outcome = outcomes.get(index, {}) if isinstance(outcomes, Mapping) else {}
            funded_existing += int(outcome.get("completed", 0) == 1)
    available_next = active + funded_existing
    report.update(step=step, next_step=next_step, active_hands=active,
                  funded_existing_hires=funded_existing, available_next_hands=available_next,
                  required_hands=required, route_id_work_slots=len(next_action.get("hands", [])),
                  baseline_unsupported_index=(baseline.get("unsupported_index")
                                              if isinstance(baseline, Mapping) else None))
    if required <= available_next:
        report["reason"] = "route_capacity_satisfied"
        return out, report
    deficit = required - available_next
    report["missing_hands"] = deficit
    if deficit != 1:
        report["reason"] = "not_single_hire_recoverable"
        return out, report

    candidates = [index for index, row in enumerate(queue[:limit]) if _idle_market_row(row)]
    if len(queue) < limit:
        candidates.append(len(queue))
    if not candidates:
        report["reason"] = "no_inert_market_slot"
        return out, report

    failures = []
    for slot in candidates:
        candidate = copy.deepcopy(queue)
        replaced = None
        if slot == len(candidate):
            candidate.append(["HIRE"])
        else:
            replaced = copy.deepcopy(candidate[slot])
            candidate[slot] = ["HIRE"]
        try:
            certificate = certify_prefix(candidate, slot)
        except Exception as exc:
            failures.append({"slot": slot, "reason": "certificate_error",
                             "error": f"{type(exc).__name__}: {exc}"[:200]})
            continue
        if not isinstance(certificate, Mapping):
            failures.append({"slot": slot, "reason": "malformed_certificate"})
            continue
        barrier = certificate.get("unsupported_index")
        outcome = certificate.get("outcomes", {}).get(slot, {})
        completed = int(outcome.get("completed", 0) == 1)
        if barrier is not None and int(barrier) < slot:
            failures.append({"slot": slot, "reason": "unsupported_prefix_barrier",
                             "barrier_index": int(barrier)})
            continue
        if not completed:
            failures.append({"slot": slot, "reason": "hire_not_funded",
                             "remaining_cash": certificate.get("money")})
            continue
        if certify_payback is None:
            failures.append({"slot": slot, "reason": "payback_certificate_required"})
            continue
        try:
            payback = certify_payback(
                copy.deepcopy(queue), copy.deepcopy(candidate), slot,
                copy.deepcopy(outcome))
        except Exception as exc:
            failures.append({"slot": slot, "reason": "payback_certificate_error",
                             "error": f"{type(exc).__name__}: {exc}"[:200]})
            continue
        if not isinstance(payback, Mapping):
            failures.append({"slot": slot, "reason": "malformed_payback_certificate"})
            continue
        if payback.get("admit") is not True:
            failures.append({"slot": slot, "reason": "payback_rejected",
                             "payback_reason": payback.get("reason"),
                             "payback_certificate": copy.deepcopy(dict(payback))})
            continue
        out["market"] = candidate
        report.update(
            changed=True,
            reason="inserted_prefix_and_payback_certified_hire",
            inserted_index=slot,
            replaced_order=replaced,
            certified_remaining_cash=certificate.get("money"),
            hire_cost=outcome.get("cost_per_unit"),
            available_next_hands=available_next + 1,
            certificate_outcome=copy.deepcopy(outcome),
            payback_certificate=copy.deepcopy(dict(payback)),
            candidate_failures=failures,
        )
        return out, report

    report.update(reason="no_admissible_inert_slot", candidate_failures=failures)
    return out, report
