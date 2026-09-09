# SPDX-License-Identifier: Apache-2.0
"""Behavior-preserving telemetry wrapper for the reserve-release candidate.

The wrapped candidate computes the returned action before this module observes
its diagnostics. Telemetry is written once, at the terminal step, outside the
repository under /tmp. No action field is added, removed, or modified.
"""
from __future__ import annotations

import atexit
from collections import Counter
import json
import os
from pathlib import Path
from typing import Any, Mapping

import candidate as wrapped

TELEMETRY_ROOT = Path("/tmp/titan-v3-reserve-activation-audit")
SEED_HINT = TELEMETRY_ROOT / "seed-hint.txt"

_REASON_COUNTS: Counter[str] = Counter()
_STEPS_WITH_CERTIFICATES: set[int] = set()
_ELIGIBLE_STEPS: set[int] = set()
_OBSERVED_FULL_STEPS: set[int] = set()
_EXACT_FULL_CERTIFICATE_STEPS: set[int] = set()
_FIRST_ELIGIBLE: list[dict[str, Any]] = []
_STATE: dict[str, Any] = {
    "schema_version": 1,
    "process_id": os.getpid(),
    "calls": 0,
    "player": None,
    "last_step": None,
    "episode_steps": None,
    "certificate_calls": 0,
    "eligible_certificates": 0,
    "malformed_certificates": 0,
    "joint_producer_busy_true_steps": 0,
    "joint_producer_busy_false_steps": 0,
    "joint_producer_busy_other_steps": 0,
}
_WRITTEN = False


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    try:
        if parsed != value:
            return None
    except Exception:
        return None
    return parsed


def _seed_hint() -> int | None:
    try:
        text = SEED_HINT.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None
    if not text:
        return None
    digits = text[1:] if text[0] in "+-" else text
    if not digits.isdigit():
        return None
    try:
        return int(text)
    except (ValueError, OverflowError):
        return None


def _shed_total(observation: Mapping[str, Any]) -> int | None:
    try:
        shed = observation["private"]["shed"]
    except (KeyError, TypeError):
        return None
    if not isinstance(shed, Mapping):
        return None
    total = 0
    for value in shed.values():
        parsed = _integer(value)
        if parsed is None:
            return None
        total += parsed
    return total


def _capture(observation: Mapping[str, Any], configuration: Mapping[str, Any] | None) -> None:
    step = _integer(observation.get("step"))
    player = _integer(observation.get("player"))
    cfg = configuration if isinstance(configuration, Mapping) else {}
    episode_steps = _integer(cfg.get("episodeSteps", 720))
    capacity = _integer(cfg.get("shedCapacity", 100))

    _STATE["calls"] += 1
    _STATE["player"] = player
    _STATE["last_step"] = step
    _STATE["episode_steps"] = episode_steps

    if step is not None and capacity is not None:
        total = _shed_total(observation)
        if total == capacity:
            _OBSERVED_FULL_STEPS.add(step)

    canonical = getattr(wrapped, "_CANONICAL", None)
    instance = getattr(canonical, "_INSTANCE", None)
    consumer = getattr(instance, "consumer", None)
    busy = getattr(consumer, "joint_producer_busy", None)
    if busy is True:
        _STATE["joint_producer_busy_true_steps"] += 1
    elif busy is False:
        _STATE["joint_producer_busy_false_steps"] += 1
    else:
        _STATE["joint_producer_busy_other_steps"] += 1

    telemetry = getattr(wrapped, "LAST_TELEMETRY", {})
    reports = telemetry.get("reserve_release", []) if isinstance(telemetry, Mapping) else []
    if not isinstance(reports, list):
        _STATE["malformed_certificates"] += 1
        return
    if reports and step is not None:
        _STEPS_WITH_CERTIFICATES.add(step)

    for report in reports:
        if not isinstance(report, Mapping):
            _STATE["malformed_certificates"] += 1
            continue
        _STATE["certificate_calls"] += 1
        reason = report.get("reason")
        _REASON_COUNTS[reason if isinstance(reason, str) and reason else "<missing>"] += 1
        report_capacity = _integer(report.get("capacity"))
        requested = _integer(report.get("current_requested_total"))
        if step is not None and report_capacity is not None and requested == report_capacity:
            _EXACT_FULL_CERTIFICATE_STEPS.add(step)
        if report.get("eligible") is True:
            _STATE["eligible_certificates"] += 1
            if step is not None:
                _ELIGIBLE_STEPS.add(step)
            if len(_FIRST_ELIGIBLE) < 12:
                _FIRST_ELIGIBLE.append(
                    {
                        "step": step,
                        "reason": reason,
                        "next_step": _integer(report.get("next_step")),
                        "capacity": report_capacity,
                        "current_requested_total": requested,
                    }
                )


def _record(complete: bool) -> dict[str, Any]:
    return {
        **_STATE,
        "seed": _seed_hint(),
        "complete": bool(complete),
        "reason_counts": dict(sorted(_REASON_COUNTS.items())),
        "steps_with_certificates": sorted(_STEPS_WITH_CERTIFICATES),
        "eligible_steps": sorted(_ELIGIBLE_STEPS),
        "observed_full_steps": sorted(_OBSERVED_FULL_STEPS),
        "exact_full_certificate_steps": sorted(_EXACT_FULL_CERTIFICATE_STEPS),
        "first_eligible": list(_FIRST_ELIGIBLE),
    }


def _write(*, complete: bool) -> None:
    global _WRITTEN
    if _WRITTEN:
        return
    TELEMETRY_ROOT.mkdir(parents=True, exist_ok=True)
    record = _record(complete)
    seed = record.get("seed")
    player = record.get("player")
    name = f"telemetry-seed-{seed}-seat-{player}-pid-{os.getpid()}.json"
    destination = TELEMETRY_ROOT / name
    temporary = TELEMETRY_ROOT / f".{name}.tmp"
    temporary.write_text(
        json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, destination)
    _WRITTEN = True


def _write_incomplete_at_exit() -> None:
    if not _WRITTEN:
        try:
            _write(complete=False)
        except Exception:
            # The evaluator already records process/action failures. Never mask
            # an earlier exception during interpreter shutdown.
            pass


atexit.register(_write_incomplete_at_exit)


def agent(observation, configuration=None):
    """Return the wrapped action unchanged and retain terminal diagnostics."""
    output = wrapped.agent(observation, configuration)
    _capture(observation, configuration)
    step = _integer(observation.get("step"))
    cfg = configuration if isinstance(configuration, Mapping) else {}
    episode_steps = _integer(cfg.get("episodeSteps", 720))
    if step is not None and episode_steps is not None and step >= episode_steps - 2:
        _write(complete=True)
    return output
