#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify the exact-current TITAN T10 redundant-hire evidence packet.

The verifier is independent of the panel runner. It binds the published bytes,
rejects duplicate JSON keys/cells, recomputes every paired outcome, and checks
that the development grid supports the narrow KEEP disposition. It grants no
hosted-score, holdout, release, or submission authority.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ARCHIVE = "a055fd56ca5821208096f37787f77dbdddc2f65c14c24132d6e219a05e6f02ba"
SOURCE = "b96676977687ee8a92d7213380f96bf5774a5ec26925cb4f0d66bdd244eb44ba"
ENGINE = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
SEEDS = (2609097001, 2609097002, 2609097003, 2609097004)
OPPONENTS = ("v1", "arlene", "apex", "kaito", "reyhan")
VARIANTS = ("redundant_hire_off", "redundant_hire_on")
SEATS = (0, 1)
GAME_COLUMNS = (
    "variant_index", "opponent_index", "seed", "seat", "own", "rival",
    "margin", "trace_sha256",
)
PAIR_COLUMNS = (
    "opponent_index", "seed", "seat", "own_delta", "rival_delta",
    "margin_delta", "trace_changed", "verdict_flip",
)


class EvidenceError(ValueError):
    """The packet is malformed, incomplete, or does not support its claim."""


