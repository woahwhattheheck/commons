# SPDX-License-Identifier: Apache-2.0
"""Current-HIRE admission with a full post-HIRE replay certificate.

SOL-CROSSWIND's source-pinned PR #11975 established the narrow ordering theorem
consumed here: the official interpreter applies every actor already present in
the observation before processing market orders, and HIRE appends a new hand
and inventory afterward.  That theorem is necessary but not sufficient for a
multi-step route exchange: from the next turn onward the new actor participates
in unit order, and HIRE spawn itself observes positions after the changed
current unit stage.

This module therefore keeps the merged exact ``p07_atomic`` pair primitive as
the first certificate, then replays the complete own-player unit/HIRE sequence
through the proposal horizon with the dynamically appended actors present.  A
proposal is published only when the full final farm and private state remain
identical.  The complete current market queue is also bound at the final
returned-action guard; a later consumer cannot retain the pair while changing
the HIRE premise.
"""
from __future__ import annotations

from copy import deepcopy
import time
from typing import Any, Mapping, MutableMapping, Sequence

MAX_OFFICIAL_MARKET_PREFIX = 10


def _blank(order: Any) -> bool:
    """Match the official parser's inert current-order carriers."""
    return order is None or order == []


def classify_current_hire(
    selected: Mapping,
    raw: Mapping,
    configuration: Mapping,
    existing_actor_count: int,
) -> dict[str, Any]:
    """Return a fail-closed admission receipt for a current market row."""
    selected_market = selected.get("market", [])
    raw_market = raw.get("market", [])
    if type(selected_market) is not list or type(raw_market) is not list:
        return {"admitted": False, "reason": "malformed_current_market"}
    if selected_market != raw_market:
        return {"admitted": False, "reason": "current_market_source_mismatch"}

    configured = configuration.get("maxMarketOrdersPerTurn", 10)
    # bool is an int subclass.  Accepting it would silently reinterpret the
    # active prefix; all noncanonical carriers are outside this theorem.
    if (
        type(configured) is not int
        or configured < 1
        or configured > MAX_OFFICIAL_MARKET_PREFIX
    ):
        return {
            "admitted": False,
            "reason": "unsupported_market_prefix_config",
        }

    active = selected_market[:configured]
    suffix = selected_market[configured:]
    if any(not _blank(order) for order in suffix):
        return {
            "admitted": False,
            "reason": "inactive_suffix_market_boundary",
        }

    active_hires = 0
    for order in active:
        if _blank(order):
            continue
        if type(order) is not list or order != ["HIRE"]:
            return {
                "admitted": False,
                "reason": "current_non_hire_market_boundary",
            }
        active_hires += 1
    if active_hires == 0:
        return {
            "admitted": False,
            "reason": "current_market_without_executable_hire",
        }

    selected_hands = selected.get("hands", [])
    raw_hands = raw.get("hands", [])
    if type(selected_hands) is not list or type(raw_hands) is not list:
        return {"admitted": False, "reason": "malformed_current_hands"}
    existing_hands = existing_actor_count - 1
    if existing_hands < 0:
        return {"admitted": False, "reason": "invalid_existing_actor_count"}
    if selected_hands[existing_hands:] != raw_hands[existing_hands:]:
        return {
            "admitted": False,
            "reason": "new_actor_tail_source_mismatch",
        }
    extra_actions = max(0, len(selected_hands) - existing_hands)
    if extra_actions > active_hires:
        return {"admitted": False, "reason": "excess_new_actor_actions"}

    return {
        "admitted": True,
        "reason": "certified_current_hire_existing_actors",
        "active_hires": active_hires,
        "extra_actor_actions": extra_actions,
        "executable_prefix": configured,
        "existing_actor_count": existing_actor_count,
    }


def _strict_replay_configuration(configuration: Mapping) -> dict[str, int]:
    values = {
        "turnsPerDay": configuration.get("turnsPerDay", 24),
        "shedCapacity": configuration.get("shedCapacity", 100),
        "farmHandCostMult": configuration.get("farmHandCostMult", 1),
        "maxMarketOrdersPerTurn": configuration.get("maxMarketOrdersPerTurn", 10),
    }
    if any(type(value) is not int for value in values.values()):
        raise ValueError("non-integer replay configuration")
    if values["turnsPerDay"] <= 0:
        raise ValueError("turnsPerDay must be positive")
    if values["shedCapacity"] < 0:
        raise ValueError("shedCapacity must be nonnegative")
    if values["farmHandCostMult"] < 0:
        raise ValueError("farmHandCostMult must be nonnegative")
    if not 1 <= values["maxMarketOrdersPerTurn"] <= MAX_OFFICIAL_MARKET_PREFIX:
        raise ValueError("unsupported market prefix")
    return values


