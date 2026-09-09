#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Atomic fail-closed promotion gate against two distinct predecessors.

The existing paired-game gate proves one candidate/baseline comparison.  This
wrapper snapshots both comparison bundles and one shared candidate panel before
running either gate, then rejects identity, grid, policy, or cache-binding drift.

Exit 0 = PROMOTE against both predecessors.
Exit 2 = INVALID evidence or cross-comparison binding.
Exit 3 = valid evidence, but at least one predecessor comparison was REJECTED.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping, Sequence

import gate as single_gate
from gate_common import (
    GateError,
    MAX_JSONL_BYTES,
    MAX_JSON_BYTES,
    SCHEMA_VERSION,
    atomic_write_json,
    sha256_file,
    snapshot_regular_file,
)

_SLOTS = ("predecessor_a", "predecessor_b")
_SHARED_PROVENANCE = (
    "engine_commit",
    "engine_sha256",
    "runner_commit",
    "runner_sha256",
    "candidate_artifact_sha256",
)


def _normalized_grid(report: Mapping[str, Any]) -> dict[str, Any]:
    grid = report["grid"]
    return {
        "seeds": sorted(grid["seeds"]),
        "opponents": sorted(grid["opponents"]),
        "seats": sorted(grid["seats"]),
        "expected_cells": grid["expected_cells"],
    }


def _bind_inner_inputs(
    *,
    report: Mapping[str, Any],
    outer_hashes: Mapping[str, str],
    slot: str,
) -> None:
    expected = {
        "contract": outer_hashes[f"{slot}_contract"],
        "evidence": outer_hashes[f"{slot}_evidence"],
        "baseline_games": outer_hashes[f"{slot}_games"],
        "candidate_games": outer_hashes["candidate_games"],
    }
    observed = report.get("input_sha256")
    if observed != expected:
        raise GateError(
            f"{slot}: single-gate input binding drift; "
            f"expected={json.dumps(expected, sort_keys=True)}, "
            f"observed={json.dumps(observed, sort_keys=True)}"
        )


def _validate_cross_comparison(
    first: Mapping[str, Any],
    second: Mapping[str, Any],
    *,
    candidate_games_sha256: str,
) -> dict[str, Any]:
    drift: dict[str, Any] = {}

    if first["candidate_name"] != second["candidate_name"]:
        drift["candidate_name"] = {
            "predecessor_a": first["candidate_name"],
            "predecessor_b": second["candidate_name"],
        }

    first_shared = {key: first["provenance"][key] for key in _SHARED_PROVENANCE}
    second_shared = {key: second["provenance"][key] for key in _SHARED_PROVENANCE}
    if first_shared != second_shared:
        drift["shared_provenance"] = {
            key: {
                "predecessor_a": first_shared[key],
                "predecessor_b": second_shared[key],
            }
            for key in _SHARED_PROVENANCE
            if first_shared[key] != second_shared[key]
        }

    first_grid = _normalized_grid(first)
    second_grid = _normalized_grid(second)
    if first_grid != second_grid:
        drift["grid"] = {
            "predecessor_a": first_grid,
            "predecessor_b": second_grid,
        }

    if first["policy"] != second["policy"]:
        drift["policy"] = {
            "predecessor_a": first["policy"],
            "predecessor_b": second["policy"],
        }

    first_candidate_games = first["input_sha256"]["candidate_games"]
    second_candidate_games = second["input_sha256"]["candidate_games"]
    if first_candidate_games != candidate_games_sha256 or second_candidate_games != candidate_games_sha256:
        drift["candidate_games_sha256"] = {
            "outer_snapshot": candidate_games_sha256,
            "predecessor_a": first_candidate_games,
            "predecessor_b": second_candidate_games,
        }

    first_baseline_name = first["baseline_name"]
    second_baseline_name = second["baseline_name"]
    if first_baseline_name == second_baseline_name:
        drift["baseline_name"] = {
            "error": "predecessor names must be distinct",
            "value": first_baseline_name,
        }

    first_baseline_sha = first["provenance"]["baseline_artifact_sha256"]
    second_baseline_sha = second["provenance"]["baseline_artifact_sha256"]
    if first_baseline_sha == second_baseline_sha:
        drift["baseline_artifact_sha256"] = {
            "error": "predecessor artifacts must be distinct",
            "value": first_baseline_sha,
        }

    candidate_sha = first_shared["candidate_artifact_sha256"]
    aliases = []
    if candidate_sha == first_baseline_sha:
        aliases.append("predecessor_a")
    if candidate_sha == second_baseline_sha:
        aliases.append("predecessor_b")
    if aliases:
        drift["candidate_artifact_alias"] = {
            "candidate_artifact_sha256": candidate_sha,
            "aliases": aliases,
        }

    if drift:
        raise GateError(
            "dual-predecessor comparison drift: "
            + json.dumps(drift, sort_keys=True, allow_nan=False)
        )

    return {
        "candidate_name": first["candidate_name"],
        **first_shared,
        "candidate_games_sha256": candidate_games_sha256,
        "grid": first_grid,
        "policy": first["policy"],
    }


