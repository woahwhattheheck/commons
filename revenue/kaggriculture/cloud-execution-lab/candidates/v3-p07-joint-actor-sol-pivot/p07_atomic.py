# SPDX-License-Identifier: Apache-2.0
"""Exact, pair-atomic integration for the TITAN P07 joint-actor primitive.

This module owns no producer and no independent schedule.  It runs only after
the existing SpatialTempo transform, enumerates a bounded pair/horizon family,
asks ``joint_assignment.propose_pair_swap`` to certify exact final-state
equivalence, and publishes both worker streams together.

The two publication boundaries are deliberately separate:

* ``guard_returned`` makes the current action all-or-nothing after every later
  consumer guard; and
* ``finish`` verifies that continuation custody contains both pair members or
  neither, repairing a hypothetical one-sided commit back to the previous
  state.

The feature is installed only by the isolated candidate entrypoint.  Canonical
TITAN and its package configuration remain byte-for-byte unchanged.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from itertools import combinations
import json
import os
from pathlib import Path
import time
from typing import Any, Mapping, MutableMapping, Sequence

from joint_assignment import JointAssignmentError, propose_pair_swap
from spatial_tempo import MOVES, move, set_unit, unit

CHECKPOINTS = (226, 360, 433)
MAX_PAIRS = 12
MAX_PROPOSALS = 64
MAX_HORIZON = 23
P07_KIND = "p07_joint_actor"
P07_REASON_ACCEPTED = "accepted_exact_joint_swap"


def _route_row(route: Sequence | Mapping, step: int) -> Mapping:
    try:
        row = route[step]
    except (IndexError, KeyError, TypeError):
        raise JointAssignmentError(f"missing route row at step {step}") from None
    if not isinstance(row, Mapping):
        raise JointAssignmentError(f"route row {step} must be a mapping")
    return row


def _normal_action(row: Mapping, worker: int) -> list:
    raw = unit(row, worker)
    return list(raw) if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) and raw else ["PASS"]


def _route_view(route: Sequence | Mapping, selected: Mapping, start: int, end: int) -> dict[int, Mapping]:
    return {
        step: (selected if step == start else _route_row(route, step))
        for step in range(start, end + 1)
    }


def _structural_end_steps(
    selected: Mapping,
    route: Sequence | Mapping,
    worker: int,
    start: int,
    limit: int,
) -> tuple[int, ...]:
    """Cheaply find strict PICKUP->service->DROP horizons before exact simulation.

    ``propose_pair_swap`` is the authority.  This scan merely avoids calling the
    exact simulator for every possible endpoint at every game step.
    """
    first_event = False
    serviced = False
    dropped = False
    ends: list[int] = []
    for step in range(start, limit + 1):
        row = selected if step == start else _route_row(route, step)
        action = _normal_action(row, worker)
        op = action[0]
        if op in MOVES or op == "PASS":
            if dropped:
                ends.append(step)
            continue
        if not first_event:
            if op != "PICKUP":
                return ()
            first_event = True
            continue
        if dropped:
            return tuple(ends)
        if op == "PICKUP":
            return tuple(ends)
        if op == "DROP":
            if not serviced:
                return ()
            dropped = True
            ends.append(step)
            continue
        serviced = True
    return tuple(ends)


def _window_limit(now: int, configuration: Mapping) -> int:
    turns_per_day = int(configuration.get("turnsPerDay", 24))
    episode_steps = int(configuration.get("episodeSteps", 720))
    if turns_per_day <= 0:
        return now - 1
    # Never include the hour-23 action: unit actions precede the end-of-day
    # transfer, and the exact primitive intentionally does not own that reset.
    limit = min(
        now + MAX_HORIZON - 1,
        ((now // turns_per_day) + 1) * turns_per_day - 2,
        episode_steps - 2,
    )
    for checkpoint in CHECKPOINTS:
        if now <= checkpoint <= limit:
            limit = checkpoint - 1
            break
    return limit


def _positions(farm: Mapping) -> list[tuple[int, int]]:
    return [
        tuple(int(x) for x in farm["farmer"][:2]),
        *[tuple(int(x) for x in position[:2]) for position in farm.get("hands", [])],
    ]


def _goal(origin: tuple[int, int], stream: Sequence[Sequence], board: int) -> tuple[int, int]:
    position = origin
    for action in stream:
        position = move(position, action, board)
    return position


def _plan_owner(plan: Mapping | None) -> str | None:
    if not isinstance(plan, Mapping):
        return None
    return str(plan.get("owner") or plan.get("owner_key") or "") or None


def _json_signature(plan: Any) -> str:
    value = plan.as_dict() if hasattr(plan, "as_dict") else plan
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _append_log(record: Mapping[str, Any]) -> None:
    """Append one short JSON line atomically when the census requests it."""
    target = os.environ.get("TITAN_P07_LOG")
    if not target:
        return
    payload = (
        json.dumps(dict(record), sort_keys=True, separators=(",", ":"), default=str)
        + "\n"
    ).encode("utf-8")
    try:
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.write(descriptor, payload)
        finally:
            os.close(descriptor)
    except OSError:
        # Diagnostics can never make the playing action fail.
        return


def _report(
    spatial: Any,
    observation: Mapping,
    *,
    changed: bool,
    reason: str,
    started: float,
    **extra: Any,
) -> dict[str, Any]:
    record = {
        "phase": "proposal",
        "step": int(observation["step"]),
        "player": int(observation["player"]),
        "changed": bool(changed),
        "reason": str(reason),
        "runtime_seconds": round(time.perf_counter() - started, 6),
        **extra,
    }
    spatial.p07_report = record
    _append_log(record)
    return record


def _publish_plan(
    spatial: Any,
    observation: Mapping,
    selected: Mapping,
    controller: Any,
    result: Any,
) -> tuple[dict, dict]:
    """Publish a certified pair to the route and SpatialTempo proposal atomically."""
    certified = result.plan
    if certified is None:
        raise ValueError("changed result must contain a plan")
    route = controller.R[controller.cur]
    now = int(observation["step"])
    if certified.step != now:
        raise ValueError("P07 may publish only from the current observation")
    pair = tuple(int(worker) for worker in certified.workers)
    if len(pair) != 2 or pair[0] == pair[1]:
        raise ValueError("P07 requires exactly two distinct workers")

    # Build every changed row and every plan dictionary before publishing any
    # shared object.  A deadline signal before publication therefore leaves no
    # partial route or proposal.
    rows: dict[int, dict] = {}
    for offset in range(certified.end_step - certified.step + 1):
        step = certified.step + offset
        row = deepcopy(_route_row(route, step))
        set_unit(row, pair[0], list(certified.replacement[0][offset]))
        set_unit(row, pair[1], list(certified.replacement[1][offset]))
        rows[step] = row

    farm = observation["farms"][observation["player"]]
    positions = _positions(farm)
    board = len(farm["tiles"])
    prior_state = deepcopy(getattr(spatial, "_committed", None))
    prior_plans = {
        worker: deepcopy(spatial.plans.get(worker))
        for worker in pair
        if worker in spatial.plans
    }
    plans: dict[int, dict] = {}
    for index, worker in enumerate(pair):
        replacement = [list(action) for action in certified.replacement[index]]
        origin = positions[worker]
        plans[worker] = {
            "kind": P07_KIND,
            "owner": certified.owner_key,
            "owner_key": certified.owner_key,
            "pair": pair,
            "step": certified.step,
            "worker": worker,
            "end": certified.end_step + 1,  # SpatialTempo end is exclusive.
            "route": controller.cur,
            "origin": origin,
            "goal": _goal(origin, replacement, board),
            "replacement": replacement,
            "original": [
                _normal_action(
                    selected if step == now else _route_row(route, step),
                    worker,
                )
                for step in range(certified.step, certified.end_step + 1)
            ],
            "extra": None,
            "travel_saved": certified.travel_saved,
        }

    output = deepcopy(selected)
    baseline_current = {
        worker: _normal_action(selected, worker) for worker in pair
    }
    candidate_current = {
        pair[0]: list(certified.replacement[0][0]),
        pair[1]: list(certified.replacement[1][0]),
    }
    set_unit(output, pair[0], candidate_current[pair[0]])
    set_unit(output, pair[1], candidate_current[pair[1]])

    pending = {
        "step": now,
        "owner": certified.owner_key,
        "pair": pair,
        "baseline_current": baseline_current,
        "candidate_current": candidate_current,
        "prior_state": prior_state,
        "prior_pair_plans": prior_plans,
        "travel_saved": int(certified.travel_saved),
        "guard_decision": None,
    }

    # Publication begins here.  All values above are already complete.
    for step in sorted(rows):
        route[step] = rows[step]
    for worker in pair:
        spatial.plans[worker] = plans[worker]
        spatial.active[worker] = plans[worker]["end"]
        spatial.events.append(
            {
                "kind": P07_KIND,
                "step": now,
                "worker": worker,
                "owner": certified.owner_key,
                "pair": list(pair),
                "travel_saved": certified.travel_saved,
            }
        )
    spatial._p07_pending = pending
    return output, pending


def reconcile(
    spatial: Any,
    observation: Mapping,
    selected: Mapping,
    controller: Any,
    *,
    owner_busy: bool = False,
) -> Mapping:
    """Select and publish at most one exact joint swap for the current step."""
    started = time.perf_counter()
    now = int(observation["step"])
    configuration = dict(getattr(spatial, "configuration", {}) or {})
    if owner_busy:
        _report(spatial, observation, changed=False, reason="other_owner_active", started=started)
        return selected
    stale_pending = getattr(spatial, "_p07_pending", None)
    if stale_pending is not None:
        if int(stale_pending.get("step", now)) != now:
            # A cancelled call may skip finalization.  SpatialTempo._begin has
            # already rebuilt the route from pristine/committed state, so only
            # this uncommitted receipt remains to be cleared.
            spatial._p07_pending = None
        else:
            _report(
                spatial,
                observation,
                changed=False,
                reason="pending_pair_not_finished",
                started=started,
            )
            return selected

    farm = observation["farms"][observation["player"]]
    count = 1 + len(farm.get("hands", []))
    if count < 2:
        _report(spatial, observation, changed=False, reason="fewer_than_two_actors", started=started)
        return selected
    if len(observation.get("private", {}).get("inventories", [])) < count:
        _report(spatial, observation, changed=False, reason="inventory_cardinality_mismatch", started=started)
        return selected

    route = controller.R[controller.cur]
    raw = _route_row(route, now)
    if selected.get("market", []) or raw.get("market", []):
        _report(spatial, observation, changed=False, reason="current_market_boundary", started=started)
        return selected

    limit = _window_limit(now, configuration)
    if limit - now < 2:
        _report(spatial, observation, changed=False, reason="window_too_short", started=started)
        return selected

    busy = set(int(worker) for worker in getattr(spatial, "active", {}))
    busy.update(int(worker) for worker in getattr(spatial, "plans", {}))
    crop = getattr(spatial, "crop_intent", None)
    if isinstance(crop, Mapping) and crop.get("worker") is not None:
        busy.add(int(crop["worker"]))
    stock = getattr(spatial, "sale_obligation", None)
    if isinstance(stock, Mapping) and stock.get("worker") is not None:
        busy.add(int(stock["worker"]))

    # Exact-current-source binding: the candidate cannot reinterpret a dynamic
    # current repair as an inherited route action.
    eligible: list[int] = []
    current_mismatch = 0
    cargo = observation["private"]["inventories"]
    for worker in range(count):
        if worker in busy or cargo[worker]:
            continue
        if _normal_action(selected, worker) != _normal_action(raw, worker):
            current_mismatch += 1
            continue
        eligible.append(worker)
    if len(eligible) < 2:
        _report(
            spatial,
            observation,
            changed=False,
            reason="fewer_than_two_eligible_actors",
            started=started,
            busy_workers=sorted(busy),
            current_row_mismatches=current_mismatch,
        )
        return selected

    ends = {
        worker: set(_structural_end_steps(selected, route, worker, now, limit))
        for worker in eligible
    }
    candidates: list[tuple[tuple[int, int, int, int], Any]] = []
    rejects: Counter[str] = Counter()
    attempts = 0
    for worker_a, worker_b in list(combinations(eligible, 2))[:MAX_PAIRS]:
        common = sorted(ends[worker_a] & ends[worker_b])
        if not common:
            rejects["no_common_complete_bundle_horizon"] += 1
            continue
        # Prefer the earliest complete endpoint, then allow bounded later rejoin
        # positions.  Every admitted endpoint is still certified independently.
        sampled = common[:4]
        if common[-1] not in sampled:
            sampled.append(common[-1])
        for end in sampled:
            if attempts >= MAX_PROPOSALS:
                break
            attempts += 1
            view = _route_view(route, selected, now, end)
            try:
                proposal = propose_pair_swap(
                    spatial.m,
                    observation,
                    view,
                    worker_a,
                    worker_b,
                    start_step=now,
                    end_step=end,
                    configuration=configuration,
                    checkpoints=CHECKPOINTS,
                )
            except (JointAssignmentError, KeyError, TypeError, ValueError) as error:
                rejects[f"malformed:{type(error).__name__}"] += 1
                continue
            if not proposal.changed or proposal.plan is None:
                rejects[proposal.reason] += 1
                continue
            plan = proposal.plan
            key = (
                int(plan.travel_saved),
                -(plan.end_step - plan.step + 1),
                -min(plan.workers),
                -max(plan.workers),
            )
            candidates.append((key, proposal))
        if attempts >= MAX_PROPOSALS:
            break

    if not candidates:
        reason = rejects.most_common(1)[0][0] if rejects else "no_structural_candidate"
        _report(
            spatial,
            observation,
            changed=False,
            reason=reason,
            started=started,
            attempts=attempts,
            eligible=eligible,
            reject_counts=dict(sorted(rejects.items())),
        )
        return selected

    candidates.sort(key=lambda item: item[0], reverse=True)
    best_key, best = candidates[0]
    tied = [proposal for key, proposal in candidates if key == best_key]
    signatures = {_json_signature(proposal.plan) for proposal in tied}
    if len(signatures) > 1:
        _report(
            spatial,
            observation,
            changed=False,
            reason="ambiguous_best_pair",
            started=started,
            attempts=attempts,
            tied=len(signatures),
            reject_counts=dict(sorted(rejects.items())),
        )
        return selected

    output, pending = _publish_plan(spatial, observation, selected, controller, best)
    _report(
        spatial,
        observation,
        changed=True,
        reason=P07_REASON_ACCEPTED,
        started=started,
        attempts=attempts,
        pair=list(pending["pair"]),
        owner=pending["owner"],
        end_step=int(best.plan.end_step),
        travel_saved=int(best.plan.travel_saved),
        current_action_changed=any(
            pending["baseline_current"][worker] != pending["candidate_current"][worker]
            for worker in pending["pair"]
        ),
        reject_counts=dict(sorted(rejects.items())),
    )
    return output


def _restore_pair_after_half_commit(spatial: Any, pending: Mapping, now: int) -> None:
    """Remove a one-sided P07 continuation while preserving unrelated commits."""
    state = deepcopy(getattr(spatial, "_committed", None))
    if not isinstance(state, MutableMapping):
        return
    pair = tuple(int(worker) for worker in pending["pair"])
    owner = str(pending["owner"])
    plans = dict(state.get("plans", {}))
    prior_state = pending.get("prior_state")
    prior_plans = (
        dict(prior_state.get("plans", {}))
        if isinstance(prior_state, Mapping)
        else {}
    )
    for worker in pair:
        if _plan_owner(plans.get(worker)) == owner:
            plans.pop(worker, None)
        if worker in prior_plans:
            plans[worker] = deepcopy(prior_plans[worker])

    patches: dict[tuple[Any, int], dict[int, list]] = {}
    for worker, plan in plans.items():
        for offset, action in enumerate(plan["replacement"]):
            step = int(plan["step"]) + offset
            if step >= now:
                patches.setdefault((plan["route"], step), {})[int(worker)] = list(action)
    events = [
        event
        for event in state.get("events", [])
        if not (
            isinstance(event, Mapping)
            and (
                event.get("owner") == owner
                or (
                    event.get("kind") == P07_KIND
                    and int(event.get("worker", -1)) in pair
                )
            )
        )
    ]
    state.update(
        patches=patches,
        plans=plans,
        events=events,
        active={int(worker): int(plan["end"]) for worker, plan in plans.items()},
    )
    spatial._committed = state


def install_spatial_hooks(spatial: Any, instance: Any, *, enabled: bool = True) -> None:
    """Install one transform/guard/finish chain on a SpatialTempo instance."""
    if getattr(spatial, "_p07_hooks_installed", False):
        spatial._p07_enabled = bool(enabled)
        spatial._p07_instance = instance
        return

    original_transform = spatial.transform
    original_guard = spatial.guard_returned
    original_finish = spatial.finish

    def transform(observation, selected, controller):
        result = original_transform(observation, selected, controller)
        if not getattr(spatial, "_p07_enabled", False):
            _report(
                spatial,
                observation,
                changed=False,
                reason="feature_disabled",
                started=time.perf_counter(),
            )
            return result
        owner = getattr(spatial, "_p07_instance", None)
        quadrant = getattr(owner, "quadrant", None)
        owner_busy = bool(getattr(quadrant, "active", False))
        return reconcile(
            spatial,
            observation,
            result,
            controller,
            owner_busy=owner_busy,
        )

    def guard_returned(observation, returned, *, repair_fallback=False):
        guarded = original_guard(
            observation, returned, repair_fallback=repair_fallback
        )
        pending = getattr(spatial, "_p07_pending", None)
        if not isinstance(pending, MutableMapping):
            return guarded
        if int(pending.get("step", -1)) != int(observation["step"]):
            return guarded
        pair = tuple(int(worker) for worker in pending["pair"])
        accepted = all(
            _normal_action(guarded, worker)
            == list(pending["candidate_current"][worker])
            for worker in pair
        )
        if accepted:
            pending["guard_decision"] = "commit_pair"
            return guarded

        # A later consumer changed one or both worker actions.  Restore the exact
        # pre-P07 current row for both, so the interpreter never sees half of an
        # exact-equivalence certificate.
        output = deepcopy(guarded)
        for worker in pair:
            set_unit(output, worker, list(pending["baseline_current"][worker]))
        pending["guard_decision"] = "rollback_pair"
        return output

    def finish(observation, returned_action, post=None):
        pending = deepcopy(getattr(spatial, "_p07_pending", None))
        original_finish(observation, returned_action, post)
        if not isinstance(pending, Mapping):
            return
        now = int(observation["step"])
        if int(pending.get("step", -1)) != now:
            spatial._p07_pending = None
            return
        owner = str(pending["owner"])
        pair = tuple(int(worker) for worker in pending["pair"])
        state = getattr(spatial, "_committed", None)
        plans = state.get("plans", {}) if isinstance(state, Mapping) else {}
        present = [
            worker for worker in pair if _plan_owner(plans.get(worker)) == owner
        ]
        repaired = False
        if len(present) == 1:
            _restore_pair_after_half_commit(spatial, pending, now)
            repaired = True
            present = []
        committed = len(present) == 2
        record = {
            "phase": "finish",
            "step": now,
            "player": int(observation["player"]),
            "owner": owner,
            "pair": list(pair),
            "guard_decision": pending.get("guard_decision"),
            "committed": committed,
            "atomic_repair": repaired,
            "present_after_finish": present,
            "travel_saved": int(pending.get("travel_saved", 0)),
        }
        spatial.p07_finish_report = record
        _append_log(record)
        spatial._p07_pending = None

    spatial.transform = transform
    spatial.guard_returned = guard_returned
    spatial.finish = finish
    spatial._p07_enabled = bool(enabled)
    spatial._p07_instance = instance
    spatial._p07_pending = None
    spatial._p07_hooks_installed = True


def install_agent(instance: Any, *, enabled: bool = True) -> Any:
    """Install P07 after every canonical initialization/reconstruction."""
    if getattr(instance, "_p07_agent_installed", False):
        instance._p07_enabled = bool(enabled)
        return instance
    original_initialize = instance._initialize

    def initialize():
        original_initialize()
        spatial = getattr(instance, "spatial", None)
        if spatial is not None:
            install_spatial_hooks(
                spatial, instance, enabled=getattr(instance, "_p07_enabled", False)
            )

    instance._initialize = initialize
    instance._p07_enabled = bool(enabled)
    instance._p07_agent_installed = True
    return instance
