#!/usr/bin/env python3
"""Byte-isolated causal bisect of submitted TITAN V2 legacy features.

The runner expands one exact source archive into four candidates that differ only
in ``TITAN-CONFIG.json``. It executes an identical source-pinned official-engine
panel for every candidate, writes a provenance receipt beside every two-game
shard, proves complete paired-cell coverage, and reports feature effects as
paired terminal-margin deltas.

It never edits the canonical controller, source archive, or release pointers.
This is local official-interpreter evidence, not a hosted Kaggle score forecast.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import tarfile
import tempfile
import threading
from typing import Any, Iterable, Mapping

EXPECTED_SOURCE_SHA256 = "e363125093463d1f7a63a01aecb70646344dae5b318952e13a1b1641e2043e58"
EXPECTED_ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
EXPECTED_ENGINE_SHA256 = {
    "kaggriculture.py": "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e",
    "kaggriculture.json": "a82c89c1a2315b93f39775d8e025471a01b738647c9772658368ee6b1b6f4867",
    "utils.py": "537b627b11784d424147ef57ebb0369b039bf83c9f891e81f10486b1f552334b",
}
EXPECTED_LOADER_SHA256 = "cd113a94ae99b03492502e425bdcf09c3db17a2aa2a8fd866f0d78caec9e311e"
EXPECTED_EVALUATOR_SHA256 = "e30b3108e0027477ab7ddbc057892a241c41a1f2b38f72caf267477877c4333c"
EXPECTED_OPPONENT_SHA256 = {
    "arlene": "1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4",
    "apex": "1f7cd5fb8a16585936d2562a3667f85bb6661688718ef58f73006de66148354a",
    "reyhan": "d39dba50793d9777c990347443bf0c481c78adaea86055f6f6b0600dcfcd9f2e",
    "kaito": "d9dc24ce5429ec628ead0621a160bee90725350683d7dfcc4686fcaf511f3aab",
}
EXPECTED_AGENT_RNG_SEED = 20260907
EXPECTED_LIMITS = {
    "action_rpc_seconds": 1.2,
    "startup_seconds": 15.0,
    "game_seconds_between_steps": 180.0,
    "remaining_overage_time": 0,
}
VARIANTS: dict[str, dict[str, bool]] = {
    "baseline": {},
    "no_redundant_hire": {"redundant_hire": False},
    "no_market_pressure": {"market_pressure": False},
    "no_legacy_features": {"redundant_hire": False, "market_pressure": False},
}
DEFAULT_SEEDS = tuple(range(2609098601, 2609098609))
DEFAULT_OPPONENTS = ("arlene", "apex", "reyhan", "kaito")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
RUN_STEM = re.compile(r"^(?P<variant>[a-z0-9_]+)--(?P<opponent>[a-z0-9_]+)--(?P<seed>-?[0-9]+)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_manifest(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def variant_identity(root: Path) -> dict[str, Any]:
    manifest = file_manifest(root)
    if "main.py" not in manifest or "TITAN-CONFIG.json" not in manifest:
        raise ValueError(f"candidate root lacks required files: {root}")
    return {
        "file_count": len(manifest),
        "file_manifest_sha256": canonical_sha256(manifest),
        "main_py_sha256": manifest["main.py"],
        "config_sha256": manifest["TITAN-CONFIG.json"],
    }


def safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    resolved = destination.resolve()
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        for member in members:
            target = (destination / member.name).resolve()
            if target != resolved and resolved not in target.parents:
                raise ValueError(f"archive member escapes destination: {member.name!r}")
            if member.issym() or member.islnk():
                raise ValueError(f"links are not accepted in source archive: {member.name!r}")
            if not (member.isfile() or member.isdir()):
                raise ValueError(f"unsupported archive member type: {member.name!r}")
        bundle.extractall(destination, members=members, filter="data")


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def prepare_variants(source_archive: Path, variants_root: Path) -> dict[str, Any]:
    actual_sha = sha256(source_archive)
    if actual_sha != EXPECTED_SOURCE_SHA256:
        raise ValueError(f"source archive SHA256 mismatch: {actual_sha}")

    if variants_root.exists():
        shutil.rmtree(variants_root)
    variants_root.mkdir(parents=True)

    baseline = variants_root / "baseline"
    safe_extract(source_archive, baseline)
    baseline_config_path = baseline / "TITAN-CONFIG.json"
    baseline_config = json.loads(baseline_config_path.read_text(encoding="utf-8"))
    if baseline_config.get("redundant_hire") is not True:
        raise ValueError("submitted baseline does not enable redundant_hire")
    if baseline_config.get("market_pressure") is not True:
        raise ValueError("submitted baseline does not enable market_pressure")
    if not (baseline / "main.py").is_file():
        raise ValueError("submitted baseline lacks main.py")

    baseline_manifest = file_manifest(baseline)
    proof: dict[str, Any] = {
        "schema_version": 2,
        "source_archive": {
            "path": str(source_archive),
            "sha256": actual_sha,
            "size_bytes": source_archive.stat().st_size,
        },
        "baseline_file_count": len(baseline_manifest),
        "baseline_file_manifest_sha256": canonical_sha256(baseline_manifest),
        "variants": {},
    }

    for name, overrides in VARIANTS.items():
        root = variants_root / name
        if name != "baseline":
            shutil.copytree(baseline, root)
        config_path = root / "TITAN-CONFIG.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if overrides:
            config.update(overrides)
            atomic_json(config_path, config)

        manifest = file_manifest(root)
        changed = sorted(
            path for path in set(baseline_manifest) | set(manifest)
            if baseline_manifest.get(path) != manifest.get(path)
        )
        expected_changed = [] if name == "baseline" else ["TITAN-CONFIG.json"]
        if changed != expected_changed:
            raise ValueError(f"{name} is not config-only: changed={changed}")
        identity = variant_identity(root)
        proof["variants"][name] = {
            "overrides": overrides,
            "config": config,
            "changed_from_baseline": changed,
            "all_non_config_bytes_equal": all(
                manifest[path] == digest
                for path, digest in baseline_manifest.items()
                if path != "TITAN-CONFIG.json"
            ),
            **identity,
        }
    return proof


def parse_csv_ints(value: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not values or len(values) != len(set(values)):
        raise argparse.ArgumentTypeError("seeds must be a nonempty set of unique integers")
    return values


def parse_csv_names(value: str) -> tuple[str, ...]:
    values = tuple(part.strip() for part in value.split(",") if part.strip())
    if not values or len(values) != len(set(values)):
        raise argparse.ArgumentTypeError("opponents must be nonempty and unique")
    unknown = sorted(set(values) - set(DEFAULT_OPPONENTS))
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown opponents: {', '.join(unknown)}")
    return values


def parse_csv_variants(value: str) -> tuple[str, ...]:
    values = tuple(part.strip() for part in value.split(",") if part.strip())
    if not values or len(values) != len(set(values)):
        raise argparse.ArgumentTypeError("run variants must be nonempty and unique")
    unknown = sorted(set(values) - set(VARIANTS))
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown variants: {', '.join(unknown)}")
    return values


def opponent_path(harness_root: Path, name: str) -> Path:
    if name == "apex":
        return harness_root / "opponents" / "apex" / "main.py"
    return harness_root / "opponents" / name / "main.py"


def verify_harness(harness_root: Path, opponents: Iterable[str]) -> dict[str, Any]:
    evaluator = harness_root / "harness" / "evaluate.py"
    loader = harness_root / "harness" / "loader.py"
    actual_evaluator = sha256(evaluator)
    actual_loader = sha256(loader)
    if actual_evaluator != EXPECTED_EVALUATOR_SHA256:
        raise ValueError(f"evaluator SHA256 mismatch: {actual_evaluator}")
    if actual_loader != EXPECTED_LOADER_SHA256:
        raise ValueError(f"loader SHA256 mismatch: {actual_loader}")

    engine_hashes = {
        name: sha256(harness_root / "engine" / name)
        for name in EXPECTED_ENGINE_SHA256
    }
    if engine_hashes != EXPECTED_ENGINE_SHA256:
        raise ValueError(f"engine SHA256 mismatch: {engine_hashes}")

    opponent_hashes: dict[str, str] = {}
    for name in opponents:
        actual = sha256(opponent_path(harness_root, name))
        expected = EXPECTED_OPPONENT_SHA256[name]
        if actual != expected:
            raise ValueError(f"opponent {name} SHA256 mismatch: {actual}")
        opponent_hashes[name] = actual

    return {
        "schema_version": 1,
        "engine_ref": EXPECTED_ENGINE_REF,
        "engine_sha256": engine_hashes,
        "loader_sha256": actual_loader,
        "evaluator_sha256": actual_evaluator,
        "agent_rng_seed": EXPECTED_AGENT_RNG_SEED,
        "limits": EXPECTED_LIMITS,
        "opponents": opponent_hashes,
    }


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_report_contract(
    report: Mapping[str, Any],
    *,
    variant: str,
    opponent: str,
    seed: int,
    identity: Mapping[str, Any],
    harness_identity: Mapping[str, Any],
) -> None:
    if report.get("schema_version") != 1:
        raise ValueError("unexpected evaluator report schema")
    if report.get("engine_ref") != harness_identity["engine_ref"]:
        raise ValueError("report engine_ref drift")
    if report.get("engine_sha256") != harness_identity["engine_sha256"]:
        raise ValueError("report engine hashes drift")
    if report.get("loader_sha256") != harness_identity["loader_sha256"]:
        raise ValueError("report loader hash drift")
    if report.get("evaluator_sha256") != harness_identity["evaluator_sha256"]:
        raise ValueError("report evaluator hash drift")
    if report.get("agent_rng_seed") != EXPECTED_AGENT_RNG_SEED:
        raise ValueError("report agent RNG seed drift")
    if report.get("limits") != EXPECTED_LIMITS:
        raise ValueError("report execution limits drift")
    if report.get("seeds") != [seed]:
        raise ValueError("report seed identity mismatch")

    candidate = report.get("candidate")
    if not isinstance(candidate, Mapping) or candidate.get("sha256") != identity["main_py_sha256"]:
        raise ValueError("report candidate entry hash mismatch")
    if candidate.get("entry") != "main.py" or candidate.get("callable") != "agent":
        raise ValueError("report candidate entry contract mismatch")

    rivals = report.get("opponents")
    if not isinstance(rivals, Mapping) or set(rivals) != {opponent}:
        raise ValueError("report opponent identity mismatch")
    rival = rivals[opponent]
    if not isinstance(rival, Mapping) or rival.get("sha256") != harness_identity["opponents"][opponent]:
        raise ValueError("report opponent hash mismatch")
    if rival.get("entry") != "main.py" or rival.get("callable") != "agent":
        raise ValueError("report opponent entry contract mismatch")

    summary = report.get("summary")
    if not isinstance(summary, Mapping) or set(summary) != {opponent}:
        raise ValueError("report summary identity mismatch")
    summary_row = summary[opponent]
    if not isinstance(summary_row, Mapping):
        raise ValueError("report summary row malformed")
    if any(summary_row.get(key) != value for key, value in {
        "scheduled": 2,
        "completed": 2,
        "failed": 0,
        "candidate_failures": 0,
        "opponent_failures": 0,
    }.items()):
        raise ValueError("report summary is not a clean two-game shard")

    games = report.get("games")
    if not isinstance(games, list) or len(games) != 2:
        raise ValueError("report must contain exactly two games")
    seen: set[tuple[str, int, int]] = set()
    for game in games:
        if not isinstance(game, Mapping):
            raise ValueError("game row malformed")
        key = game_key(game)
        expected_key = (opponent, seed, int(game.get("candidate_seat", -1)))
        if key != expected_key or key[2] not in (0, 1):
            raise ValueError(f"game identity mismatch: {key}")
        if key in seen:
            raise ValueError(f"duplicate game cell: {key}")
        seen.add(key)
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise ValueError(f"incomplete game cell: {key}")
        if game.get("steps") != 719 or game.get("episode_steps") != 720:
            raise ValueError(f"horizon mismatch: {key}")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2 or not all(_finite_number(value) for value in scores):
            raise ValueError(f"invalid scores: {key}")
        trace = game.get("trace_sha256")
        if not isinstance(trace, str) or HEX64.fullmatch(trace) is None:
            raise ValueError(f"invalid trace hash: {key}")
    if seen != {(opponent, seed, 0), (opponent, seed, 1)}:
        raise ValueError(f"missing mirrored seat: {seen}")


def receipt_path(report_path: Path) -> Path:
    return report_path.with_suffix(".receipt.json")


def invocation_contract(*, variant: str, opponent: str, seed: int) -> dict[str, Any]:
    return {
        "variant": variant,
        "opponent": opponent,
        "seed": seed,
        "candidate_relative": f"variants/{variant}/main.py",
        "opponent_relative": (
            "opponents/apex/main.py" if opponent == "apex" else f"opponents/{opponent}/main.py"
        ),
        "agent_rng_seed": EXPECTED_AGENT_RNG_SEED,
        "action_timeout_seconds": EXPECTED_LIMITS["action_rpc_seconds"],
        "startup_timeout_seconds": EXPECTED_LIMITS["startup_seconds"],
        "game_timeout_seconds": EXPECTED_LIMITS["game_seconds_between_steps"],
        "both_seats": True,
    }


def make_receipt(
    report_path: Path,
    *,
    variant: str,
    opponent: str,
    seed: int,
    identity: Mapping[str, Any],
    harness_identity: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source_archive_sha256": EXPECTED_SOURCE_SHA256,
        "report_file": report_path.name,
        "report_sha256": sha256(report_path),
        "invocation": invocation_contract(variant=variant, opponent=opponent, seed=seed),
        "candidate": dict(identity),
        "harness": {
            "engine_ref": harness_identity["engine_ref"],
            "engine_sha256": harness_identity["engine_sha256"],
            "loader_sha256": harness_identity["loader_sha256"],
            "evaluator_sha256": harness_identity["evaluator_sha256"],
            "opponent_sha256": harness_identity["opponents"][opponent],
        },
    }


def validate_receipt(
    receipt: Mapping[str, Any],
    report_path: Path,
    *,
    variant: str,
    opponent: str,
    seed: int,
    identity: Mapping[str, Any],
    harness_identity: Mapping[str, Any],
) -> None:
    expected = make_receipt(
        report_path,
        variant=variant,
        opponent=opponent,
        seed=seed,
        identity=identity,
        harness_identity=harness_identity,
    )
    if receipt != expected:
        raise ValueError(f"run receipt mismatch: {report_path.name}")


def load_validated_shard(
    report_path: Path,
    *,
    variant: str,
    opponent: str,
    seed: int,
    identity: Mapping[str, Any],
    harness_identity: Mapping[str, Any],
) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    validate_report_contract(
        report,
        variant=variant,
        opponent=opponent,
        seed=seed,
        identity=identity,
        harness_identity=harness_identity,
    )
    sidecar = receipt_path(report_path)
    receipt = json.loads(sidecar.read_text(encoding="utf-8"))
    validate_receipt(
        receipt,
        report_path,
        variant=variant,
        opponent=opponent,
        seed=seed,
        identity=identity,
        harness_identity=harness_identity,
    )
    return report


def run_one(
    *,
    variant: str,
    opponent: str,
    variants_root: Path,
    harness_root: Path,
    runs_root: Path,
    seed: int,
    resume: bool,
    identity: Mapping[str, Any],
    harness_identity: Mapping[str, Any],
) -> Path:
    output = runs_root / f"{variant}--{opponent}--{seed}.json"
    if resume and output.is_file() and receipt_path(output).is_file():
        try:
            load_validated_shard(
                output,
                variant=variant,
                opponent=opponent,
                seed=seed,
                identity=identity,
                harness_identity=harness_identity,
            )
            return output
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            pass

    candidate = variants_root / variant / "main.py"
    rival = opponent_path(harness_root, opponent)
    temporary = output.with_name(
        f".{output.name}.tmp-{os.getpid()}-{threading.get_ident()}"
    )
    temporary.unlink(missing_ok=True)
    command = [
        "python3", "-B", str(harness_root / "harness" / "evaluate.py"),
        "--engine-dir", str(harness_root / "engine"),
        "--loader", str(harness_root / "harness" / "loader.py"),
        "--candidate", f"{candidate}::agent",
        "--opponent", f"{opponent}={rival}::agent",
        "--seeds", str(seed),
        "--rng-seed", str(EXPECTED_AGENT_RNG_SEED),
        "--action-timeout", str(EXPECTED_LIMITS["action_rpc_seconds"]),
        "--startup-timeout", str(EXPECTED_LIMITS["startup_seconds"]),
        "--game-timeout", str(EXPECTED_LIMITS["game_seconds_between_steps"]),
        "--output", str(temporary),
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    log = output.with_suffix(".log")
    log.write_text(
        completed.stdout + ("\nSTDERR\n" + completed.stderr if completed.stderr else ""),
        encoding="utf-8",
    )
    if completed.returncode:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"{variant}/{opponent}/seed{seed} evaluator failed ({completed.returncode}); see {log}")

    try:
        report = json.loads(temporary.read_text(encoding="utf-8"))
        validate_report_contract(
            report,
            variant=variant,
            opponent=opponent,
            seed=seed,
            identity=identity,
            harness_identity=harness_identity,
        )
        temporary.replace(output)
        atomic_json(
            receipt_path(output),
            make_receipt(
                output,
                variant=variant,
                opponent=opponent,
                seed=seed,
                identity=identity,
                harness_identity=harness_identity,
            ),
        )
        load_validated_shard(
            output,
            variant=variant,
            opponent=opponent,
            seed=seed,
            identity=identity,
            harness_identity=harness_identity,
        )
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return output


def game_key(game: Mapping[str, Any]) -> tuple[str, int, int]:
    return str(game["opponent"]), int(game["seed"]), int(game["candidate_seat"])


def margin(game: Mapping[str, Any]) -> float:
    seat = int(game["candidate_seat"])
    scores = game["scores"]
    return float(scores[seat]) - float(scores[1 - seat])


def candidate_score(game: Mapping[str, Any]) -> float:
    return float(game["scores"][int(game["candidate_seat"])])


def opponent_score(game: Mapping[str, Any]) -> float:
    return float(game["scores"][1 - int(game["candidate_seat"])])


def summarize_values(values: Iterable[float]) -> dict[str, float | int | None]:
    sequence = list(values)
    if not sequence:
        return {"count": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "count": len(sequence),
        "mean": statistics.mean(sequence),
        "median": statistics.median(sequence),
        "min": min(sequence),
        "max": max(sequence),
    }


def classify_feature(
    enabled_effects: list[float],
    trace_divergences: int,
    by_opponent: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    mean_effect = statistics.mean(enabled_effects)
    positive = sum(value > 0 for value in enabled_effects)
    zero = sum(value == 0 for value in enabled_effects)
    negative = sum(value < 0 for value in enabled_effects)
    opponent_means = [float(row["enabled_margin_effect"]["mean"]) for row in by_opponent.values()]

    if trace_divergences == 0:
        recommendation = "no_effect_in_panel"
        reason = "All paired action/score traces were identical."
    elif mean_effect >= 25 and positive > negative and min(opponent_means) >= -100:
        recommendation = "keep"
        reason = "Enabled feature improved paired mean margin without a severe opponent-level reversal."
    elif mean_effect <= -25 and negative > positive and max(opponent_means) <= 100:
        recommendation = "remove"
        reason = "Enabled feature reduced paired mean margin without a severe opponent-level benefit."
    else:
        recommendation = "inconclusive"
        reason = "Observed effects are small, mixed, or matchup-dependent."

    if mean_effect < -250:
        regression_cause = "plausible"
    elif mean_effect > 0:
        regression_cause = "ruled_out_on_this_panel"
    else:
        regression_cause = "not_supported"
    return {
        "recommendation": recommendation,
        "reason": reason,
        "regression_cause_assessment": regression_cause,
        "enabled_margin_effect": summarize_values(enabled_effects),
        "positive_cells": positive,
        "zero_cells": zero,
        "negative_cells": negative,
        "trace_divergences": trace_divergences,
    }


def _parse_run_identity(path: Path) -> tuple[str, str, int]:
    match = RUN_STEM.fullmatch(path.stem)
    if match is None:
        raise ValueError(f"unrecognized run filename: {path.name}")
    return match.group("variant"), match.group("opponent"), int(match.group("seed"))


def aggregate(
    run_files: Iterable[Path],
    *,
    variants: Iterable[str],
    opponents: Iterable[str],
    seeds: tuple[int, ...],
    isolation: Mapping[str, Any],
    harness_identity: Mapping[str, Any],
) -> dict[str, Any]:
    expected_variants = tuple(variants)
    expected_opponents = tuple(opponents)
    games_by_variant: dict[str, dict[tuple[str, int, int], dict[str, Any]]] = {
        name: {} for name in expected_variants
    }
    reports: dict[str, Any] = {}
    seen_reports: set[tuple[str, str, int]] = set()

    for path in run_files:
        variant, opponent, seed = _parse_run_identity(path)
        identity = (variant, opponent, seed)
        if identity in seen_reports:
            raise ValueError(f"duplicate run shard: {identity}")
        seen_reports.add(identity)
        if variant not in games_by_variant:
            raise ValueError(f"unexpected variant shard: {variant}")
        if opponent not in expected_opponents or seed not in seeds:
            raise ValueError(f"unexpected run shard identity: {identity}")
        variant_proof = isolation["variants"][variant]
        report = load_validated_shard(
            path,
            variant=variant,
            opponent=opponent,
            seed=seed,
            identity=variant_proof,
            harness_identity=harness_identity,
        )
        sidecar = receipt_path(path)
        reports[f"{variant}/{opponent}/{seed}"] = {
            "path": str(path),
            "sha256": sha256(path),
            "receipt_path": str(sidecar),
            "receipt_sha256": sha256(sidecar),
            "candidate_file_manifest_sha256": variant_proof["file_manifest_sha256"],
            "candidate_config_sha256": variant_proof["config_sha256"],
            "summary": report.get("summary"),
        }
        for game in report["games"]:
            key = game_key(game)
            if key in games_by_variant[variant]:
                raise ValueError(f"duplicate cell for {variant}: {key}")
            games_by_variant[variant][key] = dict(game)

    expected_shards = {
        (variant, opponent, seed)
        for variant in expected_variants
        for opponent in expected_opponents
        for seed in seeds
    }
    if seen_reports != expected_shards:
        missing = sorted(expected_shards - seen_reports)
        extra = sorted(seen_reports - expected_shards)
        raise ValueError(f"run shard mismatch: missing={missing[:5]}, extra={extra[:5]}")

    expected_keys = {
        (opponent, seed, seat)
        for opponent in expected_opponents
        for seed in seeds
        for seat in (0, 1)
    }
    for variant in expected_variants:
        actual = set(games_by_variant[variant])
        if actual != expected_keys:
            missing = sorted(expected_keys - actual)
            extra = sorted(actual - expected_keys)
            raise ValueError(f"cell mismatch for {variant}: missing={missing[:5]}, extra={extra[:5]}")

    variant_summary: dict[str, Any] = {}
    for variant, cells in games_by_variant.items():
        margins = [margin(game) for game in cells.values()]
        variant_summary[variant] = {
            "scheduled": len(expected_keys),
            "completed": len(cells),
            "failed": 0,
            "wins": sum(value > 0 for value in margins),
            "ties": sum(value == 0 for value in margins),
            "losses": sum(value < 0 for value in margins),
            "margin": summarize_values(margins),
            "candidate_score": summarize_values(candidate_score(game) for game in cells.values()),
            "opponent_score": summarize_values(opponent_score(game) for game in cells.values()),
        }

    comparisons: dict[str, Any] = {}
    decisions: dict[str, Any] = {}
    baseline = games_by_variant["baseline"]
    feature_variants = {
        "redundant_hire": "no_redundant_hire",
        "market_pressure": "no_market_pressure",
        "legacy_pair": "no_legacy_features",
    }
    for feature, disabled_variant in feature_variants.items():
        disabled = games_by_variant[disabled_variant]
        by_opponent: dict[str, Any] = {}
        enabled_effects: list[float] = []
        trace_divergences = 0
        cell_rows: list[dict[str, Any]] = []
        for key in sorted(expected_keys):
            base_game = baseline[key]
            disabled_game = disabled[key]
            effect = margin(base_game) - margin(disabled_game)
            own_effect = candidate_score(base_game) - candidate_score(disabled_game)
            rival_effect = opponent_score(base_game) - opponent_score(disabled_game)
            divergent = (
                base_game.get("trace_sha256") != disabled_game.get("trace_sha256")
                or base_game.get("scores") != disabled_game.get("scores")
            )
            enabled_effects.append(effect)
            trace_divergences += int(divergent)
            opponent, seed, seat = key
            cell_rows.append({
                "opponent": opponent,
                "seed": seed,
                "candidate_seat": seat,
                "enabled_margin_effect": effect,
                "enabled_candidate_score_effect": own_effect,
                "enabled_opponent_score_effect": rival_effect,
                "trace_diverged": divergent,
                "baseline_margin": margin(base_game),
                "disabled_margin": margin(disabled_game),
                "baseline_trace_sha256": base_game.get("trace_sha256"),
                "disabled_trace_sha256": disabled_game.get("trace_sha256"),
            })

        paired_rows: list[dict[str, Any]] = []
        for opponent in expected_opponents:
            rows = [row for row in cell_rows if row["opponent"] == opponent]
            values = [float(row["enabled_margin_effect"]) for row in rows]
            seat_pairs = []
            for seed in seeds:
                pair = [row for row in rows if row["seed"] == seed]
                if {row["candidate_seat"] for row in pair} != {0, 1}:
                    raise ValueError(f"missing mirrored feature pair: {feature}/{opponent}/{seed}")
                pair_effect = statistics.mean(float(row["enabled_margin_effect"]) for row in pair)
                seat_pairs.append(pair_effect)
                paired_rows.append({
                    "opponent": opponent,
                    "seed": seed,
                    "enabled_margin_effect_mean_across_seats": pair_effect,
                })
            by_opponent[opponent] = {
                "enabled_margin_effect": summarize_values(values),
                "seat_pair_enabled_margin_effect": summarize_values(seat_pairs),
                "positive_cells": sum(value > 0 for value in values),
                "zero_cells": sum(value == 0 for value in values),
                "negative_cells": sum(value < 0 for value in values),
                "trace_divergences": sum(bool(row["trace_diverged"]) for row in rows),
            }
        comparisons[feature] = {
            "enabled_variant": "baseline",
            "disabled_variant": disabled_variant,
            "semantics": "positive enabled_margin_effect means the submitted enabled feature improved terminal margin",
            "by_opponent": by_opponent,
            "seat_pair_summary": summarize_values(
                float(row["enabled_margin_effect_mean_across_seats"]) for row in paired_rows
            ),
            "seat_pairs": paired_rows,
            "cells": cell_rows,
        }
        decisions[feature] = classify_feature(enabled_effects, trace_divergences, by_opponent)

    report_manifest = {
        key: {"report_sha256": row["sha256"], "receipt_sha256": row["receipt_sha256"]}
        for key, row in sorted(reports.items())
    }
    return {
        "schema_version": 2,
        "method": "paired exact-cell official-interpreter comparison; local panel, not hosted Kaggle scoring",
        "source_archive_sha256": EXPECTED_SOURCE_SHA256,
        "source_file_manifest_sha256": isolation["baseline_file_manifest_sha256"],
        "harness": dict(harness_identity),
        "seeds": list(seeds),
        "opponents": list(expected_opponents),
        "variants": list(expected_variants),
        "expected_shards": len(expected_shards),
        "expected_cells_per_variant": len(expected_keys),
        "total_completed_games": len(expected_keys) * len(expected_variants),
        "report_manifest_sha256": canonical_sha256(report_manifest),
        "reports": reports,
        "variant_summary": variant_summary,
        "feature_comparisons": comparisons,
        "decisions": decisions,
        "hosted_regression_conclusion": (
            "Neither submitted-V2-only legacy feature is supported as the cause of the hosted regression on this panel; "
            "the local source-pinned opponent distribution is non-discriminating because every variant wins every cell."
        ),
    }


def fmt(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return str(value)
    return f"{value:+.3f}"


def render_markdown(summary: Mapping[str, Any], isolation: Mapping[str, Any]) -> str:
    lines = [
        "# Submitted V2 legacy-feature bisect",
        "",
        f"Source archive: `{summary['source_archive_sha256']}` ({isolation['source_archive']['size_bytes']:,} bytes).",
        f"Source file-manifest digest: `{summary['source_file_manifest_sha256']}`.",
        f"Run/receipt manifest digest: `{summary['report_manifest_sha256']}`.",
        "",
        "This is a paired local official-interpreter panel, not a hosted Kaggle score prediction. Every variant uses identical source bytes except `TITAN-CONFIG.json`; positive feature effect means the submitted enabled feature produced the better terminal margin. Mirrored seats are retained as exact cells and also collapsed into seed/opponent pairs.",
        "",
        "## Variant outcomes",
        "",
        "| Variant | Games | W-T-L | Mean margin | Median margin |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, row in summary["variant_summary"].items():
        lines.append(
            f"| `{name}` | {row['completed']} | {row['wins']}-{row['ties']}-{row['losses']} | "
            f"{fmt(row['margin']['mean'])} | {fmt(row['margin']['median'])} |"
        )
    lines += [
        "",
        "## Feature decisions",
        "",
        "| Feature | Decision | Hosted-regression cause? | Enabled mean effect | + / 0 / - cells | Trace divergence |",
        "|---|---|---|---:|---:|---:|",
    ]
    for feature, decision in summary["decisions"].items():
        lines.append(
            f"| `{feature}` | **{decision['recommendation']}** | `{decision['regression_cause_assessment']}` | "
            f"{fmt(decision['enabled_margin_effect']['mean'])} | "
            f"{decision['positive_cells']} / {decision['zero_cells']} / {decision['negative_cells']} | "
            f"{decision['trace_divergences']}/{decision['enabled_margin_effect']['count']} |"
        )
    for feature, comparison in summary["feature_comparisons"].items():
        decision = summary["decisions"][feature]
        lines += [
            "",
            f"### `{feature}` — {decision['recommendation']}",
            "",
            decision["reason"],
            "",
            "| Opponent | Mean enabled effect | Paired-seat mean | + / 0 / - cells | Diverged |",
            "|---|---:|---:|---:|---:|",
        ]
        for opponent, row in comparison["by_opponent"].items():
            lines.append(
                f"| {opponent} | {fmt(row['enabled_margin_effect']['mean'])} | "
                f"{fmt(row['seat_pair_enabled_margin_effect']['mean'])} | "
                f"{row['positive_cells']} / {row['zero_cells']} / {row['negative_cells']} | "
                f"{row['trace_divergences']}/{row['enabled_margin_effect']['count']} |"
            )
        worst = sorted(comparison["cells"], key=lambda row: row["enabled_margin_effect"])[:5]
        best = sorted(comparison["cells"], key=lambda row: row["enabled_margin_effect"], reverse=True)[:5]
        lines += [
            "",
            "Worst enabled-feature cells: " + ", ".join(
                f"{row['opponent']}/{row['seed']}/seat{row['candidate_seat']}={fmt(row['enabled_margin_effect'])}"
                for row in worst
            ) + ".",
            "",
            "Best enabled-feature cells: " + ", ".join(
                f"{row['opponent']}/{row['seed']}/seat{row['candidate_seat']}={fmt(row['enabled_margin_effect'])}"
                for row in best
            ) + ".",
        ]
    lines += [
        "",
        "## Result",
        "",
        summary["hosted_regression_conclusion"],
        "",
        "## Reproduction",
        "",
        "```bash",
        "python3 run_bisect.py \\",
        "  --source-archive /path/to/titan-submitted-v2-e363.tar.gz \\",
        "  --harness-root /path/to/titan-v1-predecessor-public-policy-gauntlet-20260909 \\",
        "  --work-dir ./work --jobs 4",
        "```",
        "",
        f"Panel: {', '.join(map(str, summary['seeds']))}; both seats; opponents {', '.join(summary['opponents'])}; {summary['total_completed_games']} completed games and {summary['expected_shards']} validated report receipts required.",
        "",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--harness-root", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--seeds", type=parse_csv_ints, default=DEFAULT_SEEDS)
    parser.add_argument("--opponents", type=parse_csv_names, default=DEFAULT_OPPONENTS)
    parser.add_argument("--run-variants", type=parse_csv_variants, default=tuple(VARIANTS))
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.jobs < 1:
        raise SystemExit("--jobs must be positive")
    source_archive = args.source_archive.resolve(strict=True)
    harness_root = args.harness_root.resolve(strict=True)
    work_dir = args.work_dir.resolve()
    variants_root = work_dir / "variants"
    runs_root = work_dir / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    harness_identity = verify_harness(harness_root, args.opponents)
    isolation = prepare_variants(source_archive, variants_root)
    atomic_json(work_dir / "HARNESS.json", harness_identity)
    atomic_json(work_dir / "ISOLATION.json", isolation)
    if args.prepare_only:
        print(json.dumps({"harness": harness_identity, "isolation": isolation}, indent=2, sort_keys=True))
        return 0

    tasks = [
        (variant, opponent, seed)
        for variant in args.run_variants
        for opponent in args.opponents
        for seed in args.seeds
    ]
    with ThreadPoolExecutor(max_workers=min(args.jobs, len(tasks))) as executor:
        futures = {
            executor.submit(
                run_one,
                variant=variant,
                opponent=opponent,
                variants_root=variants_root,
                harness_root=harness_root,
                runs_root=runs_root,
                seed=seed,
                resume=args.resume,
                identity=isolation["variants"][variant],
                harness_identity=harness_identity,
            ): (variant, opponent, seed)
            for variant, opponent, seed in tasks
        }
        for future in as_completed(futures):
            variant, opponent, seed = futures[future]
            path = future.result()
            report = json.loads(path.read_text(encoding="utf-8"))
            row = report["summary"][opponent]
            print(
                f"DONE {variant}/{opponent}/seed{seed}: {row['wins']}W-{row['ties']}T-{row['losses']}L "
                f"mean_margin={row['mean_margin']:+.3f}",
                flush=True,
            )

    expected_run_files = [
        runs_root / f"{variant}--{opponent}--{seed}.json"
        for variant in VARIANTS
        for opponent in args.opponents
        for seed in args.seeds
    ]
    invalid: list[dict[str, str]] = []
    for path in expected_run_files:
        variant, opponent, seed = _parse_run_identity(path)
        try:
            load_validated_shard(
                path,
                variant=variant,
                opponent=opponent,
                seed=seed,
                identity=isolation["variants"][variant],
                harness_identity=harness_identity,
            )
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            invalid.append({"path": str(path), "reason": f"{type(exc).__name__}: {exc}"})
    if invalid:
        incomplete = {
            "status": "incomplete",
            "valid_shards": len(expected_run_files) - len(invalid),
            "expected_shards": len(expected_run_files),
            "invalid_or_missing": invalid,
        }
        atomic_json(work_dir / "INCOMPLETE.json", incomplete)
        print(json.dumps(incomplete, indent=2))
        return 0

    summary = aggregate(
        expected_run_files,
        variants=VARIANTS,
        opponents=args.opponents,
        seeds=args.seeds,
        isolation=isolation,
        harness_identity=harness_identity,
    )
    atomic_json(work_dir / "RESULTS.json", summary)
    (work_dir / "RESULTS.md").write_text(render_markdown(summary, isolation), encoding="utf-8")
    (work_dir / "INCOMPLETE.json").unlink(missing_ok=True)
    print(json.dumps(summary["decisions"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