def run_dual_gate(
    *,
    predecessor_a_contract_path: Path,
    predecessor_a_evidence_path: Path,
    predecessor_a_games_path: Path,
    predecessor_b_contract_path: Path,
    predecessor_b_evidence_path: Path,
    predecessor_b_games_path: Path,
    candidate_games_path: Path,
) -> tuple[dict[str, Any], int]:
    sources = {
        "predecessor_a_contract": (
            predecessor_a_contract_path,
            MAX_JSON_BYTES,
            "predecessor A contract",
        ),
        "predecessor_a_evidence": (
            predecessor_a_evidence_path,
            MAX_JSON_BYTES,
            "predecessor A evidence",
        ),
        "predecessor_a_games": (
            predecessor_a_games_path,
            MAX_JSONL_BYTES,
            "predecessor A games",
        ),
        "predecessor_b_contract": (
            predecessor_b_contract_path,
            MAX_JSON_BYTES,
            "predecessor B contract",
        ),
        "predecessor_b_evidence": (
            predecessor_b_evidence_path,
            MAX_JSON_BYTES,
            "predecessor B evidence",
        ),
        "predecessor_b_games": (
            predecessor_b_games_path,
            MAX_JSONL_BYTES,
            "predecessor B games",
        ),
        "candidate_games": (
            candidate_games_path,
            MAX_JSONL_BYTES,
            "shared candidate games",
        ),
    }

    with TemporaryDirectory(prefix="titan-v3-dual-predecessor-gate-") as directory:
        snapshot_root = Path(directory)
        snapshots = {
            name: snapshot_regular_file(
                path,
                directory=snapshot_root,
                max_bytes=max_bytes,
                label=label,
            )
            for name, (path, max_bytes, label) in sources.items()
        }
        paths = {name: snapshot.path for name, snapshot in snapshots.items()}
        hashes = {name: snapshot.sha256 for name, snapshot in snapshots.items()}
        sizes = {name: snapshot.bytes for name, snapshot in snapshots.items()}

        reports: dict[str, dict[str, Any]] = {}
        codes: dict[str, int] = {}
        for slot in _SLOTS:
            report, code = single_gate.run_gate(
                contract_path=paths[f"{slot}_contract"],
                evidence_path=paths[f"{slot}_evidence"],
                baseline_path=paths[f"{slot}_games"],
                candidate_path=paths["candidate_games"],
            )
            _bind_inner_inputs(report=report, outer_hashes=hashes, slot=slot)
            reports[slot] = report
            codes[slot] = code

        shared = _validate_cross_comparison(
            reports["predecessor_a"],
            reports["predecessor_b"],
            candidate_games_sha256=hashes["candidate_games"],
        )

        changed_snapshots = {}
        for name, snapshot in snapshots.items():
            observed = sha256_file(snapshot.path)
            if observed != snapshot.sha256:
                changed_snapshots[name] = {
                    "expected": snapshot.sha256,
                    "observed": observed,
                }
        if changed_snapshots:
            raise GateError(
                "private dual-gate input snapshot changed during evaluation: "
                + json.dumps(changed_snapshots, sort_keys=True)
            )

        promote = all(codes[slot] == 0 for slot in _SLOTS)
        report = {
            "schema_version": SCHEMA_VERSION,
            "verdict": "PROMOTE" if promote else "REJECT",
            "valid": True,
            "mode": "dual-predecessor",
            "input_sha256": hashes,
            "input_bytes": sizes,
            "input_binding": (
                "all seven inputs snapshotted before either comparison; "
                "one candidate snapshot is parsed by both single gates"
            ),
            "shared": shared,
            "comparison_exit_codes": codes,
            "comparisons": reports,
        }
        return report, 0 if promote else 3


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for slot in _SLOTS:
        prefix = slot.replace("_", "-")
        parser.add_argument(f"--{prefix}-contract", required=True, type=Path)
        parser.add_argument(f"--{prefix}-evidence", required=True, type=Path)
        parser.add_argument(f"--{prefix}-games", required=True, type=Path)
    parser.add_argument("--candidate-games", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    try:
        report, code = run_dual_gate(
            predecessor_a_contract_path=args.predecessor_a_contract,
            predecessor_a_evidence_path=args.predecessor_a_evidence,
            predecessor_a_games_path=args.predecessor_a_games,
            predecessor_b_contract_path=args.predecessor_b_contract,
            predecessor_b_evidence_path=args.predecessor_b_evidence,
            predecessor_b_games_path=args.predecessor_b_games,
            candidate_games_path=args.candidate_games,
        )
    except (GateError, OSError, UnicodeError) as exc:
        report, code = {
            "schema_version": SCHEMA_VERSION,
            "verdict": "INVALID",
            "valid": False,
            "error": str(exc),
        }, 2

    atomic_write_json(args.report, report)
    if not args.quiet:
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
