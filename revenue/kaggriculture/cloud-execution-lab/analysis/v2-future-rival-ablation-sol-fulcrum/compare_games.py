# SPDX-License-Identifier: Apache-2.0
"""Validate the complete literal opponent × seed × seat game grid."""
from __future__ import annotations

from typing import Any

from compare_common import (
    ACTION_CAPTURE_BOUNDARY,
    ACTION_DIGEST_SCHEMA,
    CompareError,
    EXPECTED_CELLS,
    EXPECTED_OPPONENTS,
    EXPECTED_SEEDS,
    finite_number,
    require_hex,
)

def validate_games(report: dict[str, Any], arm: str) -> dict[tuple[str, int, int], dict[str, Any]]:
    games = report.get("games")
    if not isinstance(games, list) or len(games) != EXPECTED_CELLS:
        raise CompareError(f"{arm} must contain exactly {EXPECTED_CELLS} games")
    indexed: dict[tuple[str, int, int], dict[str, Any]] = {}
    for offset, game in enumerate(games):
        if not isinstance(game, dict):
            raise CompareError(f"{arm} game {offset} is not an object")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        if opponent not in EXPECTED_OPPONENTS:
            raise CompareError(f"{arm} game {offset} opponent mismatch")
        if type(seed) is not int or seed not in EXPECTED_SEEDS:
            raise CompareError(f"{arm} game {offset} seed mismatch")
        if type(seat) is not int or seat not in (0, 1):
            raise CompareError(f"{arm} game {offset} candidate seat mismatch")
        key = (opponent, seed, seat)
        if key in indexed:
            raise CompareError(f"{arm} duplicate game cell: {key}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise CompareError(f"{arm} game {key} is not complete")
        if game.get("finalization_errors"):
            raise CompareError(f"{arm} game {key} has finalization errors")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise CompareError(f"{arm} game {key} scores mismatch")
        finite_number(scores[0], f"{arm} game {key} score 0")
        finite_number(scores[1], f"{arm} game {key} score 1")
        if type(game.get("episode_steps")) is not int or game.get("episode_steps") != 720:
            raise CompareError(f"{arm} game {key} episode length mismatch")
        steps = game.get("steps")
        if type(steps) is not int or steps <= 0 or steps > 720:
            raise CompareError(f"{arm} game {key} completed-step count mismatch")
        require_hex(game.get("trace_sha256"), 64, f"{arm} game {key} trace digest")
        by_seat = game.get("action_sha256_by_seat")
        if not isinstance(by_seat, list) or len(by_seat) != 2:
            raise CompareError(f"{arm} game {key} action digest vector mismatch")
        for action_seat, digest in enumerate(by_seat):
            require_hex(digest, 64, f"{arm} game {key} action digest {action_seat}")
        candidate_digest = require_hex(
            game.get("candidate_action_sha256"), 64, f"{arm} game {key} candidate action digest"
        )
        if candidate_digest != by_seat[seat]:
            raise CompareError(f"{arm} game {key} candidate action digest is seat-detached")
        if game.get("action_digest_schema") != ACTION_DIGEST_SCHEMA:
            raise CompareError(f"{arm} game {key} action digest schema mismatch")
        if game.get("action_digest_capture") != ACTION_CAPTURE_BOUNDARY:
            raise CompareError(f"{arm} game {key} action capture boundary mismatch")
        digest_steps = game.get("action_digest_steps_by_seat")
        if (
            not isinstance(digest_steps, list)
            or len(digest_steps) != 2
            or any(type(value) is not int or value != steps for value in digest_steps)
        ):
            raise CompareError(f"{arm} game {key} seat action digests are incomplete")
        if (
            type(game.get("candidate_action_digest_steps")) is not int
            or game.get("candidate_action_digest_steps") != steps
        ):
            raise CompareError(f"{arm} game {key} candidate action digest is incomplete")
        indexed[key] = game

    expected = {
        (opponent, seed, seat)
        for opponent in EXPECTED_OPPONENTS
        for seed in EXPECTED_SEEDS
        for seat in (0, 1)
    }
    if set(indexed) != expected:
        raise CompareError(f"{arm} game grid is incomplete")
    return indexed

def _paired_identity(control: dict[str, Any], ablation: dict[str, Any]) -> None:
    for key in (
        "engine_ref",
        "engine_sha256",
        "loader_sha256",
        "evaluator_sha256",
        "opponents",
        "seeds",
        "agent_rng_seed",
        "python",
        "platform",
        "limits",
        "activation_overlay",
    ):
        if control.get(key) != ablation.get(key):
            raise CompareError(f"control/ablation execution context differs at {key}")
    if control.get("invocation_id") == ablation.get("invocation_id"):
        raise CompareError("control and ablation reused one invocation identity")
    if control["candidate"]["sha256"] == ablation["candidate"]["sha256"]:
        raise CompareError("control and ablation candidate entries are aliased")

def _score(game: dict[str, Any], seat: int) -> tuple[float, float, float]:
    own = finite_number(game["scores"][seat], "candidate score")
    rival = finite_number(game["scores"][1 - seat], "rival score")
    return own, rival, own - rival
