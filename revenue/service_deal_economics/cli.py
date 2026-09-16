from __future__ import annotations

import argparse
import sys

from .authority import AuthorityError
from .current_runtime import (
    assert_current_runtime,
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


def main(
    argv: list[str] | None = None,
    _assert_runtime=assert_current_runtime,
    _compile=compile_current,
    _verify=verify_current_authority,
    _render=render_current_markdown,
    _read=read_json_file,
    _write=write_exclusive,
    _canonical=canonical_json,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        # Fence the graph before any authority-bearing ingress. The CURRENT
        # wrappers repeat the fence before/after clock and verification work.
        _assert_runtime()
        if args.command == "compile":
            packet = _read(args.input)
            report = _compile(packet)
            _write(args.output, _canonical(report) + "\n")
            if args.markdown:
                _write(args.markdown, _render(report))
            print(report["state"])
            print(report["receipt_sha256"])
            return 0 if report["state"] == "READY_FOR_OWNER_QUOTE_REVIEW" else 2

        packet = _read(args.input)
        report = _read(args.report)
        result = _verify(packet, report)
        print(_canonical(result))
        return 0 if result["state"] == "CURRENT_VERIFIED" else 2
    except (DealEconomicsError, AuthorityError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
