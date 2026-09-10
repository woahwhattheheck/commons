# SPDX-License-Identifier: Apache-2.0
"""Fail-closed, one-turn committed-HIRE solvency candidate.

The frozen seller's funded-prefix rule intentionally preserves only acquisitions
that completed in its reference trace.  That is correct for speculative/clipped
purchases, but it cannot protect a HIRE whose missing actor is demonstrably used
by the selected route on the following turns.

This module is additive and dormant until :func:`install` is called.  Its patch:
* looks only one market turn ahead;
* treats a HIRE as committed only when its new hand slot has a later non-PASS
  command before a route decision boundary;
* supports only a current market containing SELLs and a next prefix containing
  SELL/HIRE, so extra cash cannot unlock an intervening purchase and disappear;
* values every current sale at the engine price floor and credits no future sale;
* never adds WHEAT or FERTILIZER liquidation;
* preserves market indexes through frozen_selected.materialize_sales; and
* leaves the original funded-prefix minimum unchanged on every unsupported case.

The separate entrypoint also normalizes emitted hand-command arity to the actors
present in the observation.  That normalization changes no official engine
effect: surplus commands are unbound no-ops and omitted commands are PASS.
"""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
from typing import Any, Iterable, Mapping, Sequence

OPERATING_STOCK = frozenset(("WHEAT", "FERTILIZER"))
_PATCH_FLAG = "_titan_committed_hire_solvency_patch_v1"
_ORIGINAL_ATTR = "_titan_committed_hire_original_funded_minimum_now_v1"


def _cfg(config: Mapping[str, Any] | None, key: str, default: int) -> int:
    try:
        value = int((config or {}).get(key, default))
    except (TypeError, ValueError, AttributeError):
        return default
    return value


def _market(action: Mapping[str, Any] | None, maximum: int) -> list[list[Any]]:
    if not isinstance(action, Mapping):
        return []
    rows = action.get("market", [])
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return []
    result: list[list[Any]] = []
    for row in rows[:maximum]:
        result.append(list(row) if isinstance(row, Sequence) and not isinstance(row, (str, bytes)) else [])
    return result


def _hands(action: Mapping[str, Any] | None) -> Sequence[Any]:
    if not isinstance(action, Mapping):
        return ()
    value = action.get("hands", ())
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else ()


def _nonpass_hand(action: Mapping[str, Any] | None, index: int) -> bool:
    rows = _hands(action)
    if index < 0 or index >= len(rows):
        return False
    row = rows[index]
    return bool(
        isinstance(row, Sequence)
        and not isinstance(row, (str, bytes))
        and row
        and row[0] != "PASS"
    )


def _decision_steps(decisions: Iterable[Any]) -> tuple[int, ...]:
    output = []
    for row in decisions or ():
        try:
            output.append(int(row[0] if isinstance(row, Sequence) else row))
        except (TypeError, ValueError, IndexError):
            continue
    return tuple(sorted(set(output)))


