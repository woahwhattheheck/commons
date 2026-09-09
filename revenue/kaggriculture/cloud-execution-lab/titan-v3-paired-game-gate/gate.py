#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed promotion gate for paired Kaggriculture GAMES.jsonl panels.

Exit 0 = PROMOTE, 2 = INVALID evidence, 3 = valid evidence that is REJECTED.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from contract import validate_contract, validate_evidence
from gate_common import (
    GateError, MAX_JSONL_BYTES, MAX_JSON_BYTES, SCHEMA_VERSION,
    atomic_write_json, read_json, regular_file, sha256_file,
)
from metrics import analyze, evaluate_policy
from panel_load import expected_keys, load_games


def run_gate(
    *, contract_path: Path, evidence_path: Path,
    baseline_path: Path, candidate_path: Path,
) -> tuple[dict[str, Any], int]:
    paths = {
        "contract": regular_file(contract_path, max_bytes=MAX_JSON_BYTES, label="contract"),
        "evidence": regular_file(evidence_path, max_bytes=MAX_JSON_BYTES, label="evidence"),
        "baseline_games": regular_file(baseline_path, max_bytes=MAX_JSONL_BYTES, label="baseline games"),
        "candidate_games": regular_file(candidate_path, max_bytes=MAX_JSONL_BYTES, label="candidate games"),
    }
    hashes = {name: sha256_file(path) for name, path in paths.items()}
    contract = validate_contract(read_json(paths["contract"], label="contract"))
    evidence = validate_evidence(read_json(paths["evidence"], label="evidence"), contract)
    expected = expected_keys(contract)
    baseline = load_games(paths["baseline_games"], label="baseline games", expected=expected)
    candidate = load_games(paths["candidate_games"], label="candidate games", expected=expected)
    if set(baseline) != set(candidate):
        raise GateError("baseline/candidate cell-key sets differ")
    metrics = analyze(baseline, candidate)
    checks = evaluate_policy(metrics, contract["policy"])
    promote = all(item["pass"] for item in checks)
    report = {
        "schema_version": SCHEMA_VERSION,
        "verdict": "PROMOTE" if promote else "REJECT",
        "valid": True,
        "panel_id": contract["panel_id"],
        "baseline_name": contract["baseline_name"],
        "candidate_name": contract["candidate_name"],
        "input_sha256": hashes,
        "provenance": evidence["provenance"],
        "exact_command": evidence["exact_command"],
        "grid": {
            "seeds": contract["seeds"], "opponents": contract["opponents"],
            "seats": contract["seats"], "expected_cells": contract["expected_cells"],
            "observed_baseline_cells": len(baseline),
            "observed_candidate_cells": len(candidate),
        },
        "policy": contract["policy"], "checks": checks, "metrics": metrics,
    }
    return report, 0 if promote else 3


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("contract", "evidence", "baseline", "candidate", "report"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    try:
        report, code = run_gate(
            contract_path=args.contract, evidence_path=args.evidence,
            baseline_path=args.baseline, candidate_path=args.candidate,
        )
    except (GateError, OSError, UnicodeError) as exc:
        report, code = {
            "schema_version": SCHEMA_VERSION, "verdict": "INVALID",
            "valid": False, "error": str(exc),
        }, 2
    atomic_write_json(args.report, report)
    if not args.quiet:
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
