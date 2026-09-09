# SPDX-License-Identifier: Apache-2.0
"""Bind delayed-rival reports to the exact workflow runtime and lifecycle."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
BASE_COMPARATOR = HERE / "compare.py"
EXPECTED_BASE_COMPARATOR_BLOB = "02081854c9eec31667b3399fff476d7a9e20e25a"
EXPECTED_LIMITS = {
    "action_rpc_seconds": 1.0,
    "startup_seconds": 15.0,
    "game_seconds_between_steps": 180.0,
    "remaining_overage_time": 0,
}
EXPECTED_METHOD = (
    "Official interpreter with explicit driver; not hosted Kaggle scoring. "
    "Decision timings are child-reported; RPC deadlines are parent-enforced. "
    "Resource samples combine child rusage, available Linux procfs, and final "
    "wait4 usage when supported; actor provenance records the actual sources. "
    "Entry-file hashes do not cover arbitrary agent dependencies."
)
EXPECTED_GAMES = 16
EXPECTED_EPISODE_STEPS = 720
EXPECTED_ACTION_STEPS = 719
_HEX = frozenset("0123456789abcdef")


class RuntimeCustodyError(ValueError):
    """The report is detached from the workflow runtime or full lifecycle."""


def git_blob_sha1(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def _load_base() -> ModuleType:
    try:
        data = BASE_COMPARATOR.read_bytes()
    except OSError as exc:
        raise RuntimeCustodyError(
            f"delayed-rival comparator is unavailable: {BASE_COMPARATOR}: {exc}"
        ) from exc
    actual = git_blob_sha1(data)
    if actual != EXPECTED_BASE_COMPARATOR_BLOB:
        raise RuntimeCustodyError(
            "delayed-rival comparator drift: "
            f"expected {EXPECTED_BASE_COMPARATOR_BLOB}, got {actual}"
        )
    spec = importlib.util.spec_from_file_location(
        "_sol_meridian_delayed_rival_comparator",
        BASE_COMPARATOR,
    )
    if spec is None or spec.loader is None:
        raise RuntimeCustodyError("cannot construct delayed-rival comparator import")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strict_object(path: Path) -> dict[str, Any]:
    base = _load_base()
    try:
        return base.strict_object(path)
    except base.CompareError as exc:
        raise RuntimeCustodyError(str(exc)) from exc


def _validate_limits(value: Any, label: str) -> dict[str, float | int]:
    if not isinstance(value, Mapping) or set(value) != set(EXPECTED_LIMITS):
        raise RuntimeCustodyError(f"{label} limits do not match the workflow schema")
    for key, expected in EXPECTED_LIMITS.items():
        actual = value.get(key)
        expected_type = float if isinstance(expected, float) else int
        if type(actual) is not expected_type or actual != expected:
            raise RuntimeCustodyError(
                f"{label} limit {key} does not match the exact workflow value"
            )
    return dict(EXPECTED_LIMITS)


def _validate_invocation_id(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 32
        or any(char not in _HEX for char in value)
    ):
        raise RuntimeCustodyError(
            f"{label} invocation_id is not 32 lowercase hexadecimal characters"
        )
    return value


def validate_runtime_custody(
    report: Mapping[str, Any],
    label: str,
) -> dict[str, Any]:
    """Require the exact evaluator runtime, final report, and 720/719 lifecycle."""
    if not isinstance(report, Mapping):
        raise RuntimeCustodyError(f"{label} report is not an object")
    limits = _validate_limits(report.get("limits"), label)
    if report.get("method") != EXPECTED_METHOD:
        raise RuntimeCustodyError(f"{label} method does not match the pinned evaluator")
    if report.get("python") != sys.version:
        raise RuntimeCustodyError(
            f"{label} Python identity does not match the classifier process"
        )
    if report.get("platform") != sys.platform:
        raise RuntimeCustodyError(
            f"{label} platform does not match the classifier process"
        )
    invocation_id = _validate_invocation_id(report.get("invocation_id"), label)

    progress = report.get("progress")
    expected_progress = {
        "state": "complete",
        "phase": "finalize",
        "planned_games": EXPECTED_GAMES,
        "recorded_games": EXPECTED_GAMES,
        "active_game": None,
    }
    if not isinstance(progress, Mapping):
        raise RuntimeCustodyError(f"{label} final progress receipt is missing")
    for key, expected in expected_progress.items():
        actual = progress.get(key)
        if type(actual) is not type(expected) or actual != expected:
            raise RuntimeCustodyError(
                f"{label} progress {key} does not prove a finalized full panel"
            )

    games = report.get("games")
    if not isinstance(games, list) or len(games) != EXPECTED_GAMES:
        raise RuntimeCustodyError(
            f"{label} must contain exactly {EXPECTED_GAMES} game records"
        )
    for index, game in enumerate(games):
        if not isinstance(game, Mapping):
            raise RuntimeCustodyError(f"{label} game {index} is not an object")
        episode_steps = game.get("episode_steps")
        action_steps = game.get("steps")
        if type(episode_steps) is not int or episode_steps != EXPECTED_EPISODE_STEPS:
            raise RuntimeCustodyError(
                f"{label} game {index} episode_steps is not "
                f"{EXPECTED_EPISODE_STEPS}"
            )
        if type(action_steps) is not int or action_steps != EXPECTED_ACTION_STEPS:
            raise RuntimeCustodyError(
                f"{label} game {index} steps is not {EXPECTED_ACTION_STEPS}"
            )

    return {
        "limits": limits,
        "method": EXPECTED_METHOD,
        "python": sys.version,
        "platform": sys.platform,
        "invocation_id": invocation_id,
        "progress": expected_progress,
        "episode_steps": EXPECTED_EPISODE_STEPS,
        "action_steps": EXPECTED_ACTION_STEPS,
    }


def compare(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    receipt: Mapping[str, Any],
    *,
    git_head: str,
) -> dict[str, Any]:
    control_runtime = validate_runtime_custody(control, "control")
    candidate_runtime = validate_runtime_custody(candidate, "candidate")
    if control_runtime["invocation_id"] == candidate_runtime["invocation_id"]:
        raise RuntimeCustodyError(
            "control and candidate reports reuse one evaluator invocation_id"
        )

    base = _load_base()
    try:
        report = base.compare(
            control,
            candidate,
            receipt,
            git_head=git_head,
        )
    except base.CompareError as exc:
        raise RuntimeCustodyError(str(exc)) from exc
    report["runtime_custody"] = {
        "schema_version": 1,
        "limits": control_runtime["limits"],
        "method": control_runtime["method"],
        "python": control_runtime["python"],
        "platform": control_runtime["platform"],
        "control_invocation_id": control_runtime["invocation_id"],
        "candidate_invocation_id": candidate_runtime["invocation_id"],
        "final_progress": control_runtime["progress"],
        "episode_steps": control_runtime["episode_steps"],
        "action_steps": control_runtime["action_steps"],
    }
    return report


def markdown(report: Mapping[str, Any]) -> str:
    return _load_base().markdown(report)


def atomic_write(path: Path, text: str) -> None:
    _load_base().atomic_write(path, text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = compare(
            strict_object(args.control),
            strict_object(args.candidate),
            strict_object(args.receipt),
            git_head=args.head,
        )
    except RuntimeCustodyError as exc:
        report = {
            "schema_version": 1,
            "operation": "titan-v2-delayed-rival-ablation-20260909-sol-caliber-01",
            "git_head": args.head,
            "verdict": "INVALID",
            "reason": str(exc),
            "exit_code": 2,
        }
    atomic_write(
        args.output,
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )
    atomic_write(args.markdown, markdown(report))
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "reason": report["reason"],
                "exit_code": report["exit_code"],
                "overall": report.get("overall"),
                "by_opponent": report.get("by_opponent"),
                "runtime_custody": report.get("runtime_custody"),
            },
            sort_keys=True,
        )
    )
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