def _apply_unit_stage(
    module: Any,
    mechanics: Any,
    farm: MutableMapping,
    private: MutableMapping,
    row: Mapping,
    step: int,
    configuration: Mapping[str, int],
) -> None:
    """Replay the official own-player unit stage, including atomic PLANT demand."""
    count = 1 + len(farm.get("hands", []))
    actions = [module._normal_action(row, worker) for worker in range(count)]
    demand: dict[str, int] = {}
    for action in actions:
        if len(action) >= 2 and action[0] == "PLANT":
            demand[action[1]] = demand.get(action[1], 0) + 1
    seeds = private.get("seeds", {})
    blocked = {
        crop for crop, quantity in demand.items() if quantity > seeds.get(crop, 0)
    }
    board = len(farm.get("tiles", []))
    if board <= 0:
        raise ValueError("replay farm has no board")
    for worker, action in enumerate(actions):
        if len(action) >= 2 and action[0] == "PLANT" and action[1] in blocked:
            action = ["PASS"]
        mechanics._apply_unit_action(
            farm,
            private,
            worker,
            action,
            board,
            step // configuration["turnsPerDay"],
            configuration["turnsPerDay"],
            configuration["shedCapacity"],
        )


def _apply_current_hires(
    mechanics: Any,
    farm: MutableMapping,
    private: MutableMapping,
    market: Sequence,
    configuration: Mapping[str, int],
) -> None:
    """Replay only the certified current active-prefix HIRE orders."""
    do_hire = getattr(mechanics, "_do_hire", None)
    if not callable(do_hire):
        raise ValueError("mechanics lacks exact HIRE primitive")
    board = len(farm.get("tiles", []))
    for order in market[: configuration["maxMarketOrdersPerTurn"]]:
        if _blank(order):
            continue
        if order != ["HIRE"]:
            raise ValueError("uncertified order reached HIRE replay")
        do_hire(
            farm,
            private,
            board,
            configuration["farmHandCostMult"],
        )


def _simulate_full_window(
    module: Any,
    mechanics: Any,
    observation: Mapping,
    rows: Mapping[int, Mapping],
    start: int,
    end: int,
    configuration: Mapping,
) -> tuple[Mapping, Mapping]:
    cfg = _strict_replay_configuration(configuration)
    player = int(observation["player"])
    farm = deepcopy(observation["farms"][player])
    private = deepcopy(observation["private"])
    for step in range(start, end + 1):
        row = rows[step]
        if not isinstance(row, Mapping):
            raise TypeError(f"replay row {step} is not a mapping")
        _apply_unit_stage(module, mechanics, farm, private, row, step, cfg)
        market = row.get("market", [])
        if step == start:
            _apply_current_hires(mechanics, farm, private, market, cfg)
        elif market:
            # The merged exact pair primitive must still own every future market
            # boundary.  Reaching this line means its source contract drifted.
            raise ValueError("future market escaped exact pair boundary")
        mechanics._decay_plants(farm, step)
    return farm, private


def full_post_hire_certificate(
    module: Any,
    mechanics: Any,
    observation: Mapping,
    baseline_rows: Mapping[int, Mapping],
    candidate_rows: Mapping[int, Mapping],
    start: int,
    end: int,
    configuration: Mapping,
) -> dict[str, Any]:
    """Require exact final state with dynamic post-HIRE actors in unit order."""
    baseline_farm, baseline_private = _simulate_full_window(
        module,
        mechanics,
        observation,
        baseline_rows,
        start,
        end,
        configuration,
    )
    candidate_farm, candidate_private = _simulate_full_window(
        module,
        mechanics,
        observation,
        candidate_rows,
        start,
        end,
        configuration,
    )
    farm_equal = baseline_farm == candidate_farm
    private_equal = baseline_private == candidate_private
    baseline_hands = len(baseline_farm.get("hands", []))
    candidate_hands = len(candidate_farm.get("hands", []))
    return {
        "checked": True,
        "accepted": farm_equal and private_equal,
        "reason": (
            "full_post_hire_state_equal"
            if farm_equal and private_equal
            else "full_post_hire_state_mismatch"
        ),
        "start_step": start,
        "end_step": end,
        "farm_equal": farm_equal,
        "private_equal": private_equal,
        "baseline_actor_count": 1 + baseline_hands,
        "candidate_actor_count": 1 + candidate_hands,
        "hands_equal": baseline_farm.get("hands", [])
        == candidate_farm.get("hands", []),
        "money_equal": baseline_farm.get("money") == candidate_farm.get("money"),
        "inventories_equal": baseline_private.get("inventories", [])
        == candidate_private.get("inventories", []),
        "shed_equal": baseline_private.get("shed", {})
        == candidate_private.get("shed", {}),
        "tiles_equal": baseline_farm.get("tiles", [])
        == candidate_farm.get("tiles", []),
    }


