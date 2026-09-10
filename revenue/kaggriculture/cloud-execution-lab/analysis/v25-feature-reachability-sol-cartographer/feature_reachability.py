"""Pure helpers for exact-archive TITAN feature reachability and leave-one-out evidence."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import tarfile
from typing import Any, Iterable, Mapping, Sequence

FACTORS = (
    "seed",
    "funding",
    "redundant_hire",
    "market_pressure",
    "operating_stock",
    "crop_release",
    "idle_fertilizer",
    "early_capital",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def valid_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def safe_extract(archive: Path, destination: Path) -> list[str]:
    """Extract only in-root regular files/directories; reject links, devices, and duplicates."""
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)):
            raise ValueError("Archive contains duplicate member names")
        root = destination.resolve()
        regular_files: list[str] = []
        for member in members:
            if not member.name or member.name.startswith("/"):
                raise ValueError(f"Unsafe archive path: {member.name!r}")
            target = (destination / member.name).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"Unsafe archive path: {member.name!r}") from exc
            if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                raise ValueError(f"Unsupported archive member type: {member.name!r}")
            if not (member.isdir() or member.isfile()):
                raise ValueError(f"Unsupported archive member: {member.name!r}")
            if member.isfile():
                regular_files.append(member.name)
        bundle.extractall(destination, members=members, filter="data")
    return regular_files


def validate_config(config: Any, factors: Sequence[str] = FACTORS, *, require_enabled: bool = True) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise TypeError("TITAN-CONFIG.json must contain an object")
    missing = [factor for factor in factors if factor not in config]
    if missing:
        raise ValueError(f"Archive is missing feature flags: {missing}")
    non_boolean = [factor for factor in factors if not isinstance(config[factor], bool)]
    if non_boolean:
        raise TypeError(f"Feature flags must be booleans: {non_boolean}")
    disabled = [factor for factor in factors if not config[factor]]
    if require_enabled and disabled:
        raise ValueError(f"Exact-current leave-one-out requires enabled baseline flags: {disabled}")
    return dict(config)


def find_config_references(runtime: Path, factors: Sequence[str] = FACTORS) -> dict[str, list[dict[str, Any]]]:
    """Find active-source config references without importing agent code.

    The scan excludes packaged checks, historical fixtures, and tests. A match must
    contain both the exact factor token and a config/cfg token on the same source line.
    It is a conservative source-reachability screen, not proof of runtime activation.
    """
    references: dict[str, list[dict[str, Any]]] = {factor: [] for factor in factors}
    factor_patterns = {
        factor: re.compile(rf"(?<![A-Za-z0-9_]){re.escape(factor)}(?![A-Za-z0-9_])")
        for factor in factors
    }
    for path in sorted(runtime.rglob("*.py")):
        relative = path.relative_to(runtime)
        parts = set(relative.parts)
        if "checks" in parts or "historical" in parts or path.name.startswith("test_"):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, 1):
            lowered = line.lower()
            if "config" not in lowered and "cfg" not in lowered:
                continue
            for factor, pattern in factor_patterns.items():
                if pattern.search(line):
                    references[factor].append({
                        "path": relative.as_posix(),
                        "line": line_number,
                        "source": line.strip()[:300],
                    })
    return references


def variant_specs(factors: Sequence[str]) -> list[dict[str, Any]]:
    if not factors or len(factors) != len(set(factors)):
        raise ValueError("factors must be a nonempty unique sequence")
    rows: list[dict[str, Any]] = [{"name": "all_enabled", "disabled": None}]
    rows.extend({"name": f"without_{factor}", "disabled": factor} for factor in factors)
    return rows


def materialize_variants(
    base: Path,
    destination: Path,
    factors: Sequence[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config_path = base / "TITAN-CONFIG.json"
    config = validate_config(json.loads(config_path.read_text(encoding="utf-8")), factors)
    rows = variant_specs(factors)
    for row in rows:
        root = destination / row["name"]
        shutil.copytree(base, root)
        built = dict(config)
        if row["disabled"] is not None:
            built[row["disabled"]] = False
        changed = [key for key in factors if built[key] != config[key]]
        expected = [] if row["disabled"] is None else [row["disabled"]]
        if changed != expected:
            raise AssertionError(f"Variant {row['name']} changed {changed}, expected {expected}")
        write_json(root / "TITAN-CONFIG.json", built)
        row["config_sha256"] = sha256_file(root / "TITAN-CONFIG.json")
        row["candidate"] = str((root / "main.py").resolve()) + "::agent"
    return rows, config


def max_scheduled_agent_calls(game_count: int, episode_steps: int, actors: int = 2) -> int:
    """Return a hard upper bound because the official driver calls every actor once per step."""
    if not all(isinstance(value, int) and value > 0 for value in (game_count, episode_steps, actors)):
        raise ValueError("game_count, episode_steps, and actors must be positive integers")
    return game_count * episode_steps * actors


def game_key(game: Mapping[str, Any]) -> tuple[str, str, int, int]:
    return (
        str(game.get("variant")),
        str(game.get("opponent")),
        int(game.get("seed")),
        int(game.get("candidate_seat")),
    )


def margin(game: Mapping[str, Any]) -> float:
    seat = int(game["candidate_seat"])
    return float(game["scores"][seat]) - float(game["scores"][1 - seat])


def own_score(game: Mapping[str, Any]) -> float:
    return float(game["scores"][int(game["candidate_seat"])])


def rival_score(game: Mapping[str, Any]) -> float:
    return float(game["scores"][1 - int(game["candidate_seat"])])


def actor_calls(game: Mapping[str, Any]) -> int:
    actors = game.get("actors")
    if not isinstance(actors, list) or len(actors) != 2:
        raise AssertionError("Each game requires two actor receipts")
    calls = [actor.get("calls") if isinstance(actor, dict) else None for actor in actors]
    if not all(isinstance(value, int) and value >= 0 for value in calls):
        raise AssertionError(f"Invalid actor call counts: {calls}")
    return int(sum(calls))


def validate_games(
    games: Sequence[Mapping[str, Any]],
    variants: Sequence[Mapping[str, Any]],
    opponents: Sequence[str],
    seeds: Sequence[int],
    seats: Sequence[int] = (0, 1),
) -> None:
    expected = {
        (str(row["name"]), opponent, int(seed), int(seat))
        for row in variants for opponent in opponents for seed in seeds for seat in seats
    }
    if len(games) != len(expected):
        raise AssertionError(f"Expected {len(expected)} games, received {len(games)}")
    observed: set[tuple[str, str, int, int]] = set()
    for game in games:
        key = game_key(game)
        if key in observed:
            raise AssertionError(f"Duplicate game cell: {key}")
        observed.add(key)
        scores = game.get("scores")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise AssertionError(f"Incomplete game cell: {key}; {game.get('failure')}")
        if not isinstance(scores, list) or len(scores) != 2 or not all(
            isinstance(score, (int, float)) and math.isfinite(score) for score in scores
        ):
            raise AssertionError(f"Invalid terminal scores: {key}")
        if game.get("steps") != game.get("episode_steps") - 1:
            raise AssertionError(f"Invalid terminal step receipt: {key}")
        if not valid_hash(game.get("trace_sha256")):
            raise AssertionError(f"Invalid trace digest: {key}")
        actor_calls(game)
    if observed != expected:
        raise AssertionError(f"Cell mismatch; missing={sorted(expected - observed)[:3]}")


def mean(values: Iterable[float]) -> float | None:
    values = list(values)
    return statistics.mean(values) if values else None


def outcome(game: Mapping[str, Any]) -> str:
    value = margin(game)
    if value > 0:
        return "win"
    if value < 0:
        return "loss"
    return "tie"


def _classify(pairs: Sequence[Mapping[str, Any]], changed: int) -> str:
    """Classify only economically safe one-factor evidence.

    Margin alone is not enough: a disabled arm can improve relative margin while
    reducing TITAN's own terminal cash. `investigate_disable` therefore requires
    cellwise nonnegative own-cash and margin deltas, at least one strict own-cash
    gain, and no new losses or lost wins. `retain_enabled` is the symmetric signal.
    Everything else remains mixed/neutral for another panel.
    """
    if changed == 0:
        return "panel_inert"
    own = [float(row["disabled_minus_enabled_own"]) for row in pairs]
    margins = [float(row["disabled_minus_enabled_margin"]) for row in pairs]
    new_losses = sum(bool(row["new_loss"]) for row in pairs)
    lost_wins = sum(bool(row["lost_win"]) for row in pairs)
    new_wins = sum(bool(row["new_win"]) for row in pairs)
    recovered_losses = sum(bool(row["recovered_loss"]) for row in pairs)
    if (
        own
        and all(value >= 0 for value in own)
        and any(value > 0 for value in own)
        and all(value >= 0 for value in margins)
        and new_losses == 0
        and lost_wins == 0
    ):
        return "investigate_disable"
    if (
        own
        and all(value <= 0 for value in own)
        and any(value < 0 for value in own)
        and all(value <= 0 for value in margins)
        and new_wins == 0
        and recovered_losses == 0
    ):
        return "retain_enabled"
    return "mixed_or_neutral"


def summarize(
    games: Sequence[Mapping[str, Any]],
    factors: Sequence[str],
    source_references: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    index = {game_key(game): game for game in games}
    cells = sorted({(str(g["opponent"]), int(g["seed"]), int(g["candidate_seat"])) for g in games})
    by_factor: dict[str, Any] = {}
    for factor in factors:
        pairs = []
        for opponent, seed, seat in cells:
            enabled = index[("all_enabled", opponent, seed, seat)]
            disabled = index[(f"without_{factor}", opponent, seed, seat)]
            enabled_outcome = outcome(enabled)
            disabled_outcome = outcome(disabled)
            pairs.append({
                "opponent": opponent,
                "seed": seed,
                "candidate_seat": seat,
                "trace_changed": enabled["trace_sha256"] != disabled["trace_sha256"],
                "disabled_minus_enabled_margin": margin(disabled) - margin(enabled),
                "disabled_minus_enabled_own": own_score(disabled) - own_score(enabled),
                "disabled_minus_enabled_rival": rival_score(disabled) - rival_score(enabled),
                "enabled_outcome": enabled_outcome,
                "disabled_outcome": disabled_outcome,
                "outcome_transition": f"{enabled_outcome}->{disabled_outcome}",
                "new_loss": enabled_outcome != "loss" and disabled_outcome == "loss",
                "lost_win": enabled_outcome == "win" and disabled_outcome != "win",
                "new_win": enabled_outcome != "win" and disabled_outcome == "win",
                "recovered_loss": enabled_outcome == "loss" and disabled_outcome != "loss",
                "enabled_scores": enabled["scores"],
                "disabled_scores": disabled["scores"],
            })
        changed = sum(bool(row["trace_changed"]) for row in pairs)
        margin_deltas = [float(row["disabled_minus_enabled_margin"]) for row in pairs]
        own_deltas = [float(row["disabled_minus_enabled_own"]) for row in pairs]
        rival_deltas = [float(row["disabled_minus_enabled_rival"]) for row in pairs]
        new_losses = sum(bool(row["new_loss"]) for row in pairs)
        lost_wins = sum(bool(row["lost_win"]) for row in pairs)
        new_wins = sum(bool(row["new_win"]) for row in pairs)
        recovered_losses = sum(bool(row["recovered_loss"]) for row in pairs)
        transitions: dict[str, int] = {}
        for row in pairs:
            key = str(row["outcome_transition"])
            transitions[key] = transitions.get(key, 0) + 1
        classification = _classify(pairs, changed)
        by_factor[factor] = {
            "source_reference_count": len(source_references.get(factor, ())),
            "source_references": list(source_references.get(factor, ())),
            "matched_cells": len(pairs),
            "trace_changed_cells": changed,
            "trace_change_rate": changed / len(pairs) if pairs else 0.0,
            "mean_disabled_minus_enabled_own": mean(own_deltas),
            "min_disabled_minus_enabled_own": min(own_deltas) if own_deltas else None,
            "max_disabled_minus_enabled_own": max(own_deltas) if own_deltas else None,
            "own_positive_zero_negative_cells": {
                "positive": sum(value > 0 for value in own_deltas),
                "zero": sum(value == 0 for value in own_deltas),
                "negative": sum(value < 0 for value in own_deltas),
            },
            "mean_disabled_minus_enabled_margin": mean(margin_deltas),
            "min_disabled_minus_enabled_margin": min(margin_deltas) if margin_deltas else None,
            "max_disabled_minus_enabled_margin": max(margin_deltas) if margin_deltas else None,
            "mean_disabled_minus_enabled_rival": mean(rival_deltas),
            "new_losses": new_losses,
            "lost_wins": lost_wins,
            "new_wins": new_wins,
            "recovered_losses": recovered_losses,
            "outcome_transitions": transitions,
            "score_safety_gates": {
                "nonnegative_own_every_cell": bool(own_deltas) and all(value >= 0 for value in own_deltas),
                "strict_positive_own_some_cell": any(value > 0 for value in own_deltas),
                "nonnegative_margin_every_cell": bool(margin_deltas) and all(value >= 0 for value in margin_deltas),
                "zero_new_losses": new_losses == 0,
                "zero_lost_wins": lost_wins == 0,
            },
            "classification": classification,
            "possible_shadow_or_unreached_in_panel": bool(source_references.get(factor)) and changed == 0,
            "promotion_authority": False,
            "pairs": pairs,
        }
    calls = sum(actor_calls(game) for game in games)
    return {
        "classification_policy": "pareto_safe_own_cash_margin_and_outcome_v1",
        "factor_results": by_factor,
        "candidate_disable": [factor for factor, row in by_factor.items() if row["classification"] == "investigate_disable"],
        "candidate_keep": [factor for factor, row in by_factor.items() if row["classification"] == "retain_enabled"],
        "panel_inert": [factor for factor, row in by_factor.items() if row["classification"] == "panel_inert"],
        "needs_more_evidence": [factor for factor, row in by_factor.items() if row["classification"] == "mixed_or_neutral"],
        "observed_agent_calls": calls,
        "complete_games": len(games),
    }


def markdown(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# TITAN V2.5 exact feature reachability / leave-one-out",
        "",
        f"- Runner head: `{report.get('runner_head')}`",
        f"- Archive: `{report['archive']['sha256']}` ({report['archive']['bytes']} bytes)",
        f"- Internal source receipt: `{report['archive']['source_manifest_sha256']}`",
        f"- Engine: `{report['engine']['ref']}`",
        f"- Games: **{summary['complete_games']} complete**",
        f"- Agent calls: **{summary['observed_agent_calls']} / {report['limits']['max_agent_calls']}**",
        f"- Classification policy: `{summary['classification_policy']}`",
        "",
        "| Feature disabled | Source refs | Trace changed | Mean own delta | Mean margin delta | New losses | Lost wins | Classification |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for factor in report["tested_factors"]:
        row = summary["factor_results"][factor]
        lines.append(
            f"| `{factor}` | {row['source_reference_count']} | "
            f"{row['trace_changed_cells']}/{row['matched_cells']} | "
            f"{row['mean_disabled_minus_enabled_own']:.3f} | "
            f"{row['mean_disabled_minus_enabled_margin']:.3f} | "
            f"{row['new_losses']} | {row['lost_wins']} | `{row['classification']}` |"
        )
    lines += [
        "",
        "Positive deltas mean the disabled arm finished above the exact all-enabled control in the same opponent/seed/seat cell.",
        "`investigate_disable` requires nonnegative TITAN own-cash and margin deltas in every matched cell, at least one strict own-cash gain, zero new losses, and zero lost wins.",
        "`retain_enabled` is the symmetric one-sided signal. Margin-only improvement is never enough to recommend a disable.",
        "All classifications are development-panel routing signals only: no default change, held result, hosted-score estimate, or promotion authority follows automatically.",
        "Source references prove only a packaged code/config dependency; trace equality in this panel does not prove global inertness.",
        "",
    ]
    return "\n".join(lines)
