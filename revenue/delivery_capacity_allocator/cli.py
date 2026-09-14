from __future__ import annotations

import argparse
import sys
from typing import Optional

from .engine import (
    CapacityError,
    canonical_json,
    compile_current_bytes,
    read_regular_file,
    verify_current_receipt_bytes,
    write_exclusive,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="delivery-capacity-allocator")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("compile", "verify"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--policy", required=True)
        cmd.add_argument("--demands", required=True)
        cmd.add_argument("--reservations", required=True)
        # Deprecated compatibility switches: older automation/tests may still
        # supply these. They are intentionally ignored by the production-current
        # boundary because caller-provided roots cannot authenticate themselves.
        cmd.add_argument("--policy-sha", required=False, help=argparse.SUPPRESS)
        cmd.add_argument("--demand-sha", required=False, help=argparse.SUPPRESS)
        cmd.add_argument("--reservations-sha", required=False, help=argparse.SUPPRESS)
        if name == "compile":
            cmd.add_argument("--out", required=True)
        else:
            cmd.add_argument("--receipt", required=True)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        policy = read_regular_file(args.policy)
        demands = read_regular_file(args.demands)
        reservations = read_regular_file(args.reservations)
        if args.command == "compile":
            receipt = compile_current_bytes(policy, demands, reservations)
            write_exclusive(args.out, canonical_json(receipt))
            print(receipt["current_state"])
            return 0 if receipt["current_state"] == "CURRENT" else 3
        receipt = read_regular_file(args.receipt)
        ok = verify_current_receipt_bytes(policy, demands, reservations, receipt)
        print("VERIFIED_CURRENT" if ok else "NOT_CURRENT_OR_INVALID")
        return 0 if ok else 3
    except CapacityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