def _restore_exact_field(target: MutableMapping, source: Mapping, field: str) -> None:
    if field in source:
        target[field] = deepcopy(source[field])
    else:
        target.pop(field, None)


def _restore_existing_tail(
    target: MutableMapping,
    source: Mapping,
    existing_actor_count: int,
) -> None:
    existing_hands = existing_actor_count - 1
    target_hands = target.get("hands", [])
    source_hands = source.get("hands", [])
    if type(target_hands) is not list or type(source_hands) is not list:
        raise TypeError("hands carrier changed after current-HIRE certification")
    target_hands[existing_hands:] = deepcopy(source_hands[existing_hands:])
    target["hands"] = target_hands


def _record_rejection(
    module: Any,
    spatial: Any,
    observation: Mapping,
    receipt: Mapping[str, Any],
    started: float,
) -> None:
    report = getattr(module, "_report", None)
    if callable(report):
        report(
            spatial,
            observation,
            changed=False,
            reason=str(receipt["reason"]),
            started=started,
            current_hire_window=dict(receipt),
        )
        return
    spatial.p07_report = {
        "phase": "proposal",
        "step": int(observation["step"]),
        "player": int(observation["player"]),
        "changed": False,
        "reason": str(receipt["reason"]),
        "current_hire_window": dict(receipt),
    }


def _append_window_record(
    module: Any,
    spatial: Any,
    observation: Mapping,
    receipt: Mapping[str, Any],
) -> None:
    """Emit exactly one final proposal record for a current-HIRE attempt."""
    report = getattr(spatial, "p07_report", None)
    if isinstance(report, MutableMapping):
        report["current_hire_window"] = dict(receipt)
        final = dict(report)
    else:
        final = {
            "phase": "proposal",
            "step": int(observation["step"]),
            "player": int(observation["player"]),
            "changed": False,
            "reason": str(receipt.get("reason", "current_hire_unknown")),
            "current_hire_window": dict(receipt),
        }
    append = getattr(module, "_append_log", None)
    if callable(append):
        append(final)


def _spatial_snapshot(spatial: Any) -> dict[str, Any]:
    return {
        "plans": deepcopy(getattr(spatial, "plans", {})),
        "active": deepcopy(getattr(spatial, "active", {})),
        "events": deepcopy(getattr(spatial, "events", [])),
        "pending": deepcopy(getattr(spatial, "_p07_pending", None)),
        "has_report": hasattr(spatial, "p07_report"),
        "report": deepcopy(getattr(spatial, "p07_report", None)),
    }


def _restore_spatial(spatial: Any, snapshot: Mapping[str, Any]) -> None:
    spatial.plans = deepcopy(snapshot["plans"])
    spatial.active = deepcopy(snapshot["active"])
    spatial.events = deepcopy(snapshot["events"])
    spatial._p07_pending = deepcopy(snapshot["pending"])
    if snapshot["has_report"]:
        spatial.p07_report = deepcopy(snapshot["report"])
    elif hasattr(spatial, "p07_report"):
        delattr(spatial, "p07_report")


def _restore_route(route: Any, references: Mapping[int, Any]) -> None:
    for step, row in references.items():
        route[step] = row


