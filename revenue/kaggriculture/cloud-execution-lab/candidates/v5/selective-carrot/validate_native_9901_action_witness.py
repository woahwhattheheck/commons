#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed validator for the exact native-9901 Apex action witness."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

SCHEMA = "titan-v5-production-action-divergence/v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TRACE_NAMES = (
    "left_candidate",
    "right_candidate",
    "left_opponent",
    "right_opponent",
)
TRACE_DIGEST_FIELDS = {
    "left_candidate": "left_candidate_trace_sha256",
    "right_candidate": "right_candidate_trace_sha256",
    "left_opponent": "left_opponent_trace_sha256",
    "right_opponent": "right_opponent_trace_sha256",
}
EXPECTED = {
    "evaluator": "e30b3108e0027477ab7ddbc057892a241c41a1f2b38f72caf267477877c4333c",
    "loader": "61093af280494f95d0f3e5137f716c980ebaf7a2bb53fb333b03566810808e6e",
    "engine": {
        "kaggriculture.py": "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e",
        "kaggriculture.json": "a82c89c1a2315b93f39775d8e025471a01b738647c9772658368ee6b1b6f4867",
        "utils.py": "537b627b11784d424147ef57ebb0369b039bf83c9f891e81f10486b1f552334b",
    },
    "left_archive": "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361",
    "right_archive": "20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239",
    "left_entry": "87df8bf2088b0650042350590d9486b6541b6ac2cd7ac1cb51fc1eaf43e8b7d0",
    "right_entry": "e40be452f16050f8ad1a67e0124b2df6983b93869b679d82860ca11c1bec34b3",
    "opponent_entry": "e7b78d4b9e2fc7a68528e45f876a68b50d364103ebd5bf5f2dbbf68770bf54f5",
    "seed": 1209129901,
    "rng_seed": 20260912,
    "seats": [0, 1],
    "timeouts": {"action": 1.25, "startup": 10.0, "game": 900.0},
    "steps": 719,
}
EXPECTED_SCORES = {
    0: {"left": [74143.0, 64333.0], "right": [73906.0, 63838.0]},
    1: {"left": [64333.0, 74143.0], "right": [63838.0, 73906.0]},
}


class ValidationError(ValueError):
    pass


def _encoded(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_encoded(value)).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _sha_from_authority(authority: dict[str, Any], key: str) -> str:
    value = authority.get(key)
    _require(isinstance(value, dict), f"authority.{key} must be an object")
    sha = value.get("sha256")
    _require(isinstance(sha, str), f"authority.{key}.sha256 missing")
    return sha


def _optional_step(value: Any, field: str) -> int | None:
    if value is None:
        return None
    _require(
        type(value) is int and 0 <= value < EXPECTED["steps"],
        f"{field} invalid",
    )
    return value


def _validate_vector(value: Any, name: str, seat: int) -> list[dict[str, Any]]:
    _require(type(value) is list, f"seat {seat} {name} trace vector missing")
    _require(
        len(value) == EXPECTED["steps"],
        f"seat {seat} {name} trace vector length mismatch",
    )
    for step, row in enumerate(value):
        _require(type(row) is dict, f"seat {seat} {name} trace row invalid")
        _require(
            set(row) == {"step", "observation_sha256", "action_sha256"},
            f"seat {seat} {name} trace row shape invalid",
        )
        _require(row.get("step") == step, f"seat {seat} {name} trace steps not contiguous")
        for field in ("observation_sha256", "action_sha256"):
            sha = row.get(field)
            _require(
                isinstance(sha, str) and _SHA256_RE.fullmatch(sha) is not None,
                f"seat {seat} {name} {field} invalid",
            )
    return value


def _trace_digest(rows: list[dict[str, Any]]) -> str:
    # Recorder v1 digests the full trace row after dropping only the full action.
    # Every completed vector row therefore reconstructs response_kind='action'.
    return _digest([
        {
            "step": row["step"],
            "observation_sha256": row["observation_sha256"],
            "response_kind": "action",
            "action_sha256": row["action_sha256"],
        }
        for row in rows
    ])


