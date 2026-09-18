from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from outreach_qualification_firewall import (  # noqa: E402
    MAX_INPUT_BYTES,
    FirewallError,
    canonical_json,
    compile_current,
    compile_historical,
    strict_json_loads,
    verify_receipt,
)


def _read_regular_text(path_text: str) -> str:
    path = Path(path_text)
    st = path.lstat()
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise FirewallError("input must be a regular non-symlink file")
    if st.st_size > MAX_INPUT_BYTES:
        raise FirewallError("input exceeds size ceiling")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_INPUT_BYTES:
                raise FirewallError("input exceeds size ceiling")
            chunks.append(chunk)
        after = os.fstat(fd)
        before_fp = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_mode)
        after_fp = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_mode)
        if before_fp != after_fp:
            raise FirewallError("input generation changed during read")
    finally:
        os.close(fd)
    try:
        return b"".join(chunks).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FirewallError("input must be UTF-8") from exc


def _load(path: str):
    return strict_json_loads(_read_regular_text(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="outreach-qualification-firewall")
    sub = parser.add_subparsers(dest="command", required=True)
    cur = sub.add_parser("current", help="evaluate against process UTC; only mode that can authorize send")
    cur.add_argument("packet")
    hist = sub.add_parser("historical", help="owner-review only; never authorizes send")
    hist.add_argument("packet")
    hist.add_argument("--as-of", required=True)
    verify = sub.add_parser("verify-receipt")
    verify.add_argument("packet")
    verify.add_argument("decision")
    args = parser.parse_args(argv)
    try:
        if args.command == "current":
            out = compile_current(_load(args.packet))
        elif args.command == "historical":
            out = compile_historical(_load(args.packet), as_of=args.as_of)
        else:
            packet = _load(args.packet)
            decision = _load(args.decision)
            verify_receipt(packet, decision)
            out = {"verified": True, "receipt_sha256": decision["receipt_sha256"]}
        sys.stdout.buffer.write(canonical_json(out) + b"\n")
        return 0
    except (FirewallError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
