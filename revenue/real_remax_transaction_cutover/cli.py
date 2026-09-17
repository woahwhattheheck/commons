from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path
from typing import Any

from .engine import compile_cutover, verify_report
from .schema import CutoverError, canonical_bytes

MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 200_000


class DuplicateKeyError(ValueError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _nonfinite(token: str) -> None:
    raise ValueError(f"non-finite number is forbidden: {token}")


def _check_json_shape(value: Any) -> None:
    stack: list[tuple[Any, int]] = [(value, 0)]
    nodes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise CutoverError(f"JSON exceeds {MAX_JSON_NODES} nodes")
        if depth > MAX_JSON_DEPTH:
            raise CutoverError(f"JSON exceeds maximum depth {MAX_JSON_DEPTH}")
        if type(current) is dict:
            stack.extend((child, depth + 1) for child in current.values())
        elif type(current) is list:
            stack.extend((child, depth + 1) for child in current)


def load_strict_json(path: str) -> Any:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise CutoverError(f"cannot open input {path}: {exc}") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise CutoverError(f"input is not a regular file: {path}")
        if before.st_size > MAX_INPUT_BYTES:
            raise CutoverError(f"input exceeds {MAX_INPUT_BYTES} bytes: {path}")
        data = bytearray()
        while True:
            chunk = os.read(fd, min(1 << 20, MAX_INPUT_BYTES + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > MAX_INPUT_BYTES:
                raise CutoverError(f"input exceeds {MAX_INPUT_BYTES} bytes: {path}")
        after = os.fstat(fd)
        fingerprint_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_mode)
        fingerprint_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_mode)
        if fingerprint_before != fingerprint_after:
            raise CutoverError(f"input changed while being read: {path}")
    finally:
        os.close(fd)
    try:
        text = bytes(data).decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except (UnicodeDecodeError, json.JSONDecodeError, DuplicateKeyError, ValueError, RecursionError) as exc:
        raise CutoverError(f"invalid strict JSON in {path}: {exc}") from exc
    _check_json_shape(value)
    if canonical_bytes(value) != bytes(data):
        raise CutoverError(f"input is not canonical JSON: {path}")
    return value


def write_exclusive(path: str, value: Any) -> None:
    data = canonical_bytes(value)
    parent = Path(path).parent
    parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise CutoverError(f"refusing non-exclusive output {path}: {exc}") from exc
    try:
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise CutoverError(f"short write for {path}")
            view = view[n:]
        os.fsync(fd)
    except Exception:
        # Never pathname-unlink on rollback: another actor could have swapped the
        # visible name after this descriptor was reserved. Fail visibly by
        # truncating only the inode we still own through the retained fd.
        try:
            os.ftruncate(fd, 0)
            os.fsync(fd)
        except OSError:
            pass
        finally:
            os.close(fd)
        raise
    else:
        os.close(fd)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compile or verify Real/REMAX cutover evidence")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("compile", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--source", required=True)
        p.add_argument("--target", required=True)
        p.add_argument("--identity-map", required=True)
        p.add_argument("--policy", required=True)
        if name == "compile":
            p.add_argument("--output", required=True)
        else:
            p.add_argument("--report", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        source = load_strict_json(args.source)
        target = load_strict_json(args.target)
        identity_map = load_strict_json(args.identity_map)
        policy = load_strict_json(args.policy)
        if args.command == "compile":
            report = compile_cutover(source, target, identity_map, policy)
            write_exclusive(args.output, report)
            print(report["decision"])
            return 0 if report["decision"] == "PARITY" else 2
        report = load_strict_json(args.report)
        ok = verify_report(source, target, identity_map, policy, report)
        print("VERIFIED" if ok else "INVALID")
        return 0 if ok else 3
    except CutoverError as exc:
        print(f"ERROR: {exc}")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
