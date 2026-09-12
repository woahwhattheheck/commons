#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reduce exact V3.1/V4 gauntlet shards into one causal repair ledger."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
import uuid
from typing import Any, Iterable

SCHEMA = "titan.v5.v31-v4-gauntlet-reduction/v2"
EXPECTED_CALLBACKS = 719
EXACT = {
    "v31": "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361",
    "v4": "4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b",
}
_CELL_RE = re.compile(r"^(?P<opponent>.+)-p(?P<seat>[01])\.json$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ReductionError(ValueError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ReductionError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(token: str) -> None:
    raise ReductionError(f"non-finite JSON constant: {token}")


def _load(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReductionError(f"cannot parse {path}: {exc}") from exc


def _encoded(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_encoded(value)).hexdigest()


def _plain_int(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ReductionError(f"{field} must be a plain int >= {minimum}")
    return value


def _score(value: Any, field: str) -> int | float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ReductionError(f"{field} must be a finite number")
    return value


def _sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ReductionError(f"{field} must be a lowercase SHA256")
    return value


def _scan_roots(
    label: str,
    roots: Iterable[Path],
) -> tuple[dict[tuple[str, int], dict[str, Any]], list[dict[str, Any]]]:
    expected_hash = EXACT[label]
    cells: dict[tuple[str, int], dict[str, Any]] = {}
    receipts: list[dict[str, Any]] = []
    seen_roots: set[Path] = set()
    for raw_root in roots:
        root = Path(raw_root).resolve(strict=True)
        if root in seen_roots:
            raise ReductionError(f"duplicate {label} root: {root}")
        seen_roots.add(root)
        run_path = root / "run.json"
        run = _load(run_path)
        if type(run) is not dict:
            raise ReductionError(f"{run_path} must be an object")
        if run.get("candidate_sha256") != expected_hash:
            raise ReductionError(f"{label} run candidate hash mismatch in {root}")
        if run.get("group") != "all":
            raise ReductionError(f"{label} run must use group=all: {root}")
        shard = _plain_int(run.get("shard"), f"{root}.shard")
        shards = _plain_int(run.get("shards"), f"{root}.shards", 1)
        if shard >= shards:
            raise ReductionError(f"invalid shard topology in {root}")
        index_sha256 = _sha256(run.get("index_sha256"), f"{root}.index_sha256")
        engine = run.get("engine")
        if not isinstance(engine, dict) or not engine:
            raise ReductionError(f"{root}.engine must be a nonempty object")
        receipts.append({
            "root_name": root.name,
            "run_sha256": hashlib.sha256(run_path.read_bytes()).hexdigest(),
            "shard": shard,
            "shards": shards,
            "selected_fixtures": _plain_int(
                run.get("selected_fixtures"),
                f"{root}.selected_fixtures",
            ),
            "index_sha256": index_sha256,
            "evaluator_sha256": _sha256(
                run.get("evaluator_sha256"),
                f"{root}.evaluator_sha256",
            ),
            "loader_sha256": _sha256(
                run.get("loader_sha256"),
                f"{root}.loader_sha256",
            ),
            "engine": engine,
        })
        for path in sorted(root.glob("*.json")):
            match = _CELL_RE.match(path.name)
            if not match:
                continue
            record = _load(path)
            if type(record) is not dict:
                raise ReductionError(f"game must be an object: {path}")
            opponent = match.group("opponent")
            seat = int(match.group("seat"))
            if record.get("opponent") != opponent:
                raise ReductionError(f"filename/opponent mismatch: {path}")
            if record.get("candidate_sha256") != expected_hash:
                raise ReductionError(f"{label} cell candidate hash mismatch: {path}")
            submission_id = record.get("submission_id")
            family = record.get("family")
            memberships = record.get("memberships")
            if type(submission_id) is not int or submission_id <= 0:
                raise ReductionError(f"invalid submission_id: {path}")
            if not isinstance(family, str) or not family:
                raise ReductionError(f"invalid family: {path}")
            if record.get("kind") != "recorded_trace" or record.get("adaptive") is not False:
                raise ReductionError(f"cell is not an immutable recorded trace: {path}")
            if type(record.get("recorded_orientation")) is not bool:
                raise ReductionError(f"invalid recorded_orientation: {path}")
            if not isinstance(memberships, list):
                raise ReductionError(f"invalid memberships: {path}")
            scores = record.get("scores")
            if record.get("status") == "complete":
                if _plain_int(record.get("steps"), f"{path}.steps") != EXPECTED_CALLBACKS:
                    raise ReductionError(f"complete cell has wrong callback count: {path}")
                if not isinstance(scores, list) or len(scores) != 2:
                    raise ReductionError(f"complete cell scores must have length 2: {path}")
                scores = [_score(value, f"{path}.scores") for value in scores]
                margin = scores[seat] - scores[1 - seat]
            else:
                margin = None
            key = (opponent, seat)
            if key in cells:
                raise ReductionError(f"duplicate {label} cell {key!r}")
            cells[key] = {
                "opponent": opponent,
                "seat": seat,
                "submission_id": submission_id,
                "family": family,
                "kind": record.get("kind"),
                "adaptive": record.get("adaptive"),
                "recorded_orientation": record.get("recorded_orientation"),
                "memberships": memberships,
                "status": record.get("status"),
                "steps": record.get("steps"),
                "scores": scores,
                "margin": margin,
                "source_file": path.name,
            }
    if not receipts:
        raise ReductionError(f"no {label} shard roots supplied")
    receipts.sort(key=lambda row: (row["shards"], row["shard"], row["root_name"]))
    return cells, receipts


def _panel_topology(
    v31_runs: list[dict[str, Any]],
    v4_runs: list[dict[str, Any]],
    expected_cells_override: int | None,
) -> tuple[dict[str, Any], int | None]:
    def inspect(label: str, runs: list[dict[str, Any]]) -> dict[str, Any]:
        shard_totals = {row["shards"] for row in runs}
        if len(shard_totals) != 1:
            raise ReductionError(f"{label} roots disagree on declared shard count")
        declared = next(iter(shard_totals))
        by_shard: dict[int, dict[str, Any]] = {}
        index_values = {row["index_sha256"] for row in runs}
        evaluator_values = {row["evaluator_sha256"] for row in runs}
        loader_values = {row["loader_sha256"] for row in runs}
        engine_values = {_digest(row["engine"]) for row in runs}
        if len(index_values) != 1:
            raise ReductionError(f"{label} roots disagree on corpus index identity")
        if len(evaluator_values) != 1:
            raise ReductionError(f"{label} roots disagree on evaluator identity")
        if len(loader_values) != 1:
            raise ReductionError(f"{label} roots disagree on loader identity")
        if len(engine_values) != 1:
            raise ReductionError(f"{label} roots disagree on engine identity")
        for row in runs:
            shard = row["shard"]
            if shard in by_shard:
                raise ReductionError(f"duplicate {label} shard receipt: {shard}")
            by_shard[shard] = row
        expected_shards = set(range(declared))
        observed_shards = set(by_shard)
        return {
            "declared_shards": declared,
            "observed_shards": sorted(observed_shards),
            "complete_shard_set": observed_shards == expected_shards,
            "selected_fixtures_observed": sum(
                row["selected_fixtures"] for row in runs
            ),
            "index_sha256": next(iter(index_values)),
            "evaluator_sha256": next(iter(evaluator_values)),
            "loader_sha256": next(iter(loader_values)),
            "engine_digest": next(iter(engine_values)),
            "by_shard": by_shard,
        }

    left = inspect("v31", v31_runs)
    right = inspect("v4", v4_runs)
    if left["declared_shards"] != right["declared_shards"]:
        raise ReductionError("V3.1/V4 declared shard counts differ")
    if left["index_sha256"] != right["index_sha256"]:
        raise ReductionError("V3.1/V4 corpus index identities differ")
    if left["evaluator_sha256"] != right["evaluator_sha256"]:
        raise ReductionError("V3.1/V4 evaluator identities differ")
    if left["loader_sha256"] != right["loader_sha256"]:
        raise ReductionError("V3.1/V4 loader identities differ")
    if left["engine_digest"] != right["engine_digest"]:
        raise ReductionError("V3.1/V4 engine identities differ")
    shared_shards = set(left["by_shard"]) & set(right["by_shard"])
    for shard in shared_shards:
        if (
            left["by_shard"][shard]["selected_fixtures"]
            != right["by_shard"][shard]["selected_fixtures"]
        ):
            raise ReductionError(
                f"V3.1/V4 selected fixture count differs for shard {shard}"
            )
    complete_topology = left["complete_shard_set"] and right["complete_shard_set"]
    inferred_cells = None
    if complete_topology:
        inferred_fixtures = left["selected_fixtures_observed"]
        if inferred_fixtures != right["selected_fixtures_observed"]:
            raise ReductionError("V3.1/V4 complete fixture totals differ")
        inferred_cells = inferred_fixtures * 2
    if expected_cells_override is not None:
        expected_cells_override = _plain_int(
            expected_cells_override,
            "expected_cells",
            1,
        )
        if inferred_cells is not None and expected_cells_override != inferred_cells:
            raise ReductionError(
                "expected_cells override disagrees with authenticated complete "
                f"shard receipts: {expected_cells_override} != {inferred_cells}"
            )
        expected_cells = expected_cells_override
    else:
        expected_cells = inferred_cells
    public_left = {key: value for key, value in left.items() if key != "by_shard"}
    public_right = {key: value for key, value in right.items() if key != "by_shard"}
    return {
        "v31": public_left,
        "v4": public_right,
        "complete_cross_version_shard_topology": complete_topology,
        "inferred_expected_cells": inferred_cells,
        "expected_cells_override": expected_cells_override,
    }, expected_cells


def _same_authority(
    left: dict[str, Any],
    right: dict[str, Any],
    key: tuple[str, int],
) -> None:
    for field in (
        "submission_id",
        "family",
        "kind",
        "adaptive",
        "recorded_orientation",
        "memberships",
    ):
        if left.get(field) != right.get(field):
            raise ReductionError(
                f"cross-version metadata mismatch for {key!r}: {field}"
            )


def _stats(values: list[int | float]) -> dict[str, Any]:
    return {
        "count": len(values),
        "v31_better": sum(value > 0 for value in values),
        "tied": sum(value == 0 for value in values),
        "v4_better": sum(value < 0 for value in values),
        "sum_margin_delta_v31_minus_v4": sum(values) if values else None,
        "mean_margin_delta_v31_minus_v4": statistics.mean(values) if values else None,
        "median_margin_delta_v31_minus_v4": statistics.median(values) if values else None,
        "min_margin_delta_v31_minus_v4": min(values) if values else None,
        "max_margin_delta_v31_minus_v4": max(values) if values else None,
    }


def reduce_roots(
    v31_roots: Iterable[Path],
    v4_roots: Iterable[Path],
    *,
    expected_cells: int | None = None,
) -> dict[str, Any]:
    v31, v31_runs = _scan_roots("v31", v31_roots)
    v4, v4_runs = _scan_roots("v4", v4_roots)
    topology, expected_cells = _panel_topology(
        v31_runs,
        v4_runs,
        expected_cells,
    )
    keys = sorted(set(v31) | set(v4))
    paired = sorted(set(v31) & set(v4))
    cells: list[dict[str, Any]] = []
    by_family: dict[str, list[int | float]] = {}
    by_submission: dict[str, list[int | float]] = {}
    for key in paired:
        left, right = v31[key], v4[key]
        _same_authority(left, right, key)
        complete = left["margin"] is not None and right["margin"] is not None
        delta = left["margin"] - right["margin"] if complete else None
        row = {
            "opponent": key[0],
            "seat": key[1],
            "submission_id": left["submission_id"],
            "family": left["family"],
            "recorded_orientation": left["recorded_orientation"],
            "status": "complete_pair" if complete else "incomplete_pair",
            "v31_scores": left["scores"],
            "v4_scores": right["scores"],
            "v31_margin": left["margin"],
            "v4_margin": right["margin"],
            "margin_delta_v31_minus_v4": delta,
        }
        cells.append(row)
        if delta is not None:
            by_family.setdefault(left["family"], []).append(delta)
            by_submission.setdefault(str(left["submission_id"]), []).append(delta)
    complete_values = [
        row["margin_delta_v31_minus_v4"]
        for row in cells
        if row["margin_delta_v31_minus_v4"] is not None
    ]
    missing_v31 = [
        {"opponent": key[0], "seat": key[1]}
        for key in sorted(set(v4) - set(v31))
    ]
    missing_v4 = [
        {"opponent": key[0], "seat": key[1]}
        for key in sorted(set(v31) - set(v4))
    ]
    opponents: dict[str, set[int]] = {}
    for opponent, seat in paired:
        opponents.setdefault(opponent, set()).add(seat)
    both_seats = (
        all(seats == {0, 1} for seats in opponents.values())
        if opponents
        else False
    )
    panel_complete = (
        topology["complete_cross_version_shard_topology"]
        and expected_cells is not None
        and len(keys) == expected_cells
        and len(paired) == expected_cells
        and len(complete_values) == expected_cells
        and not missing_v31
        and not missing_v4
        and both_seats
    )
    family_rows = [
        {"family": name, **_stats(values)}
        for name, values in by_family.items()
    ]
    family_rows.sort(
        key=lambda row: (
            -(row["mean_margin_delta_v31_minus_v4"] or 0),
            row["family"],
        )
    )
    submission_rows = [
        {"submission_id": name, **_stats(values)}
        for name, values in by_submission.items()
    ]
    submission_rows.sort(
        key=lambda row: (
            -(row["mean_margin_delta_v31_minus_v4"] or 0),
            row["submission_id"],
        )
    )
    hotspots = [
        {
            "opponent": row["opponent"],
            "seat": row["seat"],
            "submission_id": row["submission_id"],
            "family": row["family"],
            "margin_delta_v31_minus_v4": row[
                "margin_delta_v31_minus_v4"
            ],
        }
        for row in cells
        if row["margin_delta_v31_minus_v4"] is not None
        and row["margin_delta_v31_minus_v4"] > 0
    ]
    hotspots.sort(
        key=lambda row: (
            -row["margin_delta_v31_minus_v4"],
            row["opponent"],
            row["seat"],
        )
    )
    authority = {
        "v31_archive_sha256": EXACT["v31"],
        "v4_archive_sha256": EXACT["v4"],
        "panel_topology": topology,
        "v31_runs": v31_runs,
        "v4_runs": v4_runs,
    }
    return {
        "schema": SCHEMA,
        "authority": authority,
        "authority_sha256": _digest(authority),
        "expected_cells": expected_cells,
        "observed_union_cells": len(keys),
        "paired_cells": len(paired),
        "complete_pairs": len(complete_values),
        "opponent_fixture_count": len(opponents),
        "both_seats_for_all_paired_opponents": both_seats,
        "panel_complete": panel_complete,
        "missing_v31": missing_v31,
        "missing_v4": missing_v4,
        "summary": _stats(complete_values),
        "by_family": family_rows,
        "by_submission": submission_rows,
        "regression_hotspots": hotspots,
        "cells": cells,
    }


def _atomic_write(path: Path, report: dict[str, Any]) -> None:
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    payload = json.dumps(
        report,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("x", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v31-root", action="append", type=Path, required=True)
    parser.add_argument("--v4-root", action="append", type=Path, required=True)
    parser.add_argument(
        "--expected-cells",
        type=int,
        default=None,
        help=(
            "Optional cross-check only. Complete shard receipts derive final "
            "cardinality automatically; a conflicting override is rejected."
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = reduce_roots(
            args.v31_root,
            args.v4_root,
            expected_cells=args.expected_cells,
        )
        _atomic_write(args.output, report)
    except (ReductionError, OSError, TypeError, ValueError) as exc:
        print(f"reduce_gauntlet: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "panel_complete": report["panel_complete"],
        "expected_cells": report["expected_cells"],
        "paired_cells": report["paired_cells"],
        "complete_pairs": report["complete_pairs"],
        **report["summary"],
    }, sort_keys=True))
    return 0 if report["panel_complete"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
