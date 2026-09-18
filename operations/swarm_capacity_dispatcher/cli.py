"""CLI for the offline swarm capacity dispatcher."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .dispatcher import ContractError, dispatch, verify_receipt


def _load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dump(value) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="swarm-capacity-dispatcher")
    sub = parser.add_subparsers(dest="command", required=True)

    p_dispatch = sub.add_parser("dispatch")
    p_dispatch.add_argument("--workers", required=True)
    p_dispatch.add_argument("--orders", required=True)
    p_dispatch.add_argument("--leases", required=True)
    p_dispatch.add_argument("--output")

    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--workers", required=True)
    p_verify.add_argument("--orders", required=True)
    p_verify.add_argument("--leases", required=True)
    p_verify.add_argument("--receipt", required=True)

    args = parser.parse_args(argv)
    try:
        workers = _load(args.workers)
        orders = _load(args.orders)
        leases = _load(args.leases)
        if args.command == "dispatch":
            receipt = dispatch(workers, orders, leases)
            rendered = _dump(receipt)
            if args.output:
                Path(args.output).write_text(rendered, encoding="utf-8")
            else:
                sys.stdout.write(rendered)
            return 0
        receipt = _load(args.receipt)
        ok = verify_receipt(workers, orders, leases, receipt)
        sys.stdout.write("VALID\n" if ok else "INVALID\n")
        return 0 if ok else 2
    except (OSError, json.JSONDecodeError, ContractError, ValueError) as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
