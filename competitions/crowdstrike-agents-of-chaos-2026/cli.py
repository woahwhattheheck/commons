#!/usr/bin/env python3
"""CLI for the offline Agents of Chaos manual-observation workbench."""

from __future__ import annotations

import argparse
import json
import sys

from workbench import ValidationError, compile_ledger, load_json_file, publish_bundle, verify_packet


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline manual prompt-efficiency workbench; never contacts the contest")
    sub = parser.add_subparsers(dest="command", required=True)

    compile_p = sub.add_parser("compile", help="compile a strict manual ledger and publish a create-exclusive review bundle")
    compile_p.add_argument("ledger")
    compile_p.add_argument("--out-dir", required=True)

    verify_p = sub.add_parser("verify", help="recompute a packet from its source ledger and compare exact canonical semantics")
    verify_p.add_argument("ledger")
    verify_p.add_argument("packet")

    summary_p = sub.add_parser("summary", help="print the deterministic packet to stdout without publishing files")
    summary_p.add_argument("ledger")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "compile":
            ledger = load_json_file(args.ledger)
            packet = compile_ledger(ledger)
            paths = publish_bundle(packet, args.out_dir)
            print(json.dumps({"ok": True, "packet_sha256": packet["packet_sha256"], "paths": paths}, sort_keys=True))
            return 0
        if args.command == "verify":
            ledger = load_json_file(args.ledger)
            packet = load_json_file(args.packet)
            valid = verify_packet(ledger, packet)
            print(json.dumps({"valid": valid}, sort_keys=True))
            return 0 if valid else 2
        if args.command == "summary":
            ledger = load_json_file(args.ledger)
            print(json.dumps(compile_ledger(ledger), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0
    except ValidationError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
