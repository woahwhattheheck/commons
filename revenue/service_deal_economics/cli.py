from __future__ import annotations

import argparse
import sys

from .engine import (
    DealEconomicsError,
    canonical_json,
    compile_report,
    now_utc,
    read_json_file,
    render_markdown,
    verify_current,
    write_exclusive,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="service-deal-economics")
    sub = parser.add_subparsers(dest="command", required=True)

    compile_cmd = sub.add_parser("compile", help="compile a current owner-review economics packet")
    compile_cmd.add_argument("input")
    compile_cmd.add_argument("output")
    compile_cmd.add_argument("--markdown", dest="markdown")

    verify_cmd = sub.add_parser("verify", help="verify historical receipt and current evidence state")
    verify_cmd.add_argument("input")
    verify_cmd.add_argument("report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "compile":
            packet = read_json_file(args.input)
            report = compile_report(packet, now_utc())
            write_exclusive(args.output, canonical_json(report) + "\n")
            if args.markdown:
                write_exclusive(args.markdown, render_markdown(report))
            print(report["disposition"])
            print(report["receipt_sha256"])
            return 0

        packet = read_json_file(args.input)
        report = read_json_file(args.report)
        result = verify_current(packet, report, now_utc())
        print(canonical_json(result))
        return 0 if result["state"] == "CURRENT_VERIFIED" else 2
    except DealEconomicsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
