#!/usr/bin/env python3
"""Fail-closed Kaggriculture replay gate for observable hand/action cardinality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from gate_common import (
    CANONICAL_MARKET_NO_ORDER,
    EXIT_INVALID,
    EXIT_PASS,
    EXIT_RECEIPT_TAMPERED,
    EXIT_REJECT,
    GateInputError,
    canonical_json_bytes,
)
from gate_core import analyze_replay
from gate_receipt import atomic_write_json, run_gate, seal_receipt, verify_receipt


def _load_receipt(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateInputError(f"cannot read receipt: {exc}") from exc


def _emit_receipt(receipt: Mapping[str, Any], output: str | None) -> None:
    if output:
        atomic_write_json(output, receipt)
    else:
        sys.stdout.buffer.write(canonical_json_bytes(receipt) + b"\n")


def _check_exit_code(verdict: str) -> int:
    if verdict == "PASS":
        return EXIT_PASS
    if verdict == "REJECT":
        return EXIT_REJECT
    return EXIT_INVALID


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="check one replay and emit a sealed receipt")
    check.add_argument("replay")
    check.add_argument("--seat", type=int, required=True)
    check.add_argument("--expected-sha256")
    check.add_argument("--expected-episode-id", type=int)
    check.add_argument("--expected-agent-name")
    check.add_argument("--output")

    verify = subparsers.add_parser("verify", help="verify a sealed receipt without replay bytes")
    verify.add_argument("receipt")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "check":
        receipt = run_gate(
            args.replay,
            seat=args.seat,
            expected_sha256=args.expected_sha256,
            expected_episode_id=args.expected_episode_id,
            expected_agent_name=args.expected_agent_name,
        )
        _emit_receipt(receipt, args.output)
        return _check_exit_code(receipt["verdict"])

    try:
        receipt = _load_receipt(Path(args.receipt))
        valid, message = verify_receipt(receipt)
    except GateInputError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_RECEIPT_TAMPERED
    print(message)
    return EXIT_PASS if valid else EXIT_RECEIPT_TAMPERED


if __name__ == "__main__":
    raise SystemExit(main())
