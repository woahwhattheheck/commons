from __future__ import annotations

import argparse
import os
import stat
from pathlib import Path
from typing import Any

from .core import MAX_BYTES, ReconcileError, canonical_bytes, strict_json_loads
from .engine import compile_bundle, verify_bundle


def read_bounded_regular(path: Path) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        st1 = os.fstat(fd)
        if not stat.S_ISREG(st1.st_mode):
            raise ReconcileError("input must be a regular file")
        if st1.st_size > MAX_BYTES:
            raise ReconcileError("input exceeds byte limit")
        data = b""
        while len(data) <= MAX_BYTES:
            chunk = os.read(fd, min(65536, MAX_BYTES + 1 - len(data)))
            if not chunk:
                break
            data += chunk
        if len(data) > MAX_BYTES:
            raise ReconcileError("input exceeds byte limit")
        st2 = os.fstat(fd)
        fingerprint1 = (st1.st_dev, st1.st_ino, st1.st_size, st1.st_mtime_ns, st1.st_ctime_ns, st1.st_mode)
        fingerprint2 = (st2.st_dev, st2.st_ino, st2.st_size, st2.st_mtime_ns, st2.st_ctime_ns, st2.st_mode)
        if fingerprint1 != fingerprint2:
            raise ReconcileError("input changed during read")
        return data
    finally:
        os.close(fd)


def load_path(path: Path) -> Any:
    raw = read_bounded_regular(path)
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise ReconcileError("input must be UTF-8") from exc
    return strict_json_loads(text)


def publish_exclusive(path: Path, value: Any) -> None:
    data = canonical_bytes(value) + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        sent = 0
        while sent < len(data):
            count = os.write(fd, data[sent:])
            if count <= 0:
                raise ReconcileError("short output write")
            sent += count
        os.fsync(fd)
    except Exception:
        try:
            os.close(fd)
        finally:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise
    else:
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Accepted-work-to-cash retained-evidence reconciler")
    sub = parser.add_subparsers(dest="command", required=True)
    compile_parser = sub.add_parser("compile")
    compile_parser.add_argument("input")
    compile_parser.add_argument("output")
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("bundle")
    args = parser.parse_args(argv)
    try:
        if args.command == "compile":
            source = load_path(Path(args.input))
            bundle = compile_bundle(source)
            publish_exclusive(Path(args.output), bundle)
            print(bundle["receipt_sha256"])
            return 0
        bundle = load_path(Path(args.bundle))
        verify_bundle(bundle)
        print("VALID")
        return 0
    except (OSError, ReconcileError) as exc:
        print(f"ERROR: {exc}", file=os.sys.stderr)
        return 2