def wrap_reconcile(module: Any, original_reconcile: Any):
    """Build one full-replay current-HIRE wrapper around exact P07."""

    def reconcile(
        spatial: Any,
        observation: Mapping,
        selected: Mapping,
        controller: Any,
        *,
        owner_busy: bool = False,
    ) -> Mapping:
        # Preserve the exact predecessor ordering for higher-priority ownership
        # and an unfinalized pair.  Those paths return before its market veto.
        pending = getattr(spatial, "_p07_pending", None)
        now = int(observation["step"])
        if owner_busy or (
            isinstance(pending, Mapping)
            and int(pending.get("step", now)) == now
        ):
            return original_reconcile(
                spatial,
                observation,
                selected,
                controller,
                owner_busy=owner_busy,
            )

        route = controller.R[controller.cur]
        raw = module._route_row(route, now)
        selected_market = selected.get("market", [])
        raw_market = raw.get("market", [])
        if selected_market == [] and raw_market == []:
            return original_reconcile(
                spatial,
                observation,
                selected,
                controller,
                owner_busy=owner_busy,
            )

        started = time.perf_counter()
        try:
            farm = observation["farms"][observation["player"]]
            existing_actor_count = 1 + len(farm.get("hands", []))
            configuration = dict(getattr(spatial, "configuration", {}) or {})
        except (KeyError, TypeError, ValueError):
            receipt = {"admitted": False, "reason": "malformed_current_observation"}
            _record_rejection(module, spatial, observation, receipt, started)
            return selected

        receipt = classify_current_hire(
            selected,
            raw,
            configuration,
            existing_actor_count,
        )
        if not receipt["admitted"]:
            _record_rejection(module, spatial, observation, receipt, started)
            return selected

        if not isinstance(raw, MutableMapping):
            rejected = dict(receipt)
            rejected.update(
                admitted=False,
                reason="current_hire_route_row_not_mutable",
            )
            _record_rejection(module, spatial, observation, rejected, started)
            return selected

        try:
            limit = module._window_limit(now, configuration)
            if limit < now:
                raise ValueError("empty exact-pair window")
            route_references = {
                step: module._route_row(route, step)
                for step in range(now, limit + 1)
            }
            baseline_rows = {
                step: deepcopy(row) for step, row in route_references.items()
            }
            baseline_rows[now] = deepcopy(selected)
        except (KeyError, TypeError, ValueError, IndexError) as error:
            rejected = dict(receipt)
            rejected.update(
                admitted=False,
                reason=f"current_hire_snapshot_error:{type(error).__name__}",
            )
            _record_rejection(module, spatial, observation, rejected, started)
            return selected

        spatial_before = _spatial_snapshot(spatial)
        original_row = raw
        certified_selected = deepcopy(selected)
        certified_selected["market"] = []
        certified_row = deepcopy(raw)
        certified_row["market"] = []
        try:
            route[now] = certified_row
        except (KeyError, TypeError, IndexError):
            rejected = dict(receipt)
            rejected.update(
                admitted=False,
                reason="current_hire_route_not_mutable",
            )
            _record_rejection(module, spatial, observation, rejected, started)
            return selected

        # The exact primitive normally emits its proposal immediately.  A
        # current-HIRE proposal still needs the dynamic-actor replay below, so
        # suppress that provisional line and emit one final accepted/rejected
        # record only after the second certificate.  Agent calls are isolated
        # and sequential in the evaluator process; always restore the function.
        original_append = getattr(module, "_append_log", None)
        if callable(original_append):
            module._append_log = lambda _record: None
        try:
            output = original_reconcile(
                spatial,
                observation,
                certified_selected,
                controller,
                owner_busy=owner_busy,
            )
        except BaseException:
            # The theorem may never convert an underlying error into a partial
            # route or pair-state mutation.
            _restore_route(route, route_references)
            _restore_spatial(spatial, spatial_before)
            raise
        finally:
            if callable(original_append):
                module._append_log = original_append

        report = getattr(spatial, "p07_report", None)
        changed = isinstance(report, Mapping) and report.get("changed") is True
        if not changed:
            # Preserve exact object identity on a certified but dormant row.
            route[now] = original_row
            _append_window_record(module, spatial, observation, receipt)
            return selected

        try:
            end = int(report["end_step"])
            if not now <= end <= limit:
                raise ValueError("proposal escaped snapshotted window")
            current_row = route[now]
            if not isinstance(current_row, MutableMapping):
                raise TypeError("P07 replaced current route row with non-mapping")
            _restore_exact_field(current_row, original_row, "market")
            _restore_existing_tail(current_row, original_row, existing_actor_count)

            if not isinstance(output, MutableMapping):
                raise TypeError("P07 returned non-mapping under current HIRE")
            restored = deepcopy(output)
            _restore_exact_field(restored, selected, "market")
            _restore_existing_tail(restored, selected, existing_actor_count)

            candidate_rows = {
                step: deepcopy(module._route_row(route, step))
                for step in range(now, end + 1)
            }
            candidate_rows[now] = deepcopy(restored)
            replay = full_post_hire_certificate(
                module,
                spatial.m,
                observation,
                {step: baseline_rows[step] for step in range(now, end + 1)},
                candidate_rows,
                now,
                end,
                configuration,
            )
        except (KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
            _restore_route(route, route_references)
            _restore_spatial(spatial, spatial_before)
            rejected = dict(receipt)
            rejected.update(
                admitted=False,
                reason=f"current_hire_replay_error:{type(error).__name__}",
                replay_error=str(error),
                rolled_back_exact_proposal=True,
            )
            _record_rejection(module, spatial, observation, rejected, started)
            return selected

        if not replay["accepted"]:
            accepted_report = dict(report)
            _restore_route(route, route_references)
            _restore_spatial(spatial, spatial_before)
            rejected = dict(receipt)
            rejected.update(
                admitted=False,
                reason="current_hire_full_replay_mismatch",
                replay=replay,
                rolled_back_exact_proposal=True,
                rolled_back_owner=accepted_report.get("owner"),
                rolled_back_pair=accepted_report.get("pair"),
            )
            _record_rejection(module, spatial, observation, rejected, started)
            return selected

        accepted = dict(receipt)
        accepted["replay"] = replay
        accepted["final_market_bound"] = True
        pending = getattr(spatial, "_p07_pending", None)
        if not isinstance(pending, MutableMapping):
            _restore_route(route, route_references)
            _restore_spatial(spatial, spatial_before)
            rejected = dict(receipt)
            rejected.update(
                admitted=False,
                reason="current_hire_missing_atomic_pending",
                rolled_back_exact_proposal=True,
            )
            _record_rejection(module, spatial, observation, rejected, started)
            return selected
        pending["required_market"] = deepcopy(selected.get("market", []))
        pending["current_hire_replay"] = replay
        _append_window_record(module, spatial, observation, accepted)
        return restored

    reconcile.__name__ = getattr(original_reconcile, "__name__", "reconcile")
    reconcile.__doc__ = (
        "Full-replay current-HIRE window around "
        + (getattr(original_reconcile, "__doc__", "") or "exact P07")
    )
    return reconcile


def _wrap_spatial_install(module: Any, original_install: Any):
    """Add the final market-premise guard outside the exact pair guard."""

    def install_spatial_hooks(spatial: Any, instance: Any, *, enabled: bool = True) -> None:
        original_install(spatial, instance, enabled=enabled)
        if getattr(spatial, "_p07_current_hire_guard_installed", False):
            return
        original_guard = spatial.guard_returned

        def guard_returned(observation, returned, *, repair_fallback=False):
            guarded = original_guard(
                observation,
                returned,
                repair_fallback=repair_fallback,
            )
            pending = getattr(spatial, "_p07_pending", None)
            if not isinstance(pending, MutableMapping):
                return guarded
            if "required_market" not in pending:
                return guarded
            if int(pending.get("step", -1)) != int(observation["step"]):
                return guarded

            pair = tuple(int(worker) for worker in pending["pair"])
            pair_actions_ok = all(
                module._normal_action(guarded, worker)
                == list(pending["candidate_current"][worker])
                for worker in pair
            )
            market_binding_ok = (
                guarded.get("market", []) == pending["required_market"]
            )
            pending["guard_pair_actions"] = pair_actions_ok
            pending["guard_market_binding"] = market_binding_ok
            if pair_actions_ok and market_binding_ok:
                pending["guard_decision"] = "commit_pair"
                return guarded

            # The inner pair guard may already have restored both actions.  Copy
            # once more only to make the market-dependent rollback explicit and
            # immune to future changes in that inner implementation.
            output = deepcopy(guarded)
            for worker in pair:
                module.set_unit(
                    output,
                    worker,
                    list(pending["baseline_current"][worker]),
                )
            pending["guard_decision"] = "rollback_pair"
            return output

        spatial.guard_returned = guard_returned
        spatial._p07_current_hire_guard_installed = True

    install_spatial_hooks.__name__ = getattr(
        original_install, "__name__", "install_spatial_hooks"
    )
    return install_spatial_hooks


def install_current_hire_window(module: Any) -> Any:
    """Patch only the module-global reconciler resolved by installed hooks."""
    if getattr(module, "_p07_current_hire_window_installed", False):
        return module
    original = module.reconcile
    original_install = module.install_spatial_hooks
    module._p07_current_hire_original_reconcile = original
    module._p07_current_hire_original_install = original_install
    module.reconcile = wrap_reconcile(module, original)
    module.install_spatial_hooks = _wrap_spatial_install(module, original_install)
    module._p07_current_hire_window_installed = True
    return module
