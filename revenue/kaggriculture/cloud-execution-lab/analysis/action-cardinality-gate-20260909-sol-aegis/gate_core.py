"""Replay-analysis layer for the Titan observable-hand cardinality gate."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from gate_common import (
    GateInputError,
    _action_for_record,
    _agent_name,
    _day_hour,
    _exact_int,
    _exact_string,
    _is_canonical_market_no_order,
    _observation_for_record,
    _observable_hand_count,
    _opcode,
    _require_key,
    _require_list,
    _require_mapping,
    _validate_action_rows,
    _violation_ranges,
    canonical_json_bytes,
    sha256_bytes,
)


def analyze_replay(
    replay: Mapping[str, Any],
    *,
    seat: int,
    expected_episode_id: int | None = None,
    expected_agent_name: str | None = None,
) -> dict[str, Any]:
    """Analyze a parsed replay and return deterministic, unsealed evidence."""

    seat = _exact_int(seat, "seat", minimum=0)
    if replay.get("name") != "kaggriculture":
        raise GateInputError("replay.name must be exactly 'kaggriculture'")
    module_version = _exact_string(replay.get("module_version"), "replay.module_version")
    info = _require_mapping(_require_key(replay, "info", "replay"), "replay.info")
    episode_id = _exact_int(
        _require_key(info, "EpisodeId", "replay.info"),
        "replay.info.EpisodeId",
        minimum=0,
    )
    seed = _exact_int(
        _require_key(info, "seed", "replay.info"),
        "replay.info.seed",
        minimum=0,
    )
    if expected_episode_id is not None:
        expected_episode_id = _exact_int(
            expected_episode_id, "expected_episode_id", minimum=0
        )
        if episode_id != expected_episode_id:
            raise GateInputError(
                f"episode id mismatch: observed {episode_id}, expected {expected_episode_id}"
            )
    agent_name = _agent_name(info, seat)
    if expected_agent_name is not None:
        expected_agent_name = _exact_string(expected_agent_name, "expected_agent_name")
        if agent_name != expected_agent_name:
            raise GateInputError(
                f"agent name mismatch: observed {agent_name!r}, expected {expected_agent_name!r}"
            )

    steps = _require_list(_require_key(replay, "steps", "replay"), "replay.steps")
    if not steps:
        raise GateInputError("replay.steps must not be empty")

    observations: list[Mapping[str, Any]] = []
    selected_records: list[Mapping[str, Any]] = []
    for step_index, raw_step in enumerate(steps):
        records = _require_list(raw_step, f"steps[{step_index}]")
        if seat >= len(records):
            raise GateInputError(
                f"steps[{step_index}] has {len(records)} records, no seat {seat}"
            )
        record = _require_mapping(records[seat], f"steps[{step_index}][{seat}]")
        selected_records.append(record)
        observations.append(
            _observation_for_record(record, step=step_index, seat=seat)
        )

    ledger: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    omitted_hand_rows_total = 0
    canonical_no_order_count = 0
    empty_market_row_count = 0
    trailing_opcode_counts: Counter[str] = Counter()

    for step_index, record in enumerate(selected_records):
        pre_step = 0 if step_index == 0 else step_index - 1
        pre_observation = observations[pre_step]
        observable_hands = _observable_hand_count(
            pre_observation, step=pre_step, seat=seat
        )
        day, hour = _day_hour(
            pre_observation,
            label=f"steps[{pre_step}][{seat}].observation",
        )
        action = _action_for_record(record, step=step_index, seat=seat)
        hand_rows = _require_list(
            _require_key(action, "hands", f"steps[{step_index}][{seat}].action"),
            f"steps[{step_index}][{seat}].action.hands",
        )
        _validate_action_rows(
            hand_rows, f"steps[{step_index}][{seat}].action.hands"
        )
        market_rows = _require_list(
            _require_key(action, "market", f"steps[{step_index}][{seat}].action"),
            f"steps[{step_index}][{seat}].action.market",
        )
        # Market rows are classified but not semantically validated here.  A
        # literal [] is present evidence, not an absent row, and belongs to the
        # separate market-normalization lane.
        canonical_rows_here = sum(
            1 for row in market_rows if _is_canonical_market_no_order(row)
        )
        empty_rows_here = sum(1 for row in market_rows if row == [])
        canonical_no_order_count += canonical_rows_here
        empty_market_row_count += empty_rows_here

        submitted = len(hand_rows)
        delta = submitted - observable_hands
        omitted = max(0, -delta)
        omitted_hand_rows_total += omitted
        action_digest = sha256_bytes(canonical_json_bytes(action))
        pre_state_digest = sha256_bytes(
            canonical_json_bytes(
                {
                    "day": day,
                    "hour": hour,
                    "player": seat,
                    "own_farm": pre_observation["farms"][seat],
                }
            )
        )
        ledger_row = {
            "step": step_index,
            "pre_observation_step": pre_step,
            "alignment": "bootstrap-same-step" if step_index == 0 else "previous-step",
            "day": day,
            "hour": hour,
            "observable_hands": observable_hands,
            "submitted_hand_rows": submitted,
            "delta": delta,
            "omitted_hand_rows": omitted,
            "canonical_market_no_order_rows": canonical_rows_here,
            "empty_market_rows": empty_rows_here,
            "action_sha256": action_digest,
            "pre_state_sha256": pre_state_digest,
        }
        ledger.append(ledger_row)
        if delta > 0:
            trailing_rows = hand_rows[observable_hands:]
            for row in trailing_rows:
                trailing_opcode_counts[_opcode(row)] += 1
            violations.append(
                {
                    **ledger_row,
                    "trailing_rows": trailing_rows,
                    "trailing_rows_sha256": sha256_bytes(
                        canonical_json_bytes(trailing_rows)
                    ),
                }
            )

    return {
        "environment": replay["name"],
        "module_version": module_version,
        "episode_id": episode_id,
        "seed": seed,
        "seat": seat,
        "agent_name": agent_name,
        "transition_count": len(ledger),
        "bootstrap_transition_count": 1,
        "over_cardinality_transition_count": len(violations),
        "omitted_hand_rows_total": omitted_hand_rows_total,
        "canonical_market_no_order_row_count": canonical_no_order_count,
        "empty_market_row_count": empty_market_row_count,
        "trailing_opcode_counts": dict(sorted(trailing_opcode_counts.items())),
        "violation_ranges": _violation_ranges(violations),
        "violations": violations,
        "transition_ledger_sha256": sha256_bytes(canonical_json_bytes(ledger)),
    }


