from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import FilingQualityError, compile_report, load_policy, loads_strict, verify_bundle, write_bundle


def _read(path: str) -> bytes:
    return Path(path).read_bytes()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline SEC Company Facts filing-quality desk")
    sub = parser.add_subparsers(dest="command", required=True)

    compile_p = sub.add_parser("compile", help="compile retained Company Facts + analyst policy")
    compile_p.add_argument("source")
    compile_p.add_argument("policy")
    compile_p.add_argument("output_dir")

    verify_p = sub.add_parser("verify", help="verify byte-bound output bundle")
    verify_p.add_argument("source")
    verify_p.add_argument("policy")
    verify_p.add_argument("output_dir")

    args = parser.parse_args(argv)
    try:
        source = _read(args.source)
        policy = _read(args.policy)
        if args.command == "compile":
            report = compile_report(source, policy)
            written = write_bundle(args.output_dir, report)
            print(json.dumps({"ok": True, "receipt_sha256": report["receipt_sha256"], "files": written}, sort_keys=True))
            return 0
        ok = verify_bundle(args.output_dir, source, policy)
        print(json.dumps({"ok": ok}, sort_keys=True))
        return 0 if ok else 2
    except (OSError, FilingQualityError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
