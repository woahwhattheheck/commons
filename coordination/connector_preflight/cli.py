"""CLI for connector capability preflight receipts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import PreflightError, compile_current, read_json_file, verify_current, verify_integrity, write_json_exclusive


def _emit_error(message: str) -> None:
    print(json.dumps({"ok": False, "error": message}, sort_keys=True), file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="connector-preflight")
    sub = parser.add_subparsers(dest="command", required=True)

    compile_parser = sub.add_parser("compile", help="compile a current preflight bundle")
    compile_parser.add_argument("input", type=Path)
    compile_parser.add_argument("output", type=Path)

    verify_parser = sub.add_parser("verify", help="verify exact retained bundle integrity")
    verify_parser.add_argument("input", type=Path)
    verify_parser.add_argument("bundle", type=Path)

    current_parser = sub.add_parser("verify-current", help="verify retained integrity and current decision semantics")
    current_parser.add_argument("input", type=Path)
    current_parser.add_argument("bundle", type=Path)

    args = parser.parse_args(argv)
    try:
        raw = read_json_file(args.input)
        if args.command == "compile":
            bundle = compile_current(raw)
            write_json_exclusive(args.output, bundle)
            print(json.dumps({"ok": True, "state": bundle["packet"]["overall_state"], "output": str(args.output)}, sort_keys=True))
            return 0
        bundle = read_json_file(args.bundle)
        if args.command == "verify":
            valid = verify_integrity(raw, bundle)
            print(json.dumps({"ok": valid, "integrity_valid": valid}, sort_keys=True))
            return 0 if valid else 3
        result = verify_current(raw, bundle)
        print(json.dumps({"ok": result["current_valid"], **result}, sort_keys=True))
        return 0 if result["current_valid"] else 3
    except PreflightError as exc:
        _emit_error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
