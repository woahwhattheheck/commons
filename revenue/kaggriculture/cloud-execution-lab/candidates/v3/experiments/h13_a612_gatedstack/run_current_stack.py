# SPDX-License-Identifier: Apache-2.0
"""Evidence-only H13 screen on the shipped a612 V3.1 stack.

Materialize the current score-facing submission twice from the current checkout,
changing only the strict integer r04_sale_horizon from 8 to 10.  Pair both arms
against (1) exact shipped h8 self and (2) vendored Arlene over the frozen eight
seeds and both candidate seats.  This is an offline official-interpreter gate,
not a gameplay/default/package-source mutation and not a hosted Kaggle score.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tarfile
import tempfile


CANONICAL_SHA256 = "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
BASE_ARCHIVE_SHA256 = "400ae640f3258b6a6ff19f9da99c66ef9c433e315febb1d72c75296cddeb277c"
ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
SEEDS = tuple(range(2611151001, 2611151009))

LAB_REL = Path("revenue/kaggriculture/cloud-execution-lab")
V3_REL = LAB_REL / "candidates" / "v3"
CANONICAL_REL = LAB_REL / "exports" / "titan-current.tar.gz"
EVALUATOR_REL = LAB_REL / "reference" / "evaluator" / "evaluate.py"
ENGINE_DIR_REL = LAB_REL / "reference" / "engine"
ARLENE_REL = LAB_REL / "reference" / "next-panel" / "vendor" / "arlene.py"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, *, cwd: Path) -> None:
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)


def typed(value):
    """JSON-compatible recursive value with exact Python scalar type tags."""
    if type(value) is dict:
        if not all(type(key) is str for key in value):
            raise TypeError("configuration object contains a non-string key")
        return ("dict", tuple((key, typed(value[key])) for key in sorted(value)))
    if type(value) is list:
        return ("list", tuple(typed(item) for item in value))
    if value is None:
        return ("none", None)
    if type(value) is bool:
        return ("bool", value)
    if type(value) is int:
        return ("int", value)
    if type(value) is float:
        return ("float", value)
    if type(value) is str:
        return ("str", value)
    raise TypeError(f"unsupported configuration value type: {type(value).__name__}")


def tar_map(path: Path) -> dict[str, bytes]:
    blob = path.read_bytes()
    result: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
        for member in archive.getmembers():
            if member.issym() or member.islnk():
                raise ValueError(f"archive link is not allowed: {member.name}")
            if not member.isfile():
                continue
            name = member.name[2:] if member.name.startswith("./") else member.name
            if name.startswith("/") or ".." in Path(name).parts or name in result:
                raise ValueError(f"unsafe/duplicate archive member: {member.name}")
            result[name] = archive.extractfile(member).read()
    return result


def write_tree(files: dict[str, bytes], root: Path) -> None:
    for name, blob in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)


def read_config(files: dict[str, bytes]) -> dict:
    value = json.loads(files["TITAN-CONFIG.json"].decode("utf-8"))
    if type(value) is not dict:
        raise TypeError("TITAN-CONFIG.json must be an object")
    return value


def assert_score_stack(config: dict, horizon: int) -> None:
    expected = {
        "r04_sale_window": True,
        "r04_sale_horizon": horizon,
        "r04_open_roundtrip": 0,
        "r04_row_order": True,
        "r04_evening_flush": True,
        "r04_sale_fertilizer": True,
        "r04_cattle_early": True,
        "r04_no_late_sale_advance": True,
        "r04_no_late_sale_advance_step": 648,
        "r04_strawberry_topup": True,
    }
    for key, want in expected.items():
        got = config.get(key)
        if type(got) is not type(want) or got != want:
            raise AssertionError(f"score-facing config drift {key}: {got!r} != {want!r}")


def build_submissions(repo: Path, work: Path) -> tuple[Path, Path, dict, dict, dict]:
    v3 = repo / V3_REL
    canonical = repo / CANONICAL_REL
    if sha256_file(canonical) != CANONICAL_SHA256:
        raise AssertionError("canonical archive SHA drift")

    sys.path.insert(0, str(v3))
    import build_v3  # noqa: E402

    base_files = build_v3.package_files(canonical)
    base_blob = build_v3.build_bytes(base_files)
    base_digest = sha256_bytes(base_blob)
    manifest = json.loads((v3 / "V3-MANIFEST.json").read_text(encoding="utf-8"))
    if base_digest != BASE_ARCHIVE_SHA256 or manifest.get("archive", {}).get("sha256") != base_digest:
        raise AssertionError(
            f"current build is not shipped a612 package: {base_digest} / {manifest.get('archive', {}).get('sha256')}"
        )

    h8_tar = work / "a612-h8-submission.tar.gz"
    h10_tar = work / "a612-h10-submission.tar.gz"
    run([sys.executable, "-B", v3 / "make_submission.py", v3, canonical, h8_tar], cwd=repo)
    run([sys.executable, "-B", v3 / "make_submission.py", v3, canonical, h10_tar, "10"], cwd=repo)

    h8_files, h10_files = tar_map(h8_tar), tar_map(h10_tar)
    if set(h8_files) != set(h10_files):
        raise AssertionError("h8/h10 package member sets differ")
    changed = [name for name in sorted(h8_files) if h8_files[name] != h10_files[name]]
    if changed != ["TITAN-CONFIG.json"]:
        raise AssertionError(f"h8/h10 package bytes differ outside config: {changed}")

    h8_config, h10_config = read_config(h8_files), read_config(h10_files)
    assert_score_stack(h8_config, 8)
    assert_score_stack(h10_config, 10)
    left, right = copy.deepcopy(h8_config), copy.deepcopy(h10_config)
    if left.pop("r04_sale_horizon", None) != 8 or right.pop("r04_sale_horizon", None) != 10:
        raise AssertionError("horizon isolation failed")
    if typed(left) != typed(right):
        raise AssertionError("typed configuration differs outside r04_sale_horizon")

    return h8_tar, h10_tar, h8_files, h10_files, manifest


def evaluator_report(
    repo: Path,
    candidate: Path,
    h8_opponent: Path,
    arlene: Path,
    output: Path,
    *,
    recheck_first: bool,
) -> dict:
    args = [
        sys.executable,
        "-B",
        repo / EVALUATOR_REL,
        "--engine-dir",
        repo / ENGINE_DIR_REL,
        "--candidate",
        candidate,
        "--opponent",
        f"h8_self={h8_opponent}",
        "--opponent",
        f"arlene={arlene}",
        "--seeds",
        ",".join(map(str, SEEDS)),
        "--game-timeout",
        "180",
        "--output",
        output,
    ]
    if recheck_first:
        args.append("--recheck-first")
    run(args, cwd=repo)
    report = json.loads(output.read_text(encoding="utf-8"))
    if report.get("engine_ref") != ENGINE_REF:
        raise AssertionError(f"engine ref drift: {report.get('engine_ref')!r}")
    return report


def indexed_games(report: dict) -> dict[tuple[str, int, int], dict]:
    games = report.get("games")
    if type(games) is not list:
        raise AssertionError("evaluator report has no games list")
    expected = {
        (opponent, seed, seat)
        for opponent in ("h8_self", "arlene")
        for seed in SEEDS
        for seat in (0, 1)
    }
    rows: dict[tuple[str, int, int], dict] = {}
    for game in games:
        key = (game.get("opponent"), game.get("seed"), game.get("candidate_seat"))
        if key not in expected or key in rows:
            raise AssertionError(f"unexpected/duplicate evaluator cell: {key}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise AssertionError(f"incomplete evaluator cell {key}: {game.get('failure')}")
        scores = game.get("scores")
        if not (
            type(scores) is list
            and len(scores) == 2
            and all(type(value) in (int, float) for value in scores)
        ):
            raise AssertionError(f"invalid scores for {key}: {scores!r}")
        rows[key] = game
    if set(rows) != expected:
        raise AssertionError(f"missing evaluator cells: {sorted(expected - set(rows))}")
    return rows


def components(game: dict) -> tuple[float, float, float]:
    seat = game["candidate_seat"]
    scores = game["scores"]
    own = float(scores[seat])
    rival = float(scores[1 - seat])
    return own, rival, own - rival


def summarize_pairs(h8: dict, h10: dict, opponent: str) -> tuple[dict, list[dict]]:
    rows = []
    for seed in SEEDS:
        for seat in (0, 1):
            key = (opponent, seed, seat)
            own8, rival8, margin8 = components(h8[key])
            own10, rival10, margin10 = components(h10[key])
            rows.append(
                {
                    "seed": seed,
                    "candidate_seat": seat,
                    "h8_scores": h8[key]["scores"],
                    "h10_scores": h10[key]["scores"],
                    "h8_trace_sha256": h8[key]["trace_sha256"],
                    "h10_trace_sha256": h10[key]["trace_sha256"],
                    "delta_own": own10 - own8,
                    "delta_rival": rival10 - rival8,
                    "delta_margin": margin10 - margin8,
                }
            )
    deltas = [row["delta_margin"] for row in rows]
    own = [row["delta_own"] for row in rows]
    rival = [row["delta_rival"] for row in rows]
    seat0 = [row["delta_margin"] for row in rows if row["candidate_seat"] == 0]
    seat1 = [row["delta_margin"] for row in rows if row["candidate_seat"] == 1]
    summary = {
        "cells": len(rows),
        "positive": sum(value > 0 for value in deltas),
        "zero": sum(value == 0 for value in deltas),
        "negative": sum(value < 0 for value in deltas),
        "mean_delta_margin": statistics.mean(deltas),
        "median_delta_margin": statistics.median(deltas),
        "min_delta_margin": min(deltas),
        "max_delta_margin": max(deltas),
        "mean_delta_own": statistics.mean(own),
        "mean_delta_rival": statistics.mean(rival),
        "seat0_mean_delta_margin": statistics.mean(seat0),
        "seat1_mean_delta_margin": statistics.mean(seat1),
    }
    return summary, rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    arlene = repo / ARLENE_REL
    if sha256_file(arlene) != "1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4":
        raise AssertionError("Arlene source SHA drift")

    with tempfile.TemporaryDirectory(prefix="titan-a612-h13-") as tmp:
        work = Path(tmp)
        h8_tar, h10_tar, h8_files, h10_files, manifest = build_submissions(repo, work)
        h8_dir, h10_dir = work / "h8", work / "h10"
        write_tree(h8_files, h8_dir)
        write_tree(h10_files, h10_dir)
        for package in (h8_dir, h10_dir):
            for required in ("main.py", "r04_full_router.py", "r04_h4_strawberry.py"):
                if not (package / required).is_file():
                    raise AssertionError(f"materialized submission missing {required}")

        h8_raw = output / "h8-control-raw.json"
        h10_raw = output / "h10-candidate-raw.json"
        report8 = evaluator_report(
            repo, h8_dir / "main.py", h8_dir / "main.py", arlene, h8_raw, recheck_first=True
        )
        report10 = evaluator_report(
            repo, h10_dir / "main.py", h8_dir / "main.py", arlene, h10_raw, recheck_first=True
        )
        rows8, rows10 = indexed_games(report8), indexed_games(report10)

        # Identical h8-vs-h8 is an execution/seat-mapping control, not the result.
        identity_margins = [components(rows8[("h8_self", seed, seat)])[2] for seed in SEEDS for seat in (0, 1)]
        if any(value != 0 for value in identity_margins):
            raise AssertionError(f"h8 self identity is not exact tie: {identity_margins}")

        self_summary, self_rows = summarize_pairs(rows8, rows10, "h8_self")
        arlene_summary, arlene_rows = summarize_pairs(rows8, rows10, "arlene")
        means = [self_summary["mean_delta_margin"], arlene_summary["mean_delta_margin"]]
        if all(value > 0 for value in means):
            disposition = "both_regimes_positive_mean_expand_to_recorded41"
        elif means[0] * means[1] < 0:
            disposition = "regime_sign_split_hold_or_selector"
        else:
            disposition = "horizon10_not_positive_across_current_stack"

        receipt = {
            "schema": "titan-v31-a612-h13-gatedstack/v1",
            "truth_boundary": (
                "Offline official-interpreter evidence only. The current rival gate is byte-pinned, "
                "but the evaluator does not expose its private per-game classifier boolean; h8_self "
                "and Arlene are reported as tape-like and policy-diverse regimes, not asserted gate states."
            ),
            "canonical_head": "a6120d0ea1bdb75eb0da2239220efce551f624a6",
            "source": {
                "canonical_sha256": CANONICAL_SHA256,
                "base_archive_sha256": manifest["archive"]["sha256"],
                "engine_ref": ENGINE_REF,
                "evaluator_sha256": sha256_file(repo / EVALUATOR_REL),
                "arlene_sha256": sha256_file(arlene),
            },
            "isolation": {
                "only_package_member_difference": "TITAN-CONFIG.json",
                "only_typed_config_difference": {"r04_sale_horizon": [8, 10]},
                "h8_submission": {"sha256": sha256_file(h8_tar), "bytes": h8_tar.stat().st_size, "files": len(h8_files)},
                "h10_submission": {"sha256": sha256_file(h10_tar), "bytes": h10_tar.stat().st_size, "files": len(h10_files)},
                "shipped_keys": {
                    "r04_sale_window": True,
                    "r04_strawberry_topup": True,
                    "r04_no_late_sale_advance": True,
                    "r04_sale_fertilizer": True,
                    "r04_cattle_early": True,
                },
            },
            "panel": {"seeds": list(SEEDS), "seats": [0, 1], "cells_per_regime": 16},
            "regimes": {
                "h8_self": {"summary": self_summary, "cells": self_rows},
                "arlene": {"summary": arlene_summary, "cells": arlene_rows},
            },
            "disposition": disposition,
            "raw": {
                "h8_control": {"file": h8_raw.name, "sha256": sha256_file(h8_raw)},
                "h10_candidate": {"file": h10_raw.name, "sha256": sha256_file(h10_raw)},
            },
        }
        receipt_path = output / "h13-a612-receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(
            "H13_A612_RESULT",
            json.dumps(
                {
                    "disposition": disposition,
                    "h8_self": self_summary,
                    "arlene": arlene_summary,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        print("H13_A612_RECEIPT", receipt_path, sha256_file(receipt_path), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