def committed_next_hires(
    route: Sequence[Mapping[str, Any]],
    now: int,
    farm: Mapping[str, Any],
    current_market: Sequence[Any],
    config: Mapping[str, Any] | None,
    decisions: Iterable[Any] = (),
) -> dict[str, Any]:
    """Identify next-turn HIRE rows whose actor slots are actually consumed.

    A later use of hand slot ``k`` closes over every earlier HIRE needed to create
    that slot.  Future route selection is not guessed: a decision checkpoint is a
    hard boundary.  Current-turn HIRE is outside this one-turn proof because it
    makes the next actor baseline candidate-dependent.
    """
    maximum = max(0, _cfg(config, "maxMarketOrdersPerTurn", 10))
    lookahead = max(1, _cfg(config, "committedHireUseLookahead", 8))
    now = int(now)
    next_step = now + 1
    report: dict[str, Any] = {
        "schema": "titan-committed-hire-solvency-v1",
        "status": "inactive",
        "reason": None,
        "observed_step": now,
        "next_step": next_step,
        "lookahead": lookahead,
        "required_keys": (),
        "required_hires": 0,
    }
    if any(row and row[0] == "HIRE" for row in _market({"market": current_market}, maximum)):
        report["reason"] = "current-hire-outside-one-turn-proof"
        return report
    if next_step < 0 or next_step >= len(route):
        report["reason"] = "next-step-outside-route"
        return report

    checkpoints = _decision_steps(decisions)
    hard_end = min(len(route) - 1, next_step + lookahead)
    barrier = next((step for step in checkpoints if now < step <= hard_end), None)
    if barrier is not None:
        hard_end = barrier - 1
        report["decision_barrier"] = barrier
    if hard_end < next_step:
        report["reason"] = "next-step-is-route-decision"
        return report

    orders = _market(route[next_step], maximum)
    hire_indices = [index for index, row in enumerate(orders) if row and row[0] == "HIRE"]
    report["hire_indices"] = tuple(hire_indices)
    if not hire_indices:
        report["reason"] = "no-next-turn-hire"
        return report

    existing = len(farm.get("hands", ()) or ())
    first_use: dict[int, int] = {}
    for ordinal, _index in enumerate(hire_indices, start=1):
        target = existing + ordinal - 1
        use = next(
            (step for step in range(next_step + 1, hard_end + 1)
             if _nonpass_hand(route[step], target)),
            None,
        )
        if use is not None:
            first_use[ordinal] = use
    if not first_use:
        report["reason"] = "new-hand-slots-unused"
        report["hard_end"] = hard_end
        return report

    # A higher slot cannot exist without every earlier HIRE in the same prefix.
    committed_count = max(first_use)
    committed_indices = hire_indices[:committed_count]
    keys = tuple((next_step, index, "HIRE", "") for index in committed_indices)
    report.update(
        status="committed",
        reason="later-nonpass-hand-slot",
        hard_end=hard_end,
        existing_hands=existing,
        committed_hire_indices=tuple(committed_indices),
        first_use_by_ordinal=tuple(sorted(first_use.items())),
        required_keys=keys,
        required_hires=len(keys),
    )
    return report


def _sale_only_cash_floor(
    mechanics: Any,
    farm: Mapping[str, Any],
    private: Mapping[str, Any],
    orders: Sequence[Any],
    maximum: int,
) -> dict[str, Any]:
    """Exact lower cash bound when the complete current prefix is SELL-only."""
    money = int(farm.get("money", 0))
    if money < 0:
        return {"supported": False, "reason": "negative-observed-money"}
    shed = {str(item): max(0, int(quantity)) for item, quantity in dict(private.get("shed", {})).items()}
    floor = max(1, int(getattr(mechanics, "PRICE_FLOOR", 1)))
    sold_by_item: dict[str, int] = {}
    for index, row in enumerate(list(orders)[:maximum]):
        if not row:
            continue
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
            return {"supported": False, "reason": "malformed-current-order", "index": index}
        if row[0] != "SELL" or len(row) < 3 or row[1] not in mechanics.PRODUCTS:
            return {"supported": False, "reason": "current-prefix-not-sell-only", "index": index}
        try:
            requested = max(0, int(row[2]))
        except (TypeError, ValueError):
            return {"supported": False, "reason": "malformed-current-sell", "index": index}
        item = str(row[1])
        sold = min(requested, shed.get(item, 0))
        shed[item] = shed.get(item, 0) - sold
        sold_by_item[item] = sold_by_item.get(item, 0) + sold
        money += sold * floor
    return {
        "supported": True,
        "cash_floor": money,
        "price_floor": floor,
        "sold_units": sum(sold_by_item.values()),
        "sold_by_item": dict(sorted(sold_by_item.items())),
    }


