#!/usr/bin/env python3
"""CLI for the procurement loss/debrief remediation loop."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .compiler import RemediationError, compile_record, load_json_file, render_receipt
from .verifier import verify_receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.procurement_loss_remediation")
    sub = parser.add_subparsers(dest="command", required=True)

    compile_cmd = sub.add_parser("compile", help="compile remediation input into a receipt")
    compile_cmd.add_argument("input")
    compile_cmd.add_argument("receipt")

    verify_cmd = sub.add_parser("verify", help="verify a receipt against remediation input")
    verify_cmd.add_argument("input")
    verify_cmd.add_argument("receipt")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        source = load_json_file(args.input)
        if args.command == "compile":
            receipt = compile_record(source)
            Path(args.receipt).write_bytes(render_receipt(receipt))
            print(
                json.dumps(
                    {
                        "backlog_state": receipt["backlog_state"],
                        "receipt_sha256": receipt["receipt_sha256"],
                    },
                    sort_keys=True,
                )
            )
            return 0
        receipt = load_json_file(args.receipt)
        result = verify_receipt(source, receipt)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, RemediationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
