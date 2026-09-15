"""Offline CLI for the Inkomoko response carrier."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .engine import CarrierError, canonical_json, compile_carrier, strict_json_loads, verify_carrier

MAX_BYTES = 4 * 1024 * 1024


def _read(path: Path):
    try:
        if path.is_symlink() or not path.is_file():
            raise CarrierError(f"input must be an ordinary file: {path}")
        raw = path.read_bytes()
    except OSError as exc:
        raise CarrierError(f"cannot read input: {path}") from exc
    if len(raw) > MAX_BYTES:
        raise CarrierError("input exceeds 4 MiB")
    try:
        return strict_json_loads(raw.decode("utf-8", errors="strict"))
    except UnicodeDecodeError as exc:
        raise CarrierError("input must be strict UTF-8") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inkomoko internal response-readiness carrier")
    sub = parser.add_subparsers(dest="command", required=True)
    comp = sub.add_parser("compile")
    comp.add_argument("packet", type=Path)
    comp.add_argument("acceptance", type=Path)
    comp.add_argument("--evaluated-at", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("packet", type=Path)
    verify.add_argument("acceptance", type=Path)
    verify.add_argument("report", type=Path)
    verify.add_argument("--evaluated-at", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        packet = _read(args.packet)
        acceptance = _read(args.acceptance)
        if args.command == "compile":
            report = compile_carrier(packet, acceptance, args.evaluated_at)
            sys.stdout.write(canonical_json(report) + "\n")
            return 0 if report["projection"]["proposal_state"] == "READY_FOR_OWNER_PROPOSAL_REVIEW" else 3
        report = _read(args.report)
        ok = verify_carrier(packet, acceptance, args.evaluated_at, report)
        sys.stdout.write(canonical_json({"verified": ok}) + "\n")
        return 0 if ok else 2
    except CarrierError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
