from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path

from .router import ValidationError, canonical_bytes, compile_report, loads_strict, verify_report

MAX_INPUT_BYTES = 2_000_000


def _read_bounded(path: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValidationError(f"cannot open input: {exc}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValidationError("input must be a regular file")
        if info.st_size > MAX_INPUT_BYTES:
            raise ValidationError("input exceeds size limit")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_INPUT_BYTES:
                raise ValidationError("input exceeds size limit")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _write_exclusive(path: str, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise ValidationError(f"cannot create output: {exc}") from exc
    try:
        view = memoryview(data)
        written = 0
        while written < len(view):
            count = os.write(fd, view[written:])
            if count <= 0:
                raise ValidationError("short output write")
            written += count
        os.fsync(fd)
    except Exception:
        try:
            os.close(fd)
        finally:
            try:
                Path(path).unlink()
            except OSError:
                pass
        raise
    else:
        os.close(fd)


def _load(path: str):
    return loads_strict(_read_bounded(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic swarm channel coverage router")
    sub = parser.add_subparsers(dest="command", required=True)

    compile_p = sub.add_parser("compile", help="compile an inspection queue")
    compile_p.add_argument("--input", required=True)
    compile_p.add_argument("--as-of", required=True)
    compile_p.add_argument("--output", required=True)

    verify_p = sub.add_parser("verify", help="recompile and verify a report")
    verify_p.add_argument("--input", required=True)
    verify_p.add_argument("--report", required=True)
    verify_p.add_argument("--as-of", required=True)

    args = parser.parse_args(argv)
    try:
        packet = _load(args.input)
        if args.command == "compile":
            report = compile_report(packet, args.as_of)
            _write_exclusive(args.output, canonical_bytes(report) + b"\n")
            print(report["receipt_sha256"])
            return 0
        report = _load(args.report)
        if verify_report(packet, report, args.as_of):
            print("VERIFIED")
            return 0
        print("VERIFY_FAILED", file=sys.stderr)
        return 2
    except (ValidationError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
