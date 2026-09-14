from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import ContractError, evaluate, parse_orders, parse_scenario, verify_receipt


def _load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="darpa-dv026-market-poc")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("evaluate")
    run.add_argument("scenario")
    run.add_argument("orders")
    run.add_argument(
        "--mechanism",
        choices=["CONTINUOUS_DOUBLE_AUCTION", "UNIFORM_PRICE_CALL"],
        default="CONTINUOUS_DOUBLE_AUCTION",
    )
    run.add_argument("--threshold-bps", type=int, default=9000)
    run.add_argument("--out")

    verify = sub.add_parser("verify")
    verify.add_argument("scenario")
    verify.add_argument("orders")
    verify.add_argument("receipt")

    args = parser.parse_args(argv)
    try:
        scenario = parse_scenario(_load(args.scenario))
        orders = parse_orders(scenario, _load(args.orders))
        if args.command == "evaluate":
            receipt = evaluate(
                scenario,
                orders,
                mechanism=args.mechanism,
                efficiency_threshold_bps=args.threshold_bps,
            )
            text = json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
            if args.out:
                Path(args.out).write_text(text, encoding="utf-8")
            else:
                sys.stdout.write(text)
            return 0 if receipt["efficiency_gate_pass"] else 3

        ok = verify_receipt(scenario, orders, _load(args.receipt))
        sys.stdout.write(json.dumps({"verified": ok}, sort_keys=True) + "\n")
        return 0 if ok else 4
    except (ContractError, OSError, json.JSONDecodeError, ValueError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
