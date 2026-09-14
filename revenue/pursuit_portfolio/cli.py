"""CLI for deterministic, authority-bound pursuit portfolio allocation."""
from __future__ import annotations

import argparse
import json

from .core import (
    PortfolioError,
    load_regular_json,
    read_compiled_directory,
    upstream_authority_sha256,
    verify_compiled,
    write_compiled,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pursuit-portfolio")
    sub = parser.add_subparsers(dest="command", required=True)

    digest_p = sub.add_parser(
        "authority-digest",
        help="normalize an upstream authority file and print the digest an independent owner/reviewer may pin",
    )
    digest_p.add_argument("authority")

    compile_p = sub.add_parser("compile", help="compile a current owner-review portfolio")
    compile_p.add_argument("input")
    compile_p.add_argument("authority")
    compile_p.add_argument("output_dir")
    compile_p.add_argument("--trusted-authority-sha256", required=True)

    verify_p = sub.add_parser("verify", help="deterministically verify a compiled directory")
    verify_p.add_argument("output_dir")
    verify_p.add_argument("--trusted-authority-sha256", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "authority-digest":
            authority = load_regular_json(args.authority, "upstream_authority")
            print(upstream_authority_sha256(authority))
            return 0

        if args.command == "compile":
            source = load_regular_json(args.input, "input")
            authority = load_regular_json(args.authority, "upstream_authority")
            compiled = write_compiled(
                source,
                args.output_dir,
                upstream_authority=authority,
                trusted_upstream_authority_sha256=args.trusted_authority_sha256,
            )
            print(json.dumps({
                "output_dir": args.output_dir,
                "receipt_sha256": compiled.receipt["receipt_sha256"],
                "selected_opportunity_ids": compiled.result["selected_opportunity_ids"],
                "selected_priority_units": compiled.result["selected_priority_units"],
                "upstream_authority_sha256": compiled.result["upstream_authority_sha256"],
            }, sort_keys=True))
            return 0

        result, markdown, receipt = read_compiled_directory(args.output_dir)
        verified = verify_compiled(
            result,
            markdown,
            receipt,
            trusted_upstream_authority_sha256=args.trusted_authority_sha256,
        )
        print(json.dumps(verified, sort_keys=True))
        return 0
    except PortfolioError as exc:
        parser.exit(2, f"error: {exc}\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
