# SPDX-License-Identifier: Apache-2.0
"""Generic returned-action tracing for the E20 matched-game evidence runner.

The evaluator-observation pattern is copied from merged current evidence source
`candidates/v5/v4-feed-stock-ablation/feed_stock_ablation.py` Git blob
`5dc273dcbfaf07d69b2ded7de672bfd003d7454d`.  This module carries no feed-stock
policy semantics: it only hashes action traces, finds the first divergence,
wraps `Actor.act` while one candidate game executes, and validates terminal
scores.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json

SOURCE_PATTERN_GIT_BLOB = "5dc273dcbfaf07d69b2ded7de672bfd003d7454d"


def encoded(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def action_trace_sha256(actions: list[dict]) -> str:
    digest = hashlib.sha256()
    for step, action in enumerate(actions):
        digest.update(encoded({"step": step, "action": action}))
    return digest.hexdigest()


def first_action_divergence(control: list[dict], treatment: list[dict]):
    upto = min(len(control), len(treatment))
    for step in range(upto):
        if control[step] != treatment[step]:
            return {
                "step": step,
                "control": deepcopy(control[step]),
                "e20_detour_off": deepcopy(treatment[step]),
            }
    if len(control) != len(treatment):
        return {
            "step": upto,
            "control": deepcopy(control[upto]) if upto < len(control) else None,
            "e20_detour_off": (
                deepcopy(treatment[upto]) if upto < len(treatment) else None
            ),
        }
    return None


def play_with_candidate_trace(evaluator, *args, candidate_spec: str, **kwargs):
    """Observe candidate returned actions without modifying evidence bytes."""
    captured: list[dict] = []
    original = evaluator.Actor.act

    def traced(actor, observation, configuration, timeout):
        response = original(actor, observation, configuration, timeout)
        if actor.spec == candidate_spec and response.get("kind") == "action":
            captured.append(deepcopy(response["action"]))
        return response

    evaluator.Actor.act = traced
    try:
        game = evaluator.play(*args, **kwargs)
    finally:
        evaluator.Actor.act = original
    return game, captured


def game_scores(game: dict, seat: int):
    if type(seat) is not int or seat not in (0, 1):
        raise ValueError("seat must be 0 or 1")
    if game.get("status") != "complete" or game.get("steps") != 719:
        return None
    scores = game.get("scores")
    if not isinstance(scores, list) or len(scores) != 2:
        return None
    own, rival = scores[seat], scores[1 - seat]
    if (isinstance(own, bool) or isinstance(rival, bool)
            or not isinstance(own, (int, float))
            or not isinstance(rival, (int, float))):
        return None
    return {"own": own, "rival": rival, "margin": own - rival}
