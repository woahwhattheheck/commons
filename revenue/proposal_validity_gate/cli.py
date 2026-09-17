from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import ContractError, canonical_bytes, compile_current, verify_current


def _read(path: str) -> bytes:
    return Path(path).read_bytes()


def _emit(value: dict, out: str | None) -> None:
    payload = canonical_bytes(value) + b"\n"
    if out is None:
        sys.stdout.buffer.write(payload)
        return
    path = Path(out)
    with path.open("xb") as handle:
        handle.write(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proposal-validity-gate",
        description="Fail-closed proposal validity / expiry / requote evidence gate.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    compile_parser = sub.add_parser("compile", help="Compile a currentness receipt using process UTC.")
    compile_parser.add_argument("--offer", required=True)
    compile_parser.add_argument("--current", required=True)
    compile_parser.add_argument("--out")

    verify_parser = sub.add_parser("verify", help="Verify a receipt and re-check current process UTC.")
    verify_parser.add_argument("--offer", required=True)
    verify_parser.add_argument("--current", required=True)
    verify_parser.add_argument("--receipt", required=True)
    verify_parser.add_argument("--out")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        offer_raw = _read(args.offer)
        current_raw = _read(args.current)
        if args.command == "compile":
            result = compile_current(offer_raw, current_raw)
        else:
            result = verify_current(offer_raw, current_raw, _read(args.receipt))
        _emit(result, args.out)
        return 0
    except (ContractError, OSError) as exc:
        print(f"proposal-validity-gate: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
