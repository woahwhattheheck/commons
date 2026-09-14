from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .canonical import BidVeilError, load_json_strict
from .engine import prove, verify_receipt_integrity, verify_replay


def _write_json(path: str, value: object) -> None:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise BidVeilError(f"refusing to overwrite output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bidveil", description="BidVeil local privacy-qualification semantic harness")
    sub = parser.add_subparsers(dest="command", required=True)

    p_prove = sub.add_parser("prove", help="create a LOCAL_SEMANTIC_SIMULATION_NOT_ZK receipt")
    p_prove.add_argument("opportunity")
    p_prove.add_argument("private_profile")
    p_prove.add_argument("--at", required=True, dest="at")
    p_prove.add_argument("--out", required=True)

    p_integrity = sub.add_parser("verify-integrity", help="verify receipt self-integrity only")
    p_integrity.add_argument("receipt")

    p_replay = sub.add_parser("verify-replay", help="replay local predicates using private source inputs")
    p_replay.add_argument("opportunity")
    p_replay.add_argument("private_profile")
    p_replay.add_argument("receipt")
    p_replay.add_argument("--at", required=True, dest="at")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prove":
            receipt = prove(load_json_strict(args.opportunity), load_json_strict(args.private_profile), args.at)
            _write_json(args.out, receipt)
            print(json.dumps({"decision": receipt["decision"], "mode": receipt["mode"], "receipt_sha256": receipt["receipt_sha256"]}, sort_keys=True))
            return 0
        if args.command == "verify-integrity":
            ok = verify_receipt_integrity(load_json_strict(args.receipt))
            print("VERIFIED_INTEGRITY_ONLY" if ok else "INVALID")
            return 0 if ok else 2
        if args.command == "verify-replay":
            ok = verify_replay(
                load_json_strict(args.opportunity),
                load_json_strict(args.private_profile),
                load_json_strict(args.receipt),
                args.at,
            )
            print("VERIFIED_LOCAL_REPLAY" if ok else "INVALID")
            return 0 if ok else 2
        parser.error("unknown command")
    except BidVeilError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
