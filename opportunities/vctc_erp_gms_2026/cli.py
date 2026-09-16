from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

from .engine import build_source_authority, compile_assessment, verify_assessment, ValidationError


def _no_dupe_object(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError(f"duplicate JSON key: {k}")
        obj[k] = v
    return obj


def load_json(path: str):
    p = Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size > 10_000_000:
        raise ValueError("input must be bounded regular non-symlink file")
    return json.loads(p.read_text("utf-8"), object_pairs_hook=_no_dupe_object, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"nonfinite {x}")))


def key_from_env():
    text = os.environ.get("VCTC_SOURCE_AUTHORITY_KEY_HEX", "")
    try:
        key = bytes.fromhex(text)
    except ValueError as exc:
        raise ValueError("VCTC_SOURCE_AUTHORITY_KEY_HEX must be hex") from exc
    if len(key) < 32:
        raise ValueError("VCTC_SOURCE_AUTHORITY_KEY_HEX must decode to >=32 bytes")
    return key


def write_exclusive(path: str, value):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        data = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("sign-sources")
    p.add_argument("sources")
    p.add_argument("output")
    p.add_argument("--key-id", required=True)
    p.add_argument("--issued-at")
    p = sub.add_parser("compile")
    p.add_argument("packet")
    p.add_argument("authority")
    p.add_argument("output")
    p.add_argument("--key-id", required=True)
    p.add_argument("--as-of")
    p = sub.add_parser("verify")
    p.add_argument("packet")
    p.add_argument("authority")
    p.add_argument("assessment")
    p.add_argument("--key-id", required=True)
    args = ap.parse_args(argv)
    key = key_from_env()
    try:
        if args.cmd == "sign-sources":
            rows = load_json(args.sources)
            issued = args.issued_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
            write_exclusive(args.output, build_source_authority(rows, key_id=args.key_id, key=key, issued_at=issued))
        elif args.cmd == "compile":
            packet = load_json(args.packet)
            authority = load_json(args.authority)
            as_of = args.as_of or datetime.now(timezone.utc).isoformat(timespec="seconds")
            write_exclusive(args.output, compile_assessment(packet, authority, key=key, expected_key_id=args.key_id, as_of=as_of))
        else:
            ok = verify_assessment(load_json(args.packet), load_json(args.authority), load_json(args.assessment), key=key, expected_key_id=args.key_id)
            print("VERIFIED" if ok else "FAILED")
    except (ValidationError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
