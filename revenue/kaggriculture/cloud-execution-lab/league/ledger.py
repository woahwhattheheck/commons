# SPDX-License-Identifier: Apache-2.0
"""Elo/lean ledger for the TITAN v3 adversarial league.

Every weekly round-robin rates both sides of each game: contestants
(canonical v3 + registered challengers) and the vendored public-opponent
bank.  The ledger persists under ``bank/v3-adversarial/league/`` so a
fresh week can compare own-cash strata against the prior baseline and the
alarm check can detect regressions.

Elo is the classic 400-point logistic with a configurable K-factor.  The
per-game score for a side is 1/0.5/0 from the sign of the margin
(candidate own score minus rival score); ties count as half.  Alongside
Elo the ledger keeps the "lean": raw W/T/L counts and mean margin per
player, which is what humans actually read week to week.
"""
from __future__ import annotations

import copy
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA = "titan.league-ledger.v1"
DEFAULT_ELO = 1500.0
DEFAULT_K = 24.0


class LedgerError(ValueError):
    """Raised when ledger data is malformed."""


def new_ledger() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "players": {},
        "own_cash_baseline": {},
        "runs": [],
    }


def expected_score(elo_a: float, elo_b: float) -> float:
    """Logistic expected score of A against B."""
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))


def update_elo(players: dict[str, dict[str, Any]], games: Sequence[tuple[str, str, float]],
               k: float = DEFAULT_K) -> dict[str, dict[str, Any]]:
    """Apply Elo updates for a sequence of (player_a, player_b, score_a) games.

    ``score_a`` is 1.0/0.5/0.0.  Unknown players enter at DEFAULT_ELO.
    Returns the updated players dict (mutated in place and returned).
    """
    if not math.isfinite(k) or k <= 0:
        raise LedgerError("k must be a finite positive number")
    for name_a, name_b, score_a in games:
        if score_a not in (0.0, 0.5, 1.0):
            raise LedgerError(f"score_a must be 0.0/0.5/1.0, got {score_a!r}")
        for name in (name_a, name_b):
            players.setdefault(name, {"elo": DEFAULT_ELO, "games": 0,
                                      "wins": 0, "ties": 0, "losses": 0,
                                      "margin_sum": 0.0})
        elo_a = players[name_a]["elo"]
        elo_b = players[name_b]["elo"]
        exp_a = expected_score(elo_a, elo_b)
        players[name_a]["elo"] = elo_a + k * (score_a - exp_a)
        players[name_b]["elo"] = elo_b + k * ((1.0 - score_a) - (1.0 - exp_a))
    return players


def record_results(players: dict[str, dict[str, Any]],
                   games: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Fold one panel's games into W/T/L lean and Elo.

    Each game mapping needs ``contestant`` (str), ``opponent`` (str), and
    ``margin`` (contestant own score minus rival score, finite number).
    """
    elo_games: list[tuple[str, str, float]] = []
    for index, game in enumerate(games):
        contestant = game.get("contestant")
        opponent = game.get("opponent")
        margin = game.get("margin")
        if not isinstance(contestant, str) or not contestant:
            raise LedgerError(f"game {index}: contestant must be a nonempty string")
        if not isinstance(opponent, str) or not opponent:
            raise LedgerError(f"game {index}: opponent must be a nonempty string")
        if isinstance(margin, bool) or not isinstance(margin, (int, float)) or not math.isfinite(margin):
            raise LedgerError(f"game {index}: margin must be a finite number")
        for name in (contestant, opponent):
            players.setdefault(name, {"elo": DEFAULT_ELO, "games": 0,
                                      "wins": 0, "ties": 0, "losses": 0,
                                      "margin_sum": 0.0})
        for name, result in ((contestant, margin), (opponent, -margin)):
            players[name]["games"] += 1
            players[name]["margin_sum"] += result
            if result > 0:
                players[name]["wins"] += 1
            elif result == 0:
                players[name]["ties"] += 1
            else:
                players[name]["losses"] += 1
        score_a = 1.0 if margin > 0 else (0.5 if margin == 0 else 0.0)
        elo_games.append((contestant, opponent, score_a))
    return update_elo(players, elo_games)


def standings(players: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Players sorted by Elo desc, with mean margin (the lean) attached."""
    rows = []
    for name, stats in players.items():
        games = stats.get("games", 0)
        rows.append({
            "name": name,
            "elo": round(float(stats.get("elo", DEFAULT_ELO)), 1),
            "games": games,
            "wins": stats.get("wins", 0),
            "ties": stats.get("ties", 0),
            "losses": stats.get("losses", 0),
            "mean_margin": (round(float(stats.get("margin_sum", 0.0)) / games, 3)
                            if games else None),
        })
    rows.sort(key=lambda row: (-row["elo"], row["name"]))
    return rows


def load_ledger(path: str | Path) -> dict[str, Any]:
    """Load a ledger file; return a fresh ledger when the path is absent."""
    path = Path(path)
    if not path.exists():
        return new_ledger()
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise LedgerError(f"{path}: not a {SCHEMA} ledger")
    ledger = new_ledger()
    ledger.update(copy.deepcopy(data))
    return ledger


def save_ledger(path: str | Path, ledger: Mapping[str, Any]) -> None:
    """Atomic write: temp file + os.replace, so a killed run never truncates."""
    import os
    import tempfile
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=str(path.parent), delete=False) as handle:
        json.dump(ledger, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        temporary = handle.name
    os.replace(temporary, path)
