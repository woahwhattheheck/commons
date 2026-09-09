#!/usr/bin/env python3
"""Regression: scheduled-game identity must equal exact Cartesian set.

A duplicate seed/seat row that replaces a missing scheduled seed must fail even
when aggregate cardinality (384 rows, 64 per opponent, 32/32 seats) is preserved.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Import helpers under test without executing main.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from runner import expected_keys  # type: ignore


def make_complete_game(opponent: str, seed: int, seat: int) -> dict:
    return {
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "status": "complete",
        "scores": [100.0, 90.0] if seat == 0 else [90.0, 100.0],
    }


def test_expected_keys_cartesian():
    seeds = [1, 2]
    opponents = ["a", "b"]
    keys = expected_keys(seeds, opponents)
    assert len(keys) == 8
    assert ("a", 1, 0) in keys
    assert ("b", 2, 1) in keys


def test_duplicate_replaces_missing_fails_identity():
    """Aggregate cardinality preserved but one seed duplicated and another omitted."""
    seeds = list(range(4))
    opponents = ["op1", "op2"]
    expected = expected_keys(seeds, opponents)
    assert len(expected) == 16

    games = []
    for opp in opponents:
        for seed in seeds:
            for seat in (0, 1):
                if (opp, seed, seat) == ("op1", 3, 0):
                    continue
                games.append(make_complete_game(opp, seed, seat))
    games.append(make_complete_game("op1", 0, 0))

    assert len(games) == 16
    observed = [(g["opponent"], g["seed"], g["candidate_seat"]) for g in games]
    observed_set = set(observed)
    assert len(observed) != len(observed_set)
    missing = expected - observed_set
    assert ("op1", 3, 0) in missing
    assert len(missing) == 1
    assert observed_set != expected


def test_balanced_seats_alone_insufficient():
    seeds = [10, 11]
    opponents = ["x"]
    expected = expected_keys(seeds, opponents)
    games = [
        make_complete_game("x", 10, 0),
        make_complete_game("x", 10, 0),
        make_complete_game("x", 10, 1),
        make_complete_game("x", 11, 0),
    ]
    observed = {(g["opponent"], g["seed"], g["candidate_seat"]) for g in games}
    assert observed != expected


if __name__ == "__main__":
    test_expected_keys_cartesian()
    test_duplicate_replaces_missing_fails_identity()
    test_balanced_seats_alone_insufficient()
    print("ok")
