# SPDX-License-Identifier: Apache-2.0
"""Public-state tape-regime scorer for the V3.1 L3 opponent-conditioning question.

This module is evidence tooling only.  It deliberately never returns a runtime
permission to enable L3.  The 41-live-game harm check used a post-game
"hands agreement >= 400/719 with best tape" split; this scorer asks whether a
closely related signal can be reconstructed *online* from public observations
before L3 first matters at absolute step 648.

Only public rival fields are consumed.  Hidden rival inventory, private shed,
actions, orders, replay labels and post-game outcomes are not inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

WINDOW_START = 144
L3_START = 648
REFERENCE_MATCHES = 400
REFERENCE_STEPS = 719
REFERENCE_RATIO = REFERENCE_MATCHES / REFERENCE_STEPS
MOVES = {
    "NORTH": (0, -1),
    "SOUTH": (0, 1),
    "EAST": (1, 0),
    "WEST": (-1, 0),
}
VALID_QUADRANTS = {"NW", "NE", "SW", "SE"}


class EvidenceError(ValueError):
    """Malformed or insufficient public evidence."""


def _exact_int(value: Any) -> bool:
    return type(value) is int


def _quadrant(x: int, y: int, board_size: int) -> str:
    half = board_size // 2
    return ("N" if y < half else "S") + ("W" if x < half else "E")


def _position(value: Any, board_size: int) -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise EvidenceError("position must be a length-two sequence")
    x, y = value
    if not _exact_int(x) or not _exact_int(y):
        raise EvidenceError("position coordinates must be exact integers")
    if not (0 <= x < board_size and 0 <= y < board_size):
        raise EvidenceError("position is out of bounds")
    return x, y


@dataclass(frozen=True)
class PublicRival:
    step: int
    board_size: int
    hands: tuple[tuple[int, int], ...]
    unlocked: frozenset[str]


def _public_rival(observation: Mapping[str, Any]) -> PublicRival:
    if not isinstance(observation, Mapping):
        raise EvidenceError("observation must be an object")
    step = observation.get("step")
    player = observation.get("player")
    if not _exact_int(step) or step < 0:
        raise EvidenceError("step must be a non-negative exact integer")
    if not _exact_int(player) or player not in (0, 1):
        raise EvidenceError("player must be exact seat 0 or 1")
    farms = observation.get("farms")
    if not isinstance(farms, list) or len(farms) != 2:
        raise EvidenceError("two public farms are required")
    rival = farms[1 - player]
    if not isinstance(rival, Mapping):
        raise EvidenceError("rival farm must be an object")

    tiles = rival.get("tiles")
    if not isinstance(tiles, list) or not tiles:
        raise EvidenceError("rival tiles must be a non-empty square grid")
    board_size = len(tiles)
    if any(not isinstance(row, list) or len(row) != board_size for row in tiles):
        raise EvidenceError("rival tiles must be a square grid")

    hands_raw = rival.get("hands")
    if not isinstance(hands_raw, list):
        raise EvidenceError("rival hands must be a list")
    hands = tuple(_position(pos, board_size) for pos in hands_raw)

    unlocked_raw = rival.get("unlocked_quadrants")
    if not isinstance(unlocked_raw, list):
        raise EvidenceError("rival unlocked_quadrants must be a list")
    if any(not isinstance(q, str) or q not in VALID_QUADRANTS for q in unlocked_raw):
        raise EvidenceError("rival unlocked_quadrants contains an invalid value")
    if len(set(unlocked_raw)) != len(unlocked_raw) or "NW" not in unlocked_raw:
        raise EvidenceError("rival unlocked_quadrants is non-canonical")
    return PublicRival(step, board_size, hands, frozenset(unlocked_raw))


def _hand_action(tape: Sequence[Any], step: int, hand_index: int) -> list[Any]:
    if step < 0 or step >= len(tape):
        raise EvidenceError("tape does not cover scoring step")
    row = tape[step]
    if not isinstance(row, Mapping):
        raise EvidenceError("tape row must be an object")
    hands = row.get("hands", [])
    if not isinstance(hands, list):
        raise EvidenceError("tape hands must be a list")
    if hand_index >= len(hands):
        return ["PASS"]
    action = hands[hand_index]
    if not isinstance(action, list):
        raise EvidenceError("tape hand action must be a list")
    return action


def _predict_position(
    position: tuple[int, int],
    action: Sequence[Any],
    board_size: int,
    unlocked: frozenset[str],
) -> tuple[int, int]:
    if not action or not isinstance(action[0], str) or action[0] not in MOVES:
        return position
    dx, dy = MOVES[action[0]]
    nx, ny = position[0] + dx, position[1] + dy
    if not (0 <= nx < board_size and 0 <= ny < board_size):
        return position
    if _quadrant(nx, ny, board_size) not in unlocked:
        return position
    return nx, ny


class TapeRegimeScorer:
    """Score public rival hand transitions against each known action tape.

    Observation step ``s`` contains the position resulting from action step
    ``s-1``.  We therefore compare the observed transition with each tape row at
    ``s-1``.  Hand-count-changing transitions are excluded because HIRE success
    can depend on market execution and hidden inventory.  Zero-hand transitions
    are also excluded because they carry no route information.

    Any skipped or malformed observation permanently makes the current game
    non-gateable.  A fresh/restarted game resets the scorer.
    """

    def __init__(self, tapes: Sequence[Sequence[Any]]):
        if not isinstance(tapes, Sequence) or isinstance(tapes, (str, bytes)) or not tapes:
            raise EvidenceError("at least one tape is required")
        if any(not isinstance(t, Sequence) or isinstance(t, (str, bytes)) or len(t) < L3_START for t in tapes):
            raise EvidenceError("every tape must cover the pre-L3 scoring window")
        self.tapes = list(tapes)
        self.reset()

    def reset(self) -> None:
        self.matches = [0 for _ in self.tapes]
        self.comparisons = [0 for _ in self.tapes]
        self.last: PublicRival | None = None
        self.broken = False
        self.invalid_observations = 0
        self.excluded_hand_count_changes = 0
        self.excluded_zero_hand_steps = 0

    def observe(self, observation: Mapping[str, Any]) -> None:
        try:
            current = _public_rival(observation)
        except EvidenceError:
            self.invalid_observations += 1
            self.broken = True
            return

        if self.last is None or current.step == 0 or current.step <= self.last.step:
            self.reset()
            self.last = current
            return

        previous = self.last
        self.last = current
        if current.step != previous.step + 1:
            self.broken = True
            return
        action_step = current.step - 1
        if not (WINDOW_START <= action_step < L3_START):
            return
        if len(previous.hands) != len(current.hands):
            self.excluded_hand_count_changes += 1
            return
        if not previous.hands:
            self.excluded_zero_hand_steps += 1
            return
        if previous.board_size != current.board_size:
            self.broken = True
            return

        for tape_index, tape in enumerate(self.tapes):
            try:
                predicted = tuple(
                    _predict_position(
                        position,
                        _hand_action(tape, action_step, hand_index),
                        previous.board_size,
                        previous.unlocked,
                    )
                    for hand_index, position in enumerate(previous.hands)
                )
            except EvidenceError:
                self.broken = True
                return
            self.comparisons[tape_index] += 1
            if predicted == current.hands:
                self.matches[tape_index] += 1

    def result(self) -> dict[str, Any]:
        last_step = None if self.last is None else self.last.step
        candidates = []
        for index, (matches, comparisons) in enumerate(zip(self.matches, self.comparisons)):
            ratio = (matches / comparisons) if comparisons else None
            candidates.append({
                "tape": index,
                "matches": matches,
                "comparisons": comparisons,
                "ratio": ratio,
            })
        usable = [row for row in candidates if row["comparisons"]]
        best = max(usable, key=lambda row: (row["ratio"], row["matches"], -row["tape"])) if usable else None

        provisional = "UNKNOWN"
        if not self.broken and last_step is not None and last_step >= L3_START and best is not None:
            provisional = (
                "PROVISIONAL_TAPE_LIKE"
                if best["ratio"] >= REFERENCE_RATIO
                else "PROVISIONAL_OFF_TAPE"
            )
        return {
            "schema": "titan-v31-l3-public-tape-regime/v1",
            "window": {"action_start": WINDOW_START, "action_stop_exclusive": L3_START},
            "harm_reference": {
                "matches": REFERENCE_MATCHES,
                "steps": REFERENCE_STEPS,
                "ratio": REFERENCE_RATIO,
                "metric_equivalence_proven": False,
            },
            "last_step": last_step,
            "broken": self.broken,
            "invalid_observations": self.invalid_observations,
            "excluded_hand_count_changes": self.excluded_hand_count_changes,
            "excluded_zero_hand_steps": self.excluded_zero_hand_steps,
            "best": best,
            "candidates": candidates,
            "provisional_status": provisional,
            # Deliberately false until the 41-live-game replay packet calibrates
            # this online transition metric against the original harm labels.
            "gate_ready": False,
        }


def load_current_tapes() -> list[Any]:
    root = Path(__file__).resolve().parents[2]
    overlay = root / "candidates" / "v3" / "overlay"
    sys.path.insert(0, str(overlay))
    try:
        from r01_tapes import load_tapes  # type: ignore
        return load_tapes()
    finally:
        try:
            sys.path.remove(str(overlay))
        except ValueError:
            pass


def score_observations(observations: Sequence[Mapping[str, Any]], tapes: Sequence[Sequence[Any]] | None = None) -> dict[str, Any]:
    scorer = TapeRegimeScorer(load_current_tapes() if tapes is None else tapes)
    for observation in observations:
        scorer.observe(observation)
    return scorer.result()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observations", help="JSON file containing an observation array or {'observations': [...]} object")
    args = parser.parse_args(argv)
    payload = json.loads(Path(args.observations).read_text(encoding="utf-8"))
    if isinstance(payload, Mapping):
        payload = payload.get("observations")
    if not isinstance(payload, list):
        raise SystemExit("observation input must be a JSON array")
    result = score_observations(payload)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
