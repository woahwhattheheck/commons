from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

from .ledger import LedgerError, MAX_JSON_BYTES, canonical_bytes, compile_current, loads_strict, render_markdown, verify_current


def _read_bounded_regular(path: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise LedgerError(f"cannot open input: {exc.strerror}") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise LedgerError("input must be a regular file")
        if before.st_size > MAX_JSON_BYTES:
            raise LedgerError("input exceeds size limit")
        chunks: list[bytes] = []
        remaining = MAX_JSON_BYTES + 1
        while remaining > 0:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_JSON_BYTES:
            raise LedgerError("input exceeds size limit")
        after = os.fstat(fd)
        fingerprint_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_mode)
        fingerprint_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_mode)
        if fingerprint_before != fingerprint_after or len(raw) != after.st_size:
            raise LedgerError("input generation changed during read")
        return raw
    finally:
        os.close(fd)


def _write_exclusive(path: str, data: bytes) -> None:
    parent = os.path.dirname(os.path.abspath(path)) or "."
    if not os.path.isdir(parent):
        raise LedgerError("output parent must exist")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise LedgerError(f"cannot create output: {exc.strerror}") from exc
    ok = False
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise LedgerError("short write")
            view = view[written:]
        os.fsync(fd)
        ok = True
    finally:
        os.close(fd)
        if not ok:
            try:
                os.unlink(path)
            except OSError:
                pass


def _load_packet(path: str):
    return loads_strict(_read_bounded_regular(path))


def _load_report(path: str):
    return loads_strict(_read_bounded_regular(path))


def cmd_compile(args: argparse.Namespace) -> int:
    packet = _load_packet(args.input)
    report = compile_current(packet)
    markdown = render_markdown(report).encode("utf-8")
    if report["markdown_sha256"] != __import__("hashlib").sha256(markdown).hexdigest():
        raise LedgerError("internal markdown digest mismatch")
    _write_exclusive(args.json_output, canonical_bytes(report) + b"\n")
    try:
        _write_exclusive(args.markdown_output, markdown)
    except Exception:
        try:
            os.unlink(args.json_output)
        except OSError:
            pass
        raise
    print(report["receipt_sha256"])
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    packet = _load_packet(args.input)
    report = _load_report(args.report)
    if not verify_current(packet, report):
        print("CURRENT_VERIFICATION_FAILED", file=sys.stderr)
        return 2
    print("CURRENT_VERIFIED")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline Partner Conversion Ledger")
    sub = parser.add_subparsers(dest="command", required=True)
    compile_p = sub.add_parser("compile")
    compile_p.add_argument("input")
    compile_p.add_argument("json_output")
    compile_p.add_argument("markdown_output")
    compile_p.set_defaults(func=cmd_compile)
    verify_p = sub.add_parser("verify")
    verify_p.add_argument("input")
    verify_p.add_argument("report")
    verify_p.set_defaults(func=cmd_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except LedgerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
