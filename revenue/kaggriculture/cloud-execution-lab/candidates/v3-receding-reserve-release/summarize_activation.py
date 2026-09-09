# SPDX-License-Identifier: Apache-2.0
"""Validate and summarize paired reserve-release activation evidence."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import tempfile
from typing import Any, Mapping

ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]


class AuditError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(
                AuditError(f"non-finite JSON token {token} in {path}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot read {path}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{path} must contain one JSON object")
    return value


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AuditError(f"{label} is not numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise AuditError(f"{label} is not finite")
    return parsed


def fingerprint(report: Mapping[str, Any], label: str, seed: int) -> dict[str, Any]:
    if report.get("schema_version") != 1:
        raise AuditError(f"{label} schema mismatch")
    if report.get("engine_ref") != ENGINE_REF:
        raise AuditError(f"{label} engine ref mismatch")
    if report.get("seeds") != [seed]:
        raise AuditError(f"{label} seed binding mismatch")
    opponents = report.get("opponents")
    if not isinstance(opponents, Mapping) or set(opponents) != {"arlene"}:
        raise AuditError(f"{label} opponent binding mismatch")
    return {
        "engine_sha256": report.get("engine_sha256"),
        "loader_sha256": report.get("loader_sha256"),
        "evaluator_sha256": report.get("evaluator_sha256"),
        "opponents": dict(opponents),
        "agent_rng_seed": report.get("agent_rng_seed"),
        "limits": report.get("limits"),
    }


def games(report: Mapping[str, Any], label: str, seed: int) -> dict[int, dict[str, Any]]:
    raw = report.get("games")
    if not isinstance(raw, list):
        raise AuditError(f"{label} games is not a list")
    result: dict[int, dict[str, Any]] = {}
    for index, game in enumerate(raw):
        if not isinstance(game, dict):
            raise AuditError(f"{label} game {index} is not an object")
        if game.get("opponent") != "arlene" or game.get("seed") != seed:
            raise AuditError(f"{label} game {index} identity mismatch")
        seat = game.get("candidate_seat")
        if seat not in (0, 1) or seat in result:
            raise AuditError(f"{label} duplicate or invalid seat {seat!r}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise AuditError(f"{label} incomplete seat {seat}: {game.get('failure')}")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise AuditError(f"{label} invalid scores at seat {seat}")
        trace = game.get("trace_sha256")
        if (
            not isinstance(trace, str)
            or len(trace) != 64
            or any(char not in "0123456789abcdef" for char in trace)
        ):
            raise AuditError(f"{label} invalid trace at seat {seat}")
        steps = game.get("steps")
        episode_steps = game.get("episode_steps")
        if (
            isinstance(steps, bool)
            or not isinstance(steps, int)
            or isinstance(episode_steps, bool)
            or not isinstance(episode_steps, int)
            or steps != episode_steps - 1
        ):
            raise AuditError(f"{label} invalid step coverage at seat {seat}")
        copied = dict(game)
        copied["scores"] = [
            finite(scores[0], f"{label} seat {seat} score 0"),
            finite(scores[1], f"{label} seat {seat} score 1"),
        ]
        result[int(seat)] = copied
    if set(result) != {0, 1}:
        raise AuditError(f"{label} must contain both candidate seats")
    return result


def load_telemetry(
    directory: Path,
    expected: set[tuple[int, int]],
    expected_calls: Mapping[tuple[int, int], int],
) -> dict[tuple[int, int], dict[str, Any]]:
    records: dict[tuple[int, int], dict[str, Any]] = {}
    for path in sorted(directory.glob("telemetry-*.json")):
        record = load_json(path)
        if record.get("schema_version") != 1:
            raise AuditError(f"telemetry schema mismatch in {path}")
        seed = record.get("seed")
        seat = record.get("player")
        if isinstance(seed, bool) or not isinstance(seed, int) or seat not in (0, 1):
            raise AuditError(f"invalid telemetry identity in {path}")
        key = (seed, int(seat))
        if key not in expected:
            raise AuditError(f"unexpected telemetry cell {key}")
        if key in records:
            raise AuditError(f"duplicate telemetry cell {key}")
        if record.get("complete") is not True:
            raise AuditError(f"incomplete telemetry cell {key}")
        calls = record.get("calls")
        if calls != expected_calls[key]:
            raise AuditError(
                f"telemetry call coverage mismatch for {key}: "
                f"expected {expected_calls[key]}, got {calls}"
            )
        episode_steps = record.get("episode_steps")
        last_step = record.get("last_step")
        if (
            isinstance(episode_steps, bool)
            or not isinstance(episode_steps, int)
            or isinstance(last_step, bool)
            or not isinstance(last_step, int)
            or last_step != episode_steps - 2
        ):
            raise AuditError(f"telemetry terminal binding mismatch for {key}")
        reasons = record.get("reason_counts")
        if not isinstance(reasons, dict) or any(
            not isinstance(name, str)
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            for name, count in reasons.items()
        ):
            raise AuditError(f"invalid reason counts for {key}")
        records[key] = record
    missing = sorted(expected - set(records))
    if missing:
        raise AuditError(f"missing telemetry cells: {missing}")
    return records


def file_fingerprint(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def source_fingerprints() -> dict[str, dict[str, Any]]:
    paths = {
        "candidate.py": HERE / "candidate.py",
        "control.py": HERE / "control.py",
        "reserve_release.py": HERE / "reserve_release.py",
        "instrumented_candidate.py": HERE / "instrumented_candidate.py",
        "summarize_activation.py": HERE / "summarize_activation.py",
        "main.py": LAB / "main.py",
        "titan_runtime.py": LAB / "titan_runtime.py",
        "frozen_selected.py": LAB / "frozen_selected.py",
        "scheduler.py": LAB / "scheduler.py",
        "TITAN-CONFIG.json": LAB / "TITAN-CONFIG.json",
    }
    return {name: file_fingerprint(path) for name, path in paths.items()}


def compare(results: Path, telemetry: Path, seeds: list[int]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    expected: set[tuple[int, int]] = set()
    expected_calls: dict[tuple[int, int], int] = {}
    provenance: dict[str, Any] | None = None

    for seed in seeds:
        control = load_json(results / f"control-{seed}.json")
        candidate = load_json(results / f"candidate-{seed}.json")
        control_fp = fingerprint(control, f"control {seed}", seed)
        candidate_fp = fingerprint(candidate, f"candidate {seed}", seed)
        if control_fp != candidate_fp:
            raise AuditError(f"control/candidate provenance drift for seed {seed}")
        if provenance is None:
            provenance = control_fp
        elif provenance != control_fp:
            raise AuditError(f"cross-seed provenance drift at seed {seed}")
        left = games(control, f"control {seed}", seed)
        right = games(candidate, f"candidate {seed}", seed)
        for seat in (0, 1):
            expected.add((seed, seat))
            expected_calls[(seed, seat)] = int(right[seat]["steps"])
            control_own = left[seat]["scores"][seat]
            control_rival = left[seat]["scores"][1 - seat]
            candidate_own = right[seat]["scores"][seat]
            candidate_rival = right[seat]["scores"][1 - seat]
            rows.append(
                {
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
                    "trace_changed": (
                        left[seat]["trace_sha256"] != right[seat]["trace_sha256"]
                    ),
                }
            )

    records = load_telemetry(telemetry, expected, expected_calls)
    reason_counts: Counter[str] = Counter()
    certificate_calls = 0
    eligible_certificates = 0
    malformed_certificates = 0
    calls = 0
    games_with_certificates = 0
    games_with_eligible = 0
    first_eligible: list[dict[str, Any]] = []
    busy_counts = Counter()
    for key in sorted(records):
        record = records[key]
        calls += int(record["calls"])
        certificate_calls += int(record.get("certificate_calls", 0))
        eligible = int(record.get("eligible_certificates", 0))
        eligible_certificates += eligible
        malformed_certificates += int(record.get("malformed_certificates", 0))
        reason_counts.update(record["reason_counts"])
        games_with_certificates += int(int(record.get("certificate_calls", 0)) > 0)
        games_with_eligible += int(eligible > 0)
        busy_counts["true"] += int(record.get("joint_producer_busy_true_steps", 0))
        busy_counts["false"] += int(record.get("joint_producer_busy_false_steps", 0))
        busy_counts["other"] += int(record.get("joint_producer_busy_other_steps", 0))
        for example in record.get("first_eligible", []):
            if len(first_eligible) >= 24:
                break
            first_eligible.append({"seed": key[0], "seat": key[1], **dict(example)})

    if malformed_certificates:
        raise AuditError(f"candidate emitted {malformed_certificates} malformed certificates")

    deltas = [row["margin_delta"] for row in rows]
    changed = [row for row in rows if row["trace_changed"]]
    negative = [row for row in rows if row["margin_delta"] < 0]
    positive = [row for row in rows if row["margin_delta"] > 0]
    mean_margin = statistics.mean(deltas)

    if not changed:
        verdict = "UNREACHED" if eligible_certificates == 0 else "ELIGIBLE_NO_ACTION_SIGNAL"
        reason = (
            "no eligible reserve-release certificate and no action trace changed"
            if eligible_certificates == 0
            else "certificate became eligible, but no returned action trace changed"
        )
        exit_code = 4
    elif eligible_certificates == 0:
        verdict = "INVALID"
        reason = "action traces changed without any eligible reserve-release certificate"
        exit_code = 2
    elif negative:
        verdict = "HOLD_REGRESSION"
        reason = "at least one complete paired cell regressed"
        exit_code = 1
    elif mean_margin <= 0:
        verdict = "HOLD_NONPOSITIVE"
        reason = "trace changed, but mean paired margin did not improve"
        exit_code = 1
    else:
        verdict = "ADVANCE"
        reason = "reserve release changed actions with positive mean margin and no negative cell"
        exit_code = 0

    return {
        "schema_version": 1,
        "operation": "titan-v3-reserve-activation-audit-20260909-01",
        "engine_ref": ENGINE_REF,
        "seeds": seeds,
        "cells": len(rows),
        "verdict": verdict,
        "reason": reason,
        "exit_code": exit_code,
        "provenance": provenance,
        "overall": {
            "changed_cells": len(changed),
            "positive_cells": len(positive),
            "zero_cells": sum(delta == 0 for delta in deltas),
            "negative_cells": len(negative),
            "mean_own_delta": statistics.mean(row["own_delta"] for row in rows),
            "mean_rival_delta": statistics.mean(row["rival_delta"] for row in rows),
            "mean_margin_delta": mean_margin,
            "median_margin_delta": statistics.median(deltas),
            "minimum_margin_delta": min(deltas),
            "maximum_margin_delta": max(deltas),
        },
        "activation": {
            "telemetry_cells": len(records),
            "candidate_calls": calls,
            "certificate_calls": certificate_calls,
            "eligible_certificates": eligible_certificates,
            "games_with_certificates": games_with_certificates,
            "games_with_eligible": games_with_eligible,
            "reason_counts": dict(sorted(reason_counts.items())),
            "joint_producer_busy_steps": dict(sorted(busy_counts.items())),
            "first_eligible": first_eligible,
        },
        "changed_rows": changed,
        "rows": rows,
    }


def markdown(report: Mapping[str, Any]) -> str:
    overall = report["overall"]
    activation = report["activation"]
    lines = [
        "# TITAN V3 reserve-release activation audit",
        "",
        f"**Verdict:** `{report['verdict']}` — {report['reason']}",
        "",
        f"- Complete paired cells: {report['cells']}",
        f"- Candidate decisions observed: {activation['candidate_calls']}",
        f"- Trace-changed cells: {overall['changed_cells']}",
        f"- Eligible certificates: {activation['eligible_certificates']}",
        f"- Games with an eligible certificate: {activation['games_with_eligible']}",
        f"- Mean paired margin delta: {overall['mean_margin_delta']:+.3f}",
        f"- Minimum / maximum margin delta: {overall['minimum_margin_delta']:+.3f} / {overall['maximum_margin_delta']:+.3f}",
        "",
        "## Certificate outcomes",
        "",
        "| Reason | Count |",
        "|---|---:|",
    ]
    for reason, count in activation["reason_counts"].items():
        lines.append(f"| `{reason}` | {count} |")
    lines.extend(["", "## Changed paired cells", ""])
    if report["changed_rows"]:
        lines.extend(
            [
                "| Seed | Seat | Own Δ | Rival Δ | Margin Δ |",
                "|---:|---:|---:|---:|---:|",
            ]
        )
        for row in report["changed_rows"]:
            lines.append(
                f"| {row['seed']} | {row['seat']} | {row['own_delta']:+.1f} | "
                f"{row['rival_delta']:+.1f} | {row['margin_delta']:+.1f} |"
            )
    else:
        lines.append("No returned action trace changed.")
    lines.extend(
        [
            "",
            "This is an offline official-interpreter development audit, not a hosted leaderboard result.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--telemetry", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seed-count", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    if args.seed_count < 1:
        parser.error("--seed-count must be positive")
    seeds = list(range(args.seed_start, args.seed_start + args.seed_count))
    try:
        report = compare(args.results, args.telemetry, seeds)
    except AuditError as exc:
        report = {
            "schema_version": 1,
            "operation": "titan-v3-reserve-activation-audit-20260909-01",
            "verdict": "INVALID",
            "reason": str(exc),
            "exit_code": 2,
            "seeds": seeds,
        }
        text = "# TITAN V3 reserve-release activation audit\n\n"
        text += f"**Verdict:** `INVALID` — {exc}\n"
    else:
        text = markdown(report)
    report["git_head"] = args.head
    try:
        report["source_files"] = source_fingerprints()
    except OSError as exc:
        report = {
            "schema_version": 1,
            "operation": "titan-v3-reserve-activation-audit-20260909-01",
            "verdict": "INVALID",
            "reason": f"cannot fingerprint exact sources: {type(exc).__name__}: {exc}",
            "exit_code": 2,
            "seeds": seeds,
            "git_head": args.head,
        }
        text = "# TITAN V3 reserve-release activation audit\n\n"
        text += f"**Verdict:** `INVALID` — {report['reason']}\n"
    atomic_write(
        args.output,
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )
    atomic_write(args.markdown, text)
    print(json.dumps({
        "verdict": report["verdict"],
        "reason": report["reason"],
        "exit_code": report["exit_code"],
        "overall": report.get("overall"),
        "activation": report.get("activation"),
    }, sort_keys=True))
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
