from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path

from .qualification import ContractError, canonical_bytes, compile_current, verify_report

MAX_INPUT = 1_000_000


def _read_regular(path: str) -> bytes:
    p = Path(path)
    try:
        st = p.lstat()
    except OSError as exc:
        raise ContractError(f"cannot stat input: {path}") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise ContractError(f"input must be regular non-symlink file: {path}")
    if st.st_size > MAX_INPUT:
        raise ContractError(f"input too large: {path}")
    data = p.read_bytes()
    if len(data) != st.st_size:
        raise ContractError(f"input changed while reading: {path}")
    return data


def _write_exclusive(path: str, value: object) -> None:
    raw = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8") + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise


def _optional(path: str | None) -> bytes | None:
    return None if path is None else _read_regular(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TXST AI advising qualification carrier")
    sub = parser.add_subparsers(dest="command", required=True)

    compile_p = sub.add_parser("compile", help="compile current owner-review qualification")
    compile_p.add_argument("--candidate", required=True)
    compile_p.add_argument("--official")
    compile_p.add_argument("--owner-evidence")
    compile_p.add_argument("--partner-evidence")
    compile_p.add_argument("--out", required=True)

    verify_p = sub.add_parser("verify", help="verify receipt integrity and current semantics")
    verify_p.add_argument("--candidate", required=True)
    verify_p.add_argument("--report", required=True)
    verify_p.add_argument("--official")
    verify_p.add_argument("--owner-evidence")
    verify_p.add_argument("--partner-evidence")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        candidate = _read_regular(args.candidate)
        official = _optional(args.official)
        owner = _optional(args.owner_evidence)
        partner = _optional(args.partner_evidence)
        if args.command == "compile":
            report = compile_current(candidate, official_raw=official, owner_raw=owner, partner_raw=partner)
            _write_exclusive(args.out, report)
            print(json.dumps({"state": report["state"], "receipt_sha256": report["receipt_sha256"]}, sort_keys=True))
            return 0
        result = verify_report(candidate, _read_regular(args.report), official_raw=official, owner_raw=owner, partner_raw=partner)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["integrity_valid"] and result["current_semantics_match"] else 2
    except (ContractError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
