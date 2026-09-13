"""Production CLI for fixed-host current Pursuit Portfolio v2 review."""
from __future__ import annotations

import argparse
import json

from .core import PortfolioError
from .host import (
    compile_current,
    load_candidate_json,
    publish_current,
    verify_current_directory,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pursuit-portfolio")
    sub = parser.add_subparsers(dest="command", required=True)

    compile_p = sub.add_parser(
        "compile",
        help="compile under fixed host latest-authority state and verifier-owned UTC",
    )
    compile_p.add_argument("input")
    compile_p.add_argument("authority")
    compile_p.add_argument(
        "output_dir", help="existing empty owner-controlled output directory"
    )

    verify_p = sub.add_parser(
        "verify",
        help="verify retained authority currentness, host seal, history, and fresh semantics",
    )
    verify_p.add_argument("output_dir")

    args = parser.parse_args(argv)
    try:
        if args.command == "compile":
            source = load_candidate_json(args.input, "input")
            authority = load_candidate_json(args.authority, "upstream_authority")
            value = compile_current(source, authority)
            publish_current(value, args.output_dir)
            print(
                json.dumps(
                    {
                        "authority_revision": value.host_seal["authority_revision"],
                        "authority_sha256": value.host_seal["authority_sha256"],
                        "host_seal_sha256": value.host_seal["hmac_sha256"],
                        "output_dir": args.output_dir,
                        "receipt_sha256": value.compiled.receipt["receipt_sha256"],
                        "selected_opportunity_ids": value.compiled.result[
                            "selected_opportunity_ids"
                        ],
                        "selected_priority_units": value.compiled.result[
                            "selected_priority_units"
                        ],
                    },
                    sort_keys=True,
                )
            )
            return 0

        print(json.dumps(verify_current_directory(args.output_dir), sort_keys=True))
        return 0
    except (PortfolioError, OSError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