def _first_diff(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    field: str,
) -> int | None:
    _require(len(left) == len(right), "trace vector lengths differ")
    for lrow, rrow in zip(left, right):
        _require(lrow["step"] == rrow["step"], "trace vector topology differs")
        if lrow[field] != rrow[field]:
            return lrow["step"]
    return None


def _validate_comparison(comparison: dict[str, Any], seat: int) -> tuple[int | None, bool]:
    """Derive divergence ordering from complete trace vectors, never summaries."""
    vectors_obj = comparison.get("trace_vectors")
    _require(type(vectors_obj) is dict, f"seat {seat} trace_vectors missing")
    _require(set(vectors_obj) == set(TRACE_NAMES), f"seat {seat} trace_vectors shape invalid")
    vectors = {
        name: _validate_vector(vectors_obj.get(name), name, seat)
        for name in TRACE_NAMES
    }
    for name in TRACE_NAMES:
        field = TRACE_DIGEST_FIELDS[name]
        _require(
            comparison.get(field) == _trace_digest(vectors[name]),
            f"seat {seat} {field} mismatch",
        )

    derived = {
        "first_candidate_action_divergence_step": _first_diff(
            vectors["left_candidate"], vectors["right_candidate"], "action_sha256"
        ),
        "first_candidate_observation_divergence_step": _first_diff(
            vectors["left_candidate"], vectors["right_candidate"], "observation_sha256"
        ),
        "first_opponent_action_divergence_step": _first_diff(
            vectors["left_opponent"], vectors["right_opponent"], "action_sha256"
        ),
        "first_opponent_observation_divergence_step": _first_diff(
            vectors["left_opponent"], vectors["right_opponent"], "observation_sha256"
        ),
    }
    for field, expected in derived.items():
        reported = _optional_step(comparison.get(field), f"seat {seat} {field}")
        _require(
            reported == expected,
            f"seat {seat} {field} inconsistent with trace vectors",
        )

    candidate_action = derived["first_candidate_action_divergence_step"]
    candidate_observation = derived["first_candidate_observation_divergence_step"]
    opponent_action = derived["first_opponent_action_divergence_step"]
    opponent_observation = derived["first_opponent_observation_divergence_step"]
    action_points = [
        step for step in (candidate_action, opponent_action) if step is not None
    ]
    expected_first = min(action_points) if action_points else None
    reported_first = comparison.get("first_any_action_divergence_step")
    if reported_first is not None:
        _optional_step(reported_first, f"seat {seat} first_any_action_divergence_step")
    _require(
        reported_first == expected_first,
        f"seat {seat} first action divergence summary inconsistent",
    )
    _require(
        type(comparison.get("all_actions_identical")) is bool,
        f"seat {seat} all_actions_identical missing",
    )
    _require(
        comparison["all_actions_identical"] is (expected_first is None),
        f"seat {seat} all_actions_identical inconsistent",
    )

    expected_causal = (
        candidate_action is not None
        and (opponent_action is None or candidate_action < opponent_action)
        and (
            candidate_observation is None
            or candidate_observation > candidate_action
        )
        and (
            opponent_observation is None
            or opponent_observation > candidate_action
        )
    )
    reported_causal = comparison.get("candidate_action_is_first_observed_divergence")
    _require(
        type(reported_causal) is bool,
        f"seat {seat} causal divergence label missing",
    )
    _require(
        reported_causal is expected_causal,
        f"seat {seat} causal divergence label inconsistent",
    )
    return expected_first, expected_causal