def no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=no_duplicate_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read JSON {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
    except OSError as exc:
        raise EvidenceError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def tree_sha256(root: Path) -> str:
    if not root.is_dir():
        raise EvidenceError(f"not a directory: {root}")
    digest_value = hashlib.sha256()
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        if path.is_symlink():
            raise EvidenceError(f"tree contains symlink: {path}")
        relative = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest_value.update(len(relative).to_bytes(8, "big"))
        digest_value.update(relative)
        digest_value.update(len(data).to_bytes(8, "big"))
        digest_value.update(data)
    return digest_value.hexdigest()


def number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise EvidenceError(f"{label} must be finite")
    return result


def integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EvidenceError(f"{label} must be an integer")
    return value


def valid_digest(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(character in "0123456789abcdef" for character in value))


def close(actual: float, expected: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-9):
        raise EvidenceError(f"{label}: expected {expected!r}, got {actual!r}")


def verdict(margin: float) -> str:
    return "W" if margin > 0 else "L" if margin < 0 else "T"


def verify_external(manifest: dict[str, Any], archive: Path | None,
                    source_manifest: Path | None,
                    gauntlet_root: Path | None) -> None:
    dispatch = manifest["dispatch_canonical"]
    if archive is not None:
        if archive.stat().st_size != dispatch["archive_bytes"]:
            raise EvidenceError("archive byte count mismatch")
        if sha256_file(archive) != dispatch["archive_sha256"]:
            raise EvidenceError("archive SHA-256 mismatch")
    if source_manifest is not None:
        if sha256_file(source_manifest) != dispatch["source_manifest_sha256"]:
            raise EvidenceError("SOURCE.json SHA-256 mismatch")
    if gauntlet_root is None:
        return
    engine = manifest["engine"]
    for name, record in engine["files"].items():
        path = gauntlet_root / "engine" / name
        if path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
            raise EvidenceError(f"engine fixture drift: {name}")
    for label in ("evaluator", "loader"):
        record = engine[label]
        if sha256_file(gauntlet_root / record["path"]) != record["sha256"]:
            raise EvidenceError(f"{label} drift")
    for name, record in manifest["opponents"].items():
        entry = gauntlet_root / record["entrypoint"].partition("::")[0]
        if sha256_file(entry) != record["entry_sha256"]:
            raise EvidenceError(f"opponent entry drift: {name}")
        if tree_sha256(entry.parent) != record["tree_sha256"]:
            raise EvidenceError(f"opponent tree drift: {name}")


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    return {
        "cells": count,
        "trace_changed": sum(bool(row["trace_changed"]) for row in rows),
        "mean_own_delta": sum(row["own_delta"] for row in rows) / count,
        "mean_rival_delta": sum(row["rival_delta"] for row in rows) / count,
        "mean_margin_delta": sum(row["margin_delta"] for row in rows) / count,
        "min_margin_delta": min(row["margin_delta"] for row in rows),
        "max_margin_delta": max(row["margin_delta"] for row in rows),
        "flips": dict(sorted(Counter(row["verdict_flip"] for row in rows).items())),
    }


def verify_packet(directory: Path, *, archive: Path | None = None,
                  source_manifest: Path | None = None,
                  gauntlet_root: Path | None = None) -> dict[str, Any]:
    manifest_path = directory / "MANIFEST.json"
    summary_path = directory / "SUMMARY.json"
    manifest = load_json(manifest_path)
    summary = load_json(summary_path)
    if not isinstance(manifest, dict) or not isinstance(summary, dict):
        raise EvidenceError("manifest and summary must be objects")
    evidence = manifest.get("evidence", {})
    if summary_path.stat().st_size != evidence.get("summary_bytes"):
        raise EvidenceError("summary byte count mismatch")
    if sha256_file(summary_path) != evidence.get("summary_sha256"):
        raise EvidenceError("summary SHA-256 mismatch")

    dispatch = manifest.get("dispatch_canonical", {})
    if manifest.get("schema_version") != 1 or summary.get("schema_version") != 1:
        raise EvidenceError("unsupported schema")
    if dispatch.get("archive_sha256") != ARCHIVE:
        raise EvidenceError("wrong canonical archive")
    if dispatch.get("source_manifest_sha256") != SOURCE:
        raise EvidenceError("wrong source manifest")
    if manifest.get("engine", {}).get("ref") != ENGINE:
        raise EvidenceError("wrong engine ref")
    experiment = manifest.get("experiment", {})
    if (tuple(experiment.get("seeds", ())) != SEEDS
            or tuple(experiment.get("opponents", ())) != OPPONENTS
            or tuple(experiment.get("seats", ())) != SEATS):
        raise EvidenceError("experiment grid drift")
    if (experiment.get("factor") != "redundant_hire"
            or experiment.get("control") is not False
            or experiment.get("treatment") is not True):
        raise EvidenceError("factor contract drift")

    if (summary.get("status") != "complete"
            or summary.get("archive_sha256") != ARCHIVE
            or summary.get("source_manifest_sha256") != SOURCE
            or summary.get("engine_ref") != ENGINE):
        raise EvidenceError("summary identity/status drift")
    if (tuple(summary.get("variants", ())) != VARIANTS
            or tuple(summary.get("opponents", ())) != OPPONENTS
            or tuple(summary.get("seeds", ())) != SEEDS
            or tuple(summary.get("game_columns", ())) != GAME_COLUMNS
            or tuple(summary.get("pair_columns", ())) != PAIR_COLUMNS):
        raise EvidenceError("summary schema/grid drift")

    games = summary.get("games")
    if not isinstance(games, list) or len(games) != 80:
        raise EvidenceError("expected exactly 80 games")
    index: dict[tuple[int, int, int, int], dict[str, Any]] = {}
    for row_number, raw in enumerate(games):
        if not isinstance(raw, list) or len(raw) != len(GAME_COLUMNS):
            raise EvidenceError(f"malformed game row {row_number}")
        variant = integer(raw[0], f"game {row_number}/variant")
        opponent = integer(raw[1], f"game {row_number}/opponent")
        seed = integer(raw[2], f"game {row_number}/seed")
        seat = integer(raw[3], f"game {row_number}/seat")
        if variant not in range(len(VARIANTS)) or opponent not in range(len(OPPONENTS)):
            raise EvidenceError(f"bad variant/opponent index at game {row_number}")
        if seed not in SEEDS or seat not in SEATS:
            raise EvidenceError(f"bad seed/seat at game {row_number}")
        own = number(raw[4], f"game {row_number}/own")
        rival = number(raw[5], f"game {row_number}/rival")
        margin = number(raw[6], f"game {row_number}/margin")
        close(margin, own - rival, f"game {row_number}/margin arithmetic")
        if not valid_digest(raw[7]):
            raise EvidenceError(f"bad trace digest at game {row_number}")
        key = (variant, opponent, seed, seat)
        if key in index:
            raise EvidenceError(f"duplicate game cell: {key}")
        index[key] = {"own": own, "rival": rival, "margin": margin, "trace": raw[7]}
    expected = {(variant, opponent, seed, seat)
                for variant in range(2) for opponent in range(5)
                for seed in SEEDS for seat in SEATS}
    if set(index) != expected:
        raise EvidenceError("game grid is incomplete or contains extra cells")

    recomputed_pairs: list[dict[str, Any]] = []
    by_key: dict[tuple[int, int, int], dict[str, Any]] = {}
    for opponent in range(len(OPPONENTS)):
        for seed in SEEDS:
            for seat in SEATS:
                off = index[(0, opponent, seed, seat)]
                on = index[(1, opponent, seed, seat)]
                item = {
                    "opponent": opponent, "seed": seed, "seat": seat,
                    "own_delta": on["own"] - off["own"],
                    "rival_delta": on["rival"] - off["rival"],
                    "margin_delta": on["margin"] - off["margin"],
                    "trace_changed": on["trace"] != off["trace"],
                    "verdict_flip": f"{verdict(off['margin'])}->{verdict(on['margin'])}",
                }
                recomputed_pairs.append(item)
                by_key[(opponent, seed, seat)] = item

    published_pairs = summary.get("pairs")
    if not isinstance(published_pairs, list) or len(published_pairs) != 40:
        raise EvidenceError("expected exactly 40 paired rows")
    seen: set[tuple[int, int, int]] = set()
    for row_number, raw in enumerate(published_pairs):
        if not isinstance(raw, list) or len(raw) != len(PAIR_COLUMNS):
            raise EvidenceError(f"malformed pair row {row_number}")
        key = (integer(raw[0], "pair/opponent"), integer(raw[1], "pair/seed"),
               integer(raw[2], "pair/seat"))
        if key in seen:
            raise EvidenceError(f"duplicate pair cell: {key}")
        seen.add(key)
        expected_pair = by_key.get(key)
        if expected_pair is None:
            raise EvidenceError(f"unexpected pair cell: {key}")
        for offset, name in ((3, "own_delta"), (4, "rival_delta"), (5, "margin_delta")):
            close(number(raw[offset], f"pair {key}/{name}"), expected_pair[name],
                  f"pair {key}/{name}")
        if raw[6] is not expected_pair["trace_changed"] or raw[7] != expected_pair["verdict_flip"]:
            raise EvidenceError(f"pair outcome mismatch: {key}")
    if seen != set(by_key):
        raise EvidenceError("paired grid incomplete")

    actual = aggregate(recomputed_pairs)
    published = summary.get("aggregate", {})
    for key in ("cells", "trace_changed", "flips"):
        if published.get(key) != actual[key]:
            raise EvidenceError(f"aggregate {key} mismatch")
    for key in ("mean_own_delta", "mean_rival_delta", "mean_margin_delta",
                "min_margin_delta", "max_margin_delta"):
        close(number(published.get(key), f"aggregate/{key}"), actual[key],
              f"aggregate/{key}")

    claimed = manifest.get("result", {})
    if (claimed.get("status") != "complete" or claimed.get("failures") != 0
            or claimed.get("disposition") != "KEEP"):
        raise EvidenceError("manifest result drift")
    correspondence = {
        "trace_changed_cells": "trace_changed",
        "mean_own_delta": "mean_own_delta",
        "mean_rival_delta": "mean_rival_delta",
        "mean_margin_delta": "mean_margin_delta",
        "min_margin_delta": "min_margin_delta",
        "max_margin_delta": "max_margin_delta",
        "verdict_flips": "flips",
    }
    for claim_key, actual_key in correspondence.items():
        claimed_value, actual_value = claimed.get(claim_key), actual[actual_key]
        if isinstance(actual_value, float):
            close(number(claimed_value, f"manifest/{claim_key}"), actual_value,
                  f"manifest/{claim_key}")
        elif claimed_value != actual_value:
            raise EvidenceError(f"manifest/{claim_key} mismatch")

    if (actual["cells"] != 40 or actual["trace_changed"] != 40
            or actual["min_margin_delta"] <= 0
            or actual["flips"] != {"W->W": 40}):
        raise EvidenceError("KEEP unsupported by complete paired outcomes")
    verify_external(manifest, archive, source_manifest, gauntlet_root)
    return {
        "status": "PASS", "operation": manifest["operation"],
        "archive_sha256": ARCHIVE, "engine_ref": ENGINE,
        "complete_games": 80, "paired_cells": 40,
        "trace_changed_cells": actual["trace_changed"],
        "mean_own_delta": actual["mean_own_delta"],
        "mean_margin_delta": actual["mean_margin_delta"],
        "min_margin_delta": actual["min_margin_delta"],
        "max_margin_delta": actual["max_margin_delta"],
        "verdict_flips": actual["flips"], "disposition": "KEEP",
        "authority": "offline development evidence only",
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent)
    value.add_argument("--archive", type=Path)
    value.add_argument("--source-manifest", type=Path)
    value.add_argument("--gauntlet-root", type=Path)
    value.add_argument("--json", action="store_true")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        result = verify_packet(args.directory.resolve(), archive=args.archive,
                               source_manifest=args.source_manifest,
                               gauntlet_root=args.gauntlet_root)
    except (EvidenceError, OSError) as exc:
        print(json.dumps({"status": "INVALID", "error": str(exc)}, sort_keys=True)
              if args.json else f"INVALID: {exc}")
        return 2
    print(json.dumps(result, sort_keys=True) if args.json else
          (f"PASS: {result['complete_games']} games / {result['paired_cells']} pairs; "
           f"mean margin {result['mean_margin_delta']:+.3f}; "
           f"minimum {result['min_margin_delta']:+.3f}; {result['disposition']}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