def _next_hire_cost(
    mechanics: Any,
    farm: Mapping[str, Any],
    next_action: Mapping[str, Any],
    next_step: int,
    required_keys: Sequence[Sequence[Any]],
    config: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Cash required for the committed SELL/HIRE prefix, crediting no SELL."""
    maximum = max(0, _cfg(config, "maxMarketOrdersPerTurn", 10))
    required_indices = {int(key[1]) for key in required_keys}
    if not required_indices:
        return {"supported": False, "reason": "no-required-hire"}
    last = max(required_indices)
    rows = _market(next_action, maximum)
    if last >= len(rows):
        return {"supported": False, "reason": "required-hire-outside-market-prefix"}

    hires = int(farm.get("hires_today", 0))
    turns = max(1, _cfg(config, "turnsPerDay", 24))
    if int(next_step) % turns == 0:
        hires = 0
    multiplier = _cfg(config, "farmHandCostMult", 1)
    required_cash = 0
    costs: list[tuple[int, int]] = []
    observed_required: list[int] = []
    for index, row in enumerate(rows[: last + 1]):
        if not row:
            continue
        op = row[0]
        if op == "SELL":
            # Requested future receipts are never cash in this certificate.
            continue
        if op != "HIRE":
            return {
                "supported": False,
                "reason": "next-prefix-not-sell-hire-only",
                "index": index,
                "operation": op,
            }
        cost = int(mechanics._hire_cost(hires, multiplier))
        required_cash += cost
        hires += 1
        costs.append((index, cost))
        if index in required_indices:
            observed_required.append(index)
    if set(observed_required) != required_indices:
        return {"supported": False, "reason": "required-hire-key-mismatch"}
    return {
        "supported": True,
        "required_cash": required_cash,
        "hire_costs": tuple(costs),
        "future_sale_credit": 0,
    }


def committed_hire_reserve(
    frozen: Any,
    obs: Mapping[str, Any],
    config: Mapping[str, Any] | None,
    base: Mapping[str, Any],
    farm: Mapping[str, Any],
    private: Mapping[str, Any],
    route: Sequence[Mapping[str, Any]],
    current: Mapping[str, int],
    targets: Mapping[str, int],
) -> dict[str, Any]:
    """Choose at most one non-operating product to pre-fund next-turn HIREs."""
    now = int(obs.get("step", 0))
    maximum = max(0, _cfg(config, "maxMarketOrdersPerTurn", 10))
    commitment = committed_next_hires(
        route,
        now,
        farm,
        base.get("market", ()),
        config,
        getattr(frozen.parent, "DECISIONS", ()),
    )
    report: dict[str, Any] = {
        "schema": "titan-committed-hire-reserve-v1",
        "status": "inactive",
        "reason": commitment.get("reason"),
        "commitment": commitment,
        "owner_item": None,
        "minimum_now": None,
        "requested_receipt_credit": 0,
        "operating_stock_excluded": tuple(sorted(OPERATING_STOCK)),
    }
    if commitment.get("status") != "committed":
        return report

    cost = _next_hire_cost(
        frozen.m,
        farm,
        route[now + 1],
        now + 1,
        commitment["required_keys"],
        config,
    )
    report["cost"] = cost
    if not cost.get("supported"):
        report["reason"] = cost.get("reason")
        return report

    baseline_orders = frozen.materialize_sales(
        base.get("market", ()), current, private.get("shed", {}), targets, maximum
    )
    baseline = _sale_only_cash_floor(frozen.m, farm, private, baseline_orders, maximum)
    report["baseline"] = baseline
    if not baseline.get("supported"):
        report["reason"] = baseline.get("reason")
        return report
    report["required_cash"] = int(cost["required_cash"])
    if int(baseline["cash_floor"]) >= int(cost["required_cash"]):
        report.update(status="already-funded", reason="baseline-cash-floor")
        return report

    options: list[tuple[tuple[Any, ...], str, int, dict[str, Any], list[list[Any]]]] = []
    prices = dict(obs.get("market", {}).get("prices", {}) or {})
    for raw_item in sorted(targets):
        item = str(raw_item)
        if item in OPERATING_STOCK:
            continue
        available = max(0, int(targets.get(item, 0)))
        start = min(available, max(0, int(current.get(item, 0))))
        for quantity in range(start, available + 1):
            totals = dict(current)
            totals[item] = quantity
            candidate_orders = frozen.materialize_sales(
                base.get("market", ()), totals, private.get("shed", {}), targets, maximum
            )
            candidate = _sale_only_cash_floor(
                frozen.m, farm, private, candidate_orders, maximum
            )
            if not candidate.get("supported"):
                break
            if int(candidate["cash_floor"]) < int(cost["required_cash"]):
                continue
            added = int(candidate["sold_units"]) - int(baseline["sold_units"])
            if added <= 0:
                break
            # Fewer disturbed units dominates; lower visible-value stock breaks ties.
            rank = (added, max(1, int(prices.get(item, 1))), item, quantity)
            options.append((rank, item, quantity, candidate, candidate_orders))
            break

    if not options:
        report["reason"] = "no-safe-non-operating-sale"
        return report
    rank, item, quantity, candidate, candidate_orders = min(options, key=lambda row: row[0])
    report.update(
        status="certified",
        reason="price-floor-current-sale",
        owner_item=item,
        minimum_now=quantity,
        candidate=candidate,
        candidate_market=tuple(tuple(row) for row in candidate_orders),
        added_sale_units=rank[0],
    )
    return report


def install(frozen: Any | None = None) -> Any:
    """Install the candidate into ``frozen_selected`` once and return the module."""
    if frozen is None:
        import frozen_selected as frozen  # type: ignore[no-redef]
    if getattr(frozen, _PATCH_FLAG, False):
        return frozen

    original = frozen.funded_minimum_now

    @wraps(original)
    def patched(
        obs: Mapping[str, Any],
        config: Mapping[str, Any] | None,
        base: Mapping[str, Any],
        farm: Mapping[str, Any],
        private: Mapping[str, Any],
        route: Sequence[Mapping[str, Any]],
        end: int,
        current: Mapping[str, int],
        targets: Mapping[str, int],
        item: str,
        stress_units: int = 32,
    ):
        legacy_minimum, certificate = original(
            obs, config, base, farm, private, route, end,
            current, targets, item, stress_units,
        )
        try:
            reserve = committed_hire_reserve(
                frozen, obs, config, base, farm, private, route, current, targets
            )
        except (TypeError, ValueError, KeyError, IndexError, AttributeError) as exc:
            reserve = {
                "schema": "titan-committed-hire-reserve-v1",
                "status": "inactive",
                "reason": "exception-fail-closed",
                "error": f"{type(exc).__name__}: {exc}"[:300],
                "owner_item": None,
                "minimum_now": None,
            }
        output = int(legacy_minimum)
        if reserve.get("status") == "certified" and reserve.get("owner_item") == item:
            output = max(output, int(reserve["minimum_now"]))
        detail = deepcopy(certificate) if isinstance(certificate, Mapping) else {}
        detail["committed_hire_reserve"] = deepcopy(reserve)
        detail["legacy_minimum_now"] = int(legacy_minimum)
        detail["minimum_now"] = output
        detail["committed_hire_applied"] = output > int(legacy_minimum)
        return output, detail

    setattr(frozen, _ORIGINAL_ATTR, original)
    frozen.funded_minimum_now = patched
    setattr(frozen, _PATCH_FLAG, True)
    return frozen


def uninstall(frozen: Any | None = None) -> Any:
    """Restore the exact pre-patch function; intended for isolated tests."""
    if frozen is None:
        import frozen_selected as frozen  # type: ignore[no-redef]
    original = getattr(frozen, _ORIGINAL_ATTR, None)
    if original is not None:
        frozen.funded_minimum_now = original
        delattr(frozen, _ORIGINAL_ATTR)
    if hasattr(frozen, _PATCH_FLAG):
        delattr(frozen, _PATCH_FLAG)
    return frozen


def normalize_actor_arity(
    action: Mapping[str, Any],
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Return exactly one hand command per currently observable physical hand."""
    output = deepcopy(dict(action))
    try:
        player = int(observation.get("player", 0))
        farm = observation["farms"][player]
        count = len(farm.get("hands", ()) or ())
    except (TypeError, ValueError, KeyError, IndexError, AttributeError):
        return output
    rows = output.get("hands", [])
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        rows = []
    normalized = [
        list(row) if isinstance(row, Sequence) and not isinstance(row, (str, bytes)) and row
        else ["PASS"]
        for row in list(rows)[:count]
    ]
    normalized.extend([["PASS"] for _ in range(count - len(normalized))])
    output["hands"] = normalized
    return output
