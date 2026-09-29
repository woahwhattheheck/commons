# SPDX-License-Identifier: Apache-2.0
"""Fail-closed paired report gate for the receding reserve-release candidate."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import tempfile
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"


class PanelError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(
                PanelError(f"non-finite JSON token: {token}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PanelError(f"cannot read {path}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(value, dict):
        raise PanelError(f"{path} must contain one JSON object")
    return value


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _finite_score(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PanelError(f"{label} is not numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise PanelError(f"{label} is not finite")
    return parsed


def _fingerprint(report: Mapping[str, Any], label: str) -> dict[str, Any]:
    if report.get("schema_version") != 1:
        raise PanelError(f"{label} schema_version mismatch")
    if report.get("engine_ref") != ENGINE_REF:
        raise PanelError(f"{label} engine_ref mismatch")
    if not isinstance(report.get("engine_sha256"), Mapping):
        raise PanelError(f"{label} missing engine hashes")
    if not isinstance(report.get("candidate"), Mapping):
        raise PanelError(f"{label} missing candidate fingerprint")
    if not isinstance(report.get("opponents"), Mapping):
        raise PanelError(f"{label} missing opponent fingerprints")
    seeds = report.get("seeds")
    if (
        not isinstance(seeds, list)
        or not seeds
        or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds)
        or len(seeds) != len(set(seeds))
    ):
        raise PanelError(f"{label} seeds are invalid")
    return {
        "engine_sha256": dict(report["engine_sha256"]),
        "loader_sha256": report.get("loader_sha256"),
        "evaluator_sha256": report.get("evaluator_sha256"),
        "opponents": dict(report["opponents"]),
        "seeds": list(seeds),
    }


def _games(
    report: Mapping[str, Any],
    label: str,
) -> dict[tuple[str, int, int], dict[str, Any]]:
    raw = report.get("games")
    if not isinstance(raw, list):
        raise PanelError(f"{label} games must be a list")
    result: dict[tuple[str, int, int], dict[str, Any]] = {}
    for index, game in enumerate(raw):
        if not isinstance(game, dict):
            raise PanelError(f"{label} game {index} is not an object")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        if (
            not isinstance(opponent, str)
            or not opponent
            or isinstance(seed, bool)
            or not isinstance(seed, int)
            or seat not in (0, 1)
        ):
            raise PanelError(f"{label} game {index} has an invalid identity")
        key = (opponent, seed, int(seat))
        if key in result:
            raise PanelError(f"{label} duplicate game {key}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise PanelError(f"{label} incomplete game {key}: {game.get('failure')}")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise PanelError(f"{label} game {key} has invalid scores")
        parsed_scores = [
            _finite_score(scores[0], f"{label} {key} score0"),
            _finite_score(scores[1], f"{label} {key} score1"),
        ]
        trace = game.get("trace_sha256")
        if (
            not isinstance(trace, str)
            or len(trace) != 64
            or any(char not in "0123456789abcdef" for char in trace)
        ):
            raise PanelError(f"{label} game {key} has invalid trace digest")
        copied = dict(game)
        copied["scores"] = parsed_scores
        result[key] = copied
    return result


def compare(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    expected_head: str | None = None,
) -> dict[str, Any]:
    control_fp = _fingerprint(control, "control")
    candidate_fp = _fingerprint(candidate, "candidate")
    if control_fp != candidate_fp:
        raise PanelError("control/candidate evaluator, engine, seed, or opponent drift")

    expected_control = sha256_file(HERE / "control.py")
    expected_candidate = sha256_file(HERE / "candidate.py")
    if control["candidate"].get("sha256") != expected_control:
        raise PanelError("control entrypoint digest mismatch")
    if candidate["candidate"].get("sha256") != expected_candidate:
        raise PanelError("candidate entrypoint digest mismatch")

    control_games = _games(control, "control")
    candidate_games = _games(candidate, "candidate")
    opponents = sorted(control_fp["opponents"])
    expected = {
        (opponent, seed, seat)
        for opponent in opponents
        for seed in control_fp["seeds"]
        for seat in (0, 1)
    }
    if set(control_games) != expected:
        missing = sorted(expected - set(control_games))
        extra = sorted(set(control_games) - expected)
        raise PanelError(f"control cell set mismatch; missing={missing}; extra={extra}")
    if set(candidate_games) != expected:
        missing = sorted(expected - set(candidate_games))
        extra = sorted(set(candidate_games) - expected)
        raise PanelError(f"candidate cell set mismatch; missing={missing}; extra={extra}")

    rows: list[dict[str, Any]] = []
    by_opponent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for key in sorted(expected):
        opponent, seed, seat = key
        left = control_games[key]
        right = candidate_games[key]
        control_own = left["scores"][seat]
        control_rival = left["scores"][1 - seat]
        candidate_own = right["scores"][seat]
        candidate_rival = right["scores"][1 - seat]
        row = {
            "opponent": opponent,
            "seed": seed,
            "seat": seat,
            "control_own": control_own,
            "control_rival": control_rival,
            "candidate_own": candidate_own,
            "candidate_rival": candidate_rival,
            "own_delta": candidate_own - control_own,
            "rival_delta": candidate_rival - control_rival,
            "control_margin": control_own - control_rival,
            "candidate_margin": candidate_own - candidate_rival,
            "margin_delta": (
                candidate_own - candidate_rival
                - (control_own - control_rival)
            ),
            "trace_changed": left["trace_sha256"] != right["trace_sha256"],
        }
        rows.append(row)
        by_opponent[opponent].append(row)

    def summarize(group: list[dict[str, Any]]) -> dict[str, Any]:
        deltas = [row["margin_delta"] for row in group]
        return {
            "cells": len(group),
            "changed_cells": sum(row["trace_changed"] for row in group),
            "positive_cells": sum(delta > 0 for delta in deltas),
            "zero_cells": sum(delta == 0 for delta in deltas),
            "negative_cells": sum(delta < 0 for delta in deltas),
            "mean_own_delta": statistics.mean(row["own_delta"] for row in group),
            "mean_rival_delta": statistics.mean(row["rival_delta"] for row in group),
            "mean_margin_delta": statistics.mean(deltas),
            "median_margin_delta": statistics.median(deltas),
            "minimum_margin_delta": min(deltas),
            "maximum_margin_delta": max(deltas),
        }

    overall = summarize(rows)
    if overall["changed_cells"] == 0:
        verdict = "NO_SIGNAL"
        reason = "candidate produced no complete-cell trace change"
    elif overall["negative_cells"] > 0:
        verdict = "HOLD"
        reason = "at least one development cell regressed"
    elif overall["mean_margin_delta"] <= 0:
        verdict = "HOLD"
        reason = "mean paired margin did not improve"
    else:
        verdict = "ADVANCE"
        reason = "positive paired margin with no negative development cell"

    source_paths = (
        "bootstrap.py",
        "control.py",
        "candidate.py",
        "reserve_release.py",
        "test_reserve_release.py",
        "compare_panel.py",
        "test_compare_panel.py",
    )
    sources = {
        name: {
            "sha256": sha256_file(HERE / name),
            "bytes": (HERE / name).stat().st_size,
        }
        for name in source_paths
    }
    canonical_paths = (
        LAB / "main.py",
        LAB / "titan_runtime.py",
        LAB / "frozen_selected.py",
        LAB / "scheduler.py",
        LAB / "TITAN-CONFIG.json",
    )
    canonical = {
        str(path.relative_to(LAB)): {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in canonical_paths
    }
    return {
        "schema_version": 1,
        "operation": "titan-v3-receding-reserve-release-20260909-01",
        "git_head": expected_head,
        "engine_ref": ENGINE_REF,
        "seeds": control_fp["seeds"],
        "opponents": opponents,
        "control_entrypoint": dict(control["candidate"]),
        "candidate_entrypoint": dict(candidate["candidate"]),
        "source_files": sources,
        "canonical_files": canonical,
        "cells": len(rows),
        "verdict": verdict,
        "reason": reason,
        "overall": overall,
        "by_opponent": {
            opponent: summarize(group)
            for opponent, group in sorted(by_opponent.items())
        },
        "rows": rows,
    }


def markdown(report: Mapping[str, Any]) -> str:
    overall = report["overall"]
    lines = [
        "# TITAN V3 receding reserve-release panel",
        "",
        f"**Verdict:** `{report['verdict']}` — {report['reason']}",
        "",
        f"- Complete paired cells: {report['cells']}",
        f"- Trace-changed cells: {overall['changed_cells']}",
        f"- Mean own-cash delta: {overall['mean_own_delta']:+.3f}",
        f"- Mean rival-cash delta: {overall['mean_rival_delta']:+.3f}",
        f"- Mean margin delta: {overall['mean_margin_delta']:+.3f}",
        f"- Minimum / maximum margin delta: "
        f"{overall['minimum_margin_delta']:+.3f} / "
        f"{overall['maximum_margin_delta']:+.3f}",
        "",
        "| Opponent | Cells | Changed | + / 0 / - | Mean margin Δ | Min margin Δ |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for opponent, values in report["by_opponent"].items():
        lines.append(
            f"| {opponent} | {values['cells']} | {values['changed_cells']} | "
            f"{values['positive_cells']} / {values['zero_cells']} / "
            f"{values['negative_cells']} | "
            f"{values['mean_margin_delta']:+.3f} | "
            f"{values['minimum_margin_delta']:+.3f} |"
        )
    lines.extend(
        [
            "",
            "This is an offline official-interpreter development screen. "
            "It is not a hosted leaderboard score or a canonical-promotion decision.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--head")
    args = parser.parse_args()

    try:
        report = compare(
            load_json(args.control),
            load_json(args.candidate),
            expected_head=args.head,
        )
    except PanelError as exc:
        error = {
            "schema_version": 1,
            "operation": "titan-v3-receding-reserve-release-20260909-01",
            "verdict": "INVALID",
            "reason": str(exc),
            "git_head": args.head,
        }
        atomic_write(
            args.output,
            json.dumps(error, indent=2, sort_keys=True, allow_nan=False) + "\n",
        )
        atomic_write(
            args.markdown,
            "# TITAN V3 receding reserve-release panel\n\n"
            f"**Verdict:** `INVALID` — {exc}\n",
        )
        print(json.dumps(error, sort_keys=True))
        return 2

    atomic_write(
        args.output,
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )
    atomic_write(args.markdown, markdown(report))
    print(json.dumps({
        "verdict": report["verdict"],
        "cells": report["cells"],
        "overall": report["overall"],
    }, sort_keys=True))
    return 0 if report["verdict"] in ("ADVANCE", "NO_SIGNAL") else 1


if __name__ == "__main__":
    raise SystemExit(main())
