#!/usr/bin/env python3
"""Fail-closed disabled-feature noninterference gate.

Source mode proves configured effects unreachable under false feature bindings.
Trace mode consumes already-spent paired evidence and requires exact identity.
Neither mode runs TITAN or a game.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from gate_common import (
    GateError, _require_verdict, _resolve_under, canonical_bytes, git_blob_sha1,
    load_json, sha256_bytes, write_receipt,
)
from source_gate import audit_source, validate_source_contract
from trace_gate import audit_trace, validate_trace_evidence

def _check_cli_expectation(receipt: Mapping[str, Any], expect: str | None) -> None:
    if expect is None:
        return
    expected = _require_verdict(expect, "--expect")
    if expected != receipt["expected_verdict"]:
        raise GateError(
            f"--expect {expected} disagrees with input expectation {receipt['expected_verdict']}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    source = subparsers.add_parser("source", help="audit source reachability")
    source.add_argument("--repo-root", type=Path, required=True)
    source.add_argument("--contract", type=Path, required=True)
    source.add_argument("--output", type=Path, required=True)
    source.add_argument("--expect", choices=("PASS", "BLOCK"))

    trace = subparsers.add_parser("trace", help="audit already-spent paired evidence")
    trace.add_argument("--evidence", type=Path, required=True)
    trace.add_argument("--output", type=Path, required=True)
    trace.add_argument("--expect", choices=("PASS", "BLOCK"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.mode == "source":
            contract = load_json(args.contract)
            receipt = audit_source(args.repo_root, contract)
            source_contract = validate_source_contract(contract)
            source_path = _resolve_under(
                args.repo_root, source_contract["source"]["path"], "source.path"
            )
            _check_cli_expectation(receipt, args.expect)
            write_receipt(args.output, receipt, (args.contract, source_path))
        else:
            evidence = load_json(args.evidence)
            receipt = audit_trace(evidence)
            _check_cli_expectation(receipt, args.expect)
            write_receipt(args.output, receipt, (args.evidence,))
    except GateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(canonical_bytes(receipt).decode("utf-8"))
    return 0 if receipt["expectation_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
