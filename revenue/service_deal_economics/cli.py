from __future__ import annotations

import argparse
import sys

from .authority import (
    AuthorityError,
    compile_current,
    render_current_markdown,
    verify_current_authority,
)
from .engine import DealEconomicsError, canonical_json, read_json_file, write_exclusive


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="service-deal-economics")
    sub = parser.add_subparsers(dest="command", required=True)

    compile_cmd = sub.add_parser("compile", help="compile a current authority-gated owner-review economics packet")
    compile_cmd.add_argument("input")
    compile_cmd.add_argument("output")
    compile_cmd.add_argument("--markdown", dest="markdown")

    verify_cmd = sub.add_parser("verify", help="verify historical receipt plus current fixed-host input authority")
    verify_cmd.add_argument("input")
    verify_cmd.add_argument("report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "compile":
            packet = read_json_file(args.input)
            report = compile_current(packet)
            write_exclusive(args.output, canonical_json(report) + "\n")
            if args.markdown:
                write_exclusive(args.markdown, render_current_markdown(report))
            print(report["state"])
            print(report["receipt_sha256"])
            return 0 if report["state"] == "READY_FOR_OWNER_QUOTE_REVIEW" else 2

        packet = read_json_file(args.input)
        report = read_json_file(args.report)
        result = verify_current_authority(packet, report)
        print(canonical_json(result))
        return 0 if result["state"] == "CURRENT_VERIFIED" else 2
    except (DealEconomicsError, AuthorityError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
