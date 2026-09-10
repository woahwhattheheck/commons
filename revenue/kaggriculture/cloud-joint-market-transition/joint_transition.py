# SPDX-License-Identifier: Apache-2.0
"""Exact two-player market + town transition oracle for TITAN source proofs.

The oracle invokes the pinned official ``_process_market`` and ``_town_consume``
functions. Callers supply one complete POST-UNIT prestate and both players'
literal actions. This is a conditional mechanics proof tool, not a policy,
opponent model, game simulator, promotion gate, or hidden-state claim.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Mapping, Sequence

from engine_binding import (
    BudgetExceeded,
    ENGINE_COMMIT,
    ENGINE_GIT_BLOB,
    ENGINE_PATH,
    ENGINE_REPOSITORY,
    ENGINE_SHA256,
    SCHEMA,
    canonical_sha256,
    load_transition_engine,
    _validate_engine_identity,
)
from protection import _comparison
from state_contracts import (
    _require_int,
    _unit_fields,
    _validate_action,
    _validate_json_tree,
    _validate_market,
    _validate_party,
    _validate_party_against_config,
    _validate_town,
    _validated_config,
    _without_market,
)
from transition_core import (
    _check_deadline,
    _run_arm,
    _simulate_prefix,
    _state_from_inputs,
    _work_bound,
)


def compare_joint_transition(
    mechanics: Any,
    *,
    step: int,
    seat: int,
    farms: Sequence[Mapping[str, Any]],
    privates: Sequence[Mapping[str, Any]],
    market: Mapping[str, Any],
    town: Mapping[str, Any],
    baseline_actions: Sequence[Mapping[str, Any]],
    candidate_actions: Sequence[Mapping[str, Any]],
    configuration: Mapping[str, Any],
    checkpoints: Sequence[Mapping[str, Any]] | None = None,
    max_work_units: int = 250_000,
    max_orders_budget: int = 128,
    deadline: float | None = None,
) -> dict[str, Any]:
    """Compare exact current market+town transitions from one shared prestate.

    The rival action must be byte-equivalent between arms. The candidate may only
    change the tested player's market queue; unit fields must already have been
    applied and must match. Unknown or over-budget input returns ``status=unknown``.
    """

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "unknown",
        "reason": None,
        "step": step,
        "seat": seat,
        "horizon": "one_post_unit_market_then_town_transition",
        "conditional_on_supplied_private_state": True,
        "probabilistic": False,
        "action_selected": False,
        "promotion_claimed": False,
        "engine": {
            "repository": ENGINE_REPOSITORY,
            "commit": ENGINE_COMMIT,
            "path": ENGINE_PATH,
            "git_blob": getattr(mechanics, "git_blob_sha1", None),
            "sha256": getattr(mechanics, "source_sha256", None),
        },
    }
    started = time.perf_counter()
    raw_inputs = {
        "step": step,
        "seat": seat,
        "farms": farms,
        "privates": privates,
        "market": market,
        "town": town,
        "baseline_actions": baseline_actions,
        "candidate_actions": candidate_actions,
        "configuration": configuration,
        "checkpoints": checkpoints or [],
    }
    try:
        _validate_engine_identity(mechanics)
        _require_int(max_work_units, "max_work_units", minimum=1)
        _require_int(max_orders_budget, "max_orders_budget", minimum=1)
        if deadline is not None and (isinstance(deadline, bool) or not isinstance(deadline, (int, float)) or not math.isfinite(float(deadline))):
            raise ValueError("deadline_must_be_finite_absolute_time")
        _check_deadline(deadline)
        _validate_json_tree(raw_inputs)
        input_hash_before = canonical_sha256(raw_inputs)
        _require_int(step, "step", minimum=0)
        _require_int(seat, "seat", minimum=0)
        if seat not in (0, 1):
            raise ValueError("seat_must_be_zero_or_one")
        if not isinstance(farms, (list, tuple)) or len(farms) != 2:
            raise ValueError("exactly_two_farms_required")
        if not isinstance(privates, (list, tuple)) or len(privates) != 2:
            raise ValueError("exactly_two_privates_required")
        if not isinstance(baseline_actions, (list, tuple)) or len(baseline_actions) != 2:
            raise ValueError("exactly_two_baseline_actions_required")
        if not isinstance(candidate_actions, (list, tuple)) or len(candidate_actions) != 2:
            raise ValueError("exactly_two_candidate_actions_required")
        for player in (0, 1):
            _validate_party(farms[player], privates[player], f"player{player}")
            _validate_action(baseline_actions[player], f"baseline_player{player}")
            _validate_action(candidate_actions[player], f"candidate_player{player}")
        _validate_market(mechanics, market)
        _validate_town(mechanics, town)
        config = _validated_config(configuration)
        for player in (0, 1):
            _validate_party_against_config(mechanics, farms[player], privates[player], config, f"player{player}")
        max_orders = max(1, config["maxMarketOrdersPerTurn"])
        if max_orders > max_orders_budget:
            raise BudgetExceeded("order_budget")
        if baseline_actions[1 - seat] != candidate_actions[1 - seat]:
            raise ValueError("rival_action_must_be_identical_between_arms")
        if _without_market(baseline_actions[seat]) != _without_market(candidate_actions[seat]):
            raise ValueError("candidate_may_only_change_tested_market_queue")
        for player in (0, 1):
            if _unit_fields(baseline_actions[player]) != _unit_fields(candidate_actions[player]):
                raise ValueError("unit_fields_must_match_between_arms")
        checkpoint_list = list(checkpoints or [])

        work = (
            _work_bound(mechanics, baseline_actions, farms, config, max_orders)
            + _work_bound(mechanics, candidate_actions, farms, config, max_orders)
        )
        if work > max_work_units:
            raise BudgetExceeded("unit_work_budget")
        report["requested_work_bound"] = work
        prestate = _state_from_inputs(farms, privates, market, town)
        report["prestate_hash"] = canonical_sha256(prestate)
        baseline = _run_arm(mechanics, prestate, baseline_actions, config, step=step, deadline=deadline)
        candidate = _run_arm(mechanics, prestate, candidate_actions, config, step=step, deadline=deadline)
        _check_deadline(deadline)
        report["baseline"] = baseline
        report["candidate"] = candidate
        report["comparison"] = _comparison(baseline, candidate, seat=seat, checkpoints=checkpoint_list)
        input_hash_after = canonical_sha256(raw_inputs)
        if input_hash_before != input_hash_after:
            raise RuntimeError("input_mutation_detected")
        report["input_hash"] = input_hash_before
        report["input_unchanged"] = True
        _validate_json_tree(report)  # reject overflow/non-finite derived evidence
        report["status"] = "complete_conditional"
    except BudgetExceeded as exc:
        report["reason"] = str(exc)
    except (ValueError, KeyError, TypeError, OverflowError, RecursionError) as exc:
        report["reason"] = "invalid_or_incomplete_input:" + str(exc)
    except Exception as exc:  # engine exceptions are evidence failures, not partial results
        report["reason"] = "engine_or_oracle_error:" + type(exc).__name__ + ":" + str(exc)
    report["elapsed_seconds"] = time.perf_counter() - started
    return report


def _paths_alias(left: Path, right: Path) -> bool:
    try:
        if left.resolve() == right.resolve():
            return True
        return left.exists() and right.exists() and left.samefile(right)
    except (OSError, RuntimeError):
        raise ValueError("cannot_resolve_path_identity") from None


def _atomic_write(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temp_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-source", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--deadline-seconds", type=float)
    args = parser.parse_args(argv)
    for incoming in (args.engine_source, args.input, Path(__file__)):
        if args.output is not None and _paths_alias(args.output, incoming):
            parser.error("output must not alias engine, input, or oracle source")
    if args.deadline_seconds is not None and (not math.isfinite(args.deadline_seconds) or args.deadline_seconds <= 0):
        parser.error("deadline-seconds must be finite and positive")

    mechanics = load_transition_engine(args.engine_source)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    deadline = time.monotonic() + args.deadline_seconds if args.deadline_seconds is not None else None
    result = compare_joint_transition(mechanics, deadline=deadline, **payload)
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output is None:
        print(text, end="")
    else:
        _atomic_write(args.output, text.encode("utf-8"))
    if result["status"] != "complete_conditional":
        return 2
    if result["comparison"]["protection"]["status"] == "HOLD":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
