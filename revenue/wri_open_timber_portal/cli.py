from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import sys

from .engine import ContractError, compile_proposal, load_json_strict, render_markdown, verify_report

MAX_BYTES = 2_000_000


def read_regular(path: Path) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ContractError(f"not a regular file: {path}")
        if before.st_size > MAX_BYTES:
            raise ContractError(f"file too large: {path}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_BYTES:
                raise ContractError(f"file too large: {path}")
            chunks.append(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise ContractError(f"file changed during read: {path}")
        return b"".join(chunks)
    finally:
        os.close(fd)


def now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wri-open-timber-proposal")
    sub = parser.add_subparsers(dest="cmd", required=True)
    compile_cmd = sub.add_parser("compile")
    compile_cmd.add_argument("packet", type=Path)
    compile_cmd.add_argument("--format", choices=("json", "markdown"), default="json")
    verify_cmd = sub.add_parser("verify")
    verify_cmd.add_argument("packet", type=Path)
    verify_cmd.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    try:
        packet = load_json_strict(read_regular(args.packet))
        if args.cmd == "compile":
            report = compile_proposal(packet, as_of=now())
            if args.format == "markdown":
                print(render_markdown(report), end="")
            else:
                print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
            return 0 if report["technical_readiness"] == "TECHNICALLY_READY" else 2
        report = load_json_strict(read_regular(args.report))
        result = verify_report(packet, report, current_as_of=now())
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 0 if result["verdict"] == "CURRENT_TECHNICAL_CARRIER_VERIFIED" else 3
    except (ContractError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
