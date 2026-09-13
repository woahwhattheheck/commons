#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from .control import (
        ControlError,
        canonical_bytes,
        compile_bytes,
        parse_receipt_bytes,
        read_bounded_regular,
        render_markdown,
        verify_bytes,
        write_exclusive_regular,
    )
except ImportError:  # direct-script execution
    from control import (  # type: ignore
        ControlError,
        canonical_bytes,
        compile_bytes,
        parse_receipt_bytes,
        read_bounded_regular,
        render_markdown,
        verify_bytes,
        write_exclusive_regular,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evidence-bound teaming conversion owner-review compiler")
    sub = parser.add_subparsers(dest="command", required=True)

    compile_p = sub.add_parser("compile", help="compile exact JSON inputs into owner-review outputs")
    compile_p.add_argument("--input", required=True)
    compile_p.add_argument("--policy", required=True)
    compile_p.add_argument("--json-output", required=True)
    compile_p.add_argument("--markdown-output", required=True)

    verify_p = sub.add_parser("verify", help="recompile and verify an exact-byte receipt")
    verify_p.add_argument("--input", required=True)
    verify_p.add_argument("--policy", required=True)
    verify_p.add_argument("--receipt", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        input_bytes = read_bounded_regular(args.input)
        policy_bytes = read_bounded_regular(args.policy)
        if args.command == "compile":
            if Path(args.json_output).resolve() == Path(args.markdown_output).resolve():
                raise ControlError("JSON and Markdown outputs must be distinct paths")
            now = datetime.now(timezone.utc).replace(microsecond=0)
            receipt = compile_bytes(input_bytes, policy_bytes, as_of=now)
            json_bytes = canonical_bytes(receipt)
            markdown_bytes = render_markdown(receipt).encode("utf-8")
            # Publication is create-exclusive. A pre-existing target aborts rather than overwriting evidence.
            write_exclusive_regular(args.json_output, json_bytes)
            try:
                write_exclusive_regular(args.markdown_output, markdown_bytes)
            except Exception:
                Path(args.json_output).unlink(missing_ok=True)
                raise
            print(f"{receipt['payload']['disposition']} {receipt['receipt_sha256']}")
            return 0
        if args.command == "verify":
            receipt_bytes = read_bounded_regular(args.receipt)
            receipt = verify_bytes(input_bytes, policy_bytes, receipt_bytes)
            print(f"VERIFIED {receipt['payload']['disposition']} {receipt['receipt_sha256']}")
            return 0
        raise ControlError("unknown command")
    except (ControlError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