def validate(report: dict[str, Any]) -> dict[str, Any]:
    _require(type(report) is dict, "report must be a JSON object")
    _require(report.get("schema") == SCHEMA, "unexpected report schema")

    claimed_report_sha = report.get("report_sha256")
    _require(isinstance(claimed_report_sha, str), "report_sha256 missing")
    unsigned = dict(report)
    unsigned.pop("report_sha256", None)
    _require(_digest(unsigned) == claimed_report_sha, "report_sha256 mismatch")

    authority = report.get("authority")
    _require(type(authority) is dict, "authority must be an object")
    _require(report.get("authority_sha256") == _digest(authority), "authority_sha256 mismatch")
    _require(_sha_from_authority(authority, "evaluator") == EXPECTED["evaluator"], "wrong evaluator")
    _require(_sha_from_authority(authority, "loader") == EXPECTED["loader"], "wrong loader")
    _require(authority.get("engine_sha256") == EXPECTED["engine"], "wrong engine authority")
    _require(_sha_from_authority(authority, "left_archive") == EXPECTED["left_archive"], "wrong V3.1 archive")
    _require(_sha_from_authority(authority, "right_archive") == EXPECTED["right_archive"], "wrong production-v3 archive")
    _require(authority.get("left_entry_sha256") == EXPECTED["left_entry"], "wrong V3.1 entry")
    _require(authority.get("right_entry_sha256") == EXPECTED["right_entry"], "wrong production-v3 entry")
    _require(authority.get("opponent_entry_sha256") == EXPECTED["opponent_entry"], "wrong Apex entry")
    _require(authority.get("seed") == EXPECTED["seed"], "wrong seed")
    _require(authority.get("rng_seed") == EXPECTED["rng_seed"], "wrong RNG seed")
    _require(authority.get("seats") == EXPECTED["seats"], "wrong seat panel")
    _require(authority.get("timeouts") == EXPECTED["timeouts"], "wrong timeout authority")

    rows = report.get("rows")
    _require(type(rows) is list and len(rows) == 2, "expected exactly two seat rows")
    by_seat: dict[int, dict[str, Any]] = {}
    for row in rows:
        _require(type(row) is dict, "row must be an object")
        seat = row.get("candidate_seat")
        _require(type(seat) is int and seat in (0, 1) and seat not in by_seat, "invalid/duplicate candidate seat")
        by_seat[seat] = row
    _require(set(by_seat) == {0, 1}, "both candidate seats are required")

    first_steps: dict[str, int] = {}
    causal_by_seat: dict[str, bool] = {}
    for seat in (0, 1):
        row = by_seat[seat]
        expected = EXPECTED_SCORES[seat]
        for side in ("left", "right"):
            result = row.get(f"{side}_result")
            _require(type(result) is dict, f"seat {seat} {side}_result missing")
            _require(result.get("status") == "complete", f"seat {seat} {side} incomplete")
            _require(result.get("candidate_seat") == seat, f"seat {seat} {side} candidate_seat mismatch")
            _require(result.get("scores") == expected[side], f"seat {seat} {side} terminal score mismatch")
            _require(result.get("steps") == EXPECTED["steps"], f"seat {seat} {side} step count mismatch")

        comparison = row.get("comparison")
        _require(type(comparison) is dict, f"seat {seat} comparison missing")
        _require(comparison.get("steps") == EXPECTED["steps"], f"seat {seat} comparison step count mismatch")
        first, causal = _validate_comparison(comparison, seat)
        _require(first is not None, f"seat {seat} lacks a real action divergence")
        first_steps[str(seat)] = first
        causal_by_seat[str(seat)] = causal

    return {
        "schema": "titan-v5-production-action-divergence-native-9901-validation/v1",
        "status": "PASS",
        "report_sha256": claimed_report_sha,
        "authority_sha256": report["authority_sha256"],
        "first_any_action_divergence_step": first_steps,
        "candidate_action_is_first_observed_divergence": causal_by_seat,
        "causal_candidate_first_both_seats": all(causal_by_seat.values()),
        "retained_terminal_scores_reproduced": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    try:
        raw = args.report.read_text(encoding="utf-8")
        report = json.loads(raw)
        result = validate(report)
    except (OSError, json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        print(f"validate_native_9901_action_witness: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
