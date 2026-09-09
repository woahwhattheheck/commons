# SPDX-License-Identifier: Apache-2.0
"""Exact evaluator overlay adding pre-interpreter candidate action digests.

The pinned evaluator, loader, child workers, official interpreter calls, and every
returned action byte remain unchanged.  During each game this overlay observes a
successful parent-side ``Actor.act`` return, hashes its action before ``play`` can
assign it to engine state, then delegates the exact object unchanged.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable

CORE_EVALUATOR_GIT_BLOB = "077feb2208b6e0c1727835eb4f8089709bf67f3b"
ACTION_DIGEST_SCHEMA = "sha256(length_u64be || canonical_json({step,action}))"
ACTION_CAPTURE_BOUNDARY = "parent_actor_success_return_before_engine_interpreter"
HERE = Path(__file__).resolve().parent


class OverlayError(ValueError):
    """The pinned evaluator or overlay installation violated its contract."""


def git_blob_bytes(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data,
        usedforsecurity=False,
    ).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ActionDigestTracker:
    """Length-framed action digests with literal seat and sequence custody."""

    def __init__(self, encoder: Callable[[Any], bytes]):
        self.encoder = encoder
        self.hashes = [hashlib.sha256(), hashlib.sha256()]
        self.counts = [0, 0]

    def record(self, seat: int, step: int, action: Any) -> None:
        if type(seat) is not int or seat not in (0, 1):
            raise OverlayError(f"invalid action seat: {seat!r}")
        if type(step) is not int or step != self.counts[seat]:
            raise OverlayError(
                f"non-contiguous action step for seat {seat}: "
                f"expected {self.counts[seat]}, got {step!r}"
            )
        payload = self.encoder({"step": step, "action": action})
        if not isinstance(payload, bytes):
            raise OverlayError("core canonical encoder did not return bytes")
        self.hashes[seat].update(len(payload).to_bytes(8, "big"))
        self.hashes[seat].update(payload)
        self.counts[seat] += 1

    def hexdigests(self) -> list[str]:
        return [value.hexdigest() for value in self.hashes]


def _observation_step(observation: Any) -> int:
    if isinstance(observation, dict):
        value = observation.get("step")
    else:
        value = getattr(observation, "step", None)
    if type(value) is not int:
        raise OverlayError(f"actor observation step is not a literal int: {value!r}")
    return value


def wrapped_play(
    core: ModuleType,
    original_play: Callable[..., dict[str, Any]],
    original_actor_act: Callable[..., dict[str, Any]],
    original_encoded: Callable[[Any], bytes],
) -> Callable[..., dict[str, Any]]:
    """Wrap one game while restoring ``Actor.act`` on every exit path."""

    def play(*args: Any, **kwargs: Any) -> dict[str, Any]:
        tracker = ActionDigestTracker(original_encoded)
        actor_seats: dict[int, int] = {}
        if core.Actor.act is not original_actor_act:
            raise OverlayError("core evaluator Actor.act was already replaced")

        def observed_act(actor: Any, observation: Any, configuration: Any, timeout: float):
            result = original_actor_act(actor, observation, configuration, timeout)
            if isinstance(result, dict) and result.get("kind") == "action":
                identity = id(actor)
                if identity not in actor_seats:
                    if len(actor_seats) >= 2:
                        raise OverlayError("more than two actors observed in one game")
                    actor_seats[identity] = len(actor_seats)
                seat = actor_seats[identity]
                # This executes before play() receives the response, assigns the
                # action to state, or calls the official engine interpreter.
                tracker.record(seat, _observation_step(observation), result.get("action"))
            return result

        core.Actor.act = observed_act
        try:
            result = original_play(*args, **kwargs)
        finally:
            core.Actor.act = original_actor_act
        if not isinstance(result, dict):
            raise OverlayError("core play did not return an object")
        digests = tracker.hexdigests()
        seat = result.get("candidate_seat")
        if type(seat) is not int or seat not in (0, 1):
            raise OverlayError("core play returned an invalid candidate seat")
        result["action_sha256_by_seat"] = digests
        result["candidate_action_sha256"] = digests[seat]
        result["action_digest_steps_by_seat"] = list(tracker.counts)
        result["candidate_action_digest_steps"] = tracker.counts[seat]
        result["action_digest_schema"] = ACTION_DIGEST_SCHEMA
        result["action_digest_capture"] = ACTION_CAPTURE_BOUNDARY
        return result

    return play


def install(core: ModuleType) -> None:
    if getattr(core, "_fulcrum_activation_overlay", False):
        raise OverlayError("activation overlay already installed")
    original_encoded = core.encoded
    original_play = core.play
    original_actor_act = core.Actor.act
    original_write_report = core.write_report
    overlay_identity = {
        "schema_version": 1,
        "sha256": sha256(Path(__file__)),
        "core_evaluator_git_blob": CORE_EVALUATOR_GIT_BLOB,
        "action_digest_schema": ACTION_DIGEST_SCHEMA,
        "action_digest_capture": ACTION_CAPTURE_BOUNDARY,
    }

    core.play = wrapped_play(core, original_play, original_actor_act, original_encoded)

    def write_report(path: Path, report: dict[str, Any]) -> None:
        existing = report.get("activation_overlay")
        if existing is not None and existing != overlay_identity:
            raise OverlayError("report contains conflicting activation overlay identity")
        report["activation_overlay"] = dict(overlay_identity)
        original_write_report(path, report)

    core.write_report = write_report
    core._fulcrum_activation_overlay = True


def load_core(path: Path) -> ModuleType:
    data = path.read_bytes()
    actual = git_blob_bytes(data)
    if actual != CORE_EVALUATOR_GIT_BLOB:
        raise OverlayError(
            f"core evaluator Git blob drift: expected {CORE_EVALUATOR_GIT_BLOB}, got {actual}"
        )
    spec = importlib.util.spec_from_file_location("fulcrum_core_evaluator", path)
    if spec is None or spec.loader is None:
        raise OverlayError(f"cannot import core evaluator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def core_path() -> Path:
    override = os.environ.get("FULCRUM_CORE_EVALUATOR")
    if override:
        return Path(override).resolve(strict=True)
    return (HERE.parents[2] / "cloud-eval" / "evaluate.py").resolve(strict=True)


def main() -> int:
    core = load_core(core_path())
    install(core)
    result = core.main()
    if type(result) is not int:
        raise OverlayError("core evaluator main did not return an integer")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
