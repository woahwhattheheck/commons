# SPDX-License-Identifier: MIT
from __future__ import annotations
import argparse
import sys
from .ledger import LedgerError, compile_ledger, read_json_file, verify_ledger, write_json_exclusive


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="muse-arbitration-liveness")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("compile")
    c.add_argument("input")
    c.add_argument("output")
    v = sub.add_parser("verify")
    v.add_argument("input")
    v.add_argument("packet")
    args = parser.parse_args(argv)
    try:
        payload = read_json_file(args.input)
        if args.command == "compile":
            packet = compile_ledger(payload)
            write_json_exclusive(args.output, packet)
            print(packet["packet_sha256"])
            return 0
        packet = read_json_file(args.packet)
        if not verify_ledger(payload, packet):
            print("INVALID", file=sys.stderr)
            return 2
        print(packet["packet_sha256"])
        return 0
    except LedgerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
