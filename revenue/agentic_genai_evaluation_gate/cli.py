"""Command-line interface for the agentic GenAI evaluation evidence gate."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .gate import EvidenceError, compile_receipt, render_markdown, verify_receipt

MAX_INPUT_BYTES = 8 * 1024 * 1024


def _stat_token(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read_fd_bounded(fd: int, *, path: Path) -> bytes:
    data = bytearray()
    while len(data) <= MAX_INPUT_BYTES:
        chunk = os.read(fd, min(65536, MAX_INPUT_BYTES + 1 - len(data)))
        if not chunk:
            break
        data.extend(chunk)
    if len(data) > MAX_INPUT_BYTES:
        raise EvidenceError(f"{path}: input exceeds {MAX_INPUT_BYTES} bytes")
    return bytes(data)


def _read_bytes_bounded(path: Path) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if nofollow:
        flags |= nofollow
    path_before = path.lstat() if not nofollow else None
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise EvidenceError(f"{path}: expected regular file")
        if path_before is not None and (path_before.st_dev, path_before.st_ino) != (before.st_dev, before.st_ino):
            raise EvidenceError(f"{path}: file identity changed during open")
        if before.st_size > MAX_INPUT_BYTES:
            raise EvidenceError(f"{path}: input exceeds {MAX_INPUT_BYTES} bytes")

        first = _read_fd_bounded(fd, path=path)
        middle = os.fstat(fd)
        if _stat_token(middle) != _stat_token(before) or len(first) != before.st_size:
            raise EvidenceError(f"{path}: file generation changed during read")

        os.lseek(fd, 0, os.SEEK_SET)
        second = _read_fd_bounded(fd, path=path)
        after = os.fstat(fd)
        if _stat_token(after) != _stat_token(before) or second != first:
            raise EvidenceError(f"{path}: file generation changed during read")
        return first
    finally:
        os.close(fd)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise EvidenceError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _read_json(path: Path) -> Any:
    raw = _read_bytes_bounded(path)
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise EvidenceError(f"{path}: invalid UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except EvidenceError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise EvidenceError(f"{path}: invalid JSON") from exc


def _write_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    fd = os.open(path, flags, 0o600)
    try:
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise OSError("short write")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _cmd_compile(args: argparse.Namespace) -> int:
    packet = _read_json(Path(args.packet))
    receipt = compile_receipt(packet, evaluated_at=_now())
    json_bytes = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8")
    md_bytes = render_markdown(receipt).encode("utf-8")
    _write_exclusive(Path(args.receipt_out), json_bytes)
    if args.markdown_out:
        _write_exclusive(Path(args.markdown_out), md_bytes)
    print(receipt["decision"])
    print(receipt["receipt_sha256"])
    return 0 if receipt["decision"] == "RELEASE_CANDIDATE" else 2


def _cmd_verify(args: argparse.Namespace) -> int:
    packet = _read_json(Path(args.packet))
    receipt = _read_json(Path(args.receipt))
    result = verify_receipt(packet, receipt, verified_at=_now())
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result.get("valid") else 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    compile_p = sub.add_parser("compile", help="compile evaluation evidence")
    compile_p.add_argument("packet")
    compile_p.add_argument("receipt_out")
    compile_p.add_argument("--markdown-out")
    compile_p.set_defaults(func=_cmd_compile)
    verify_p = sub.add_parser("verify", help="verify an existing receipt")
    verify_p.add_argument("packet")
    verify_p.add_argument("receipt")
    verify_p.set_defaults(func=_cmd_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return int(args.func(args))
    except (EvidenceError, OSError) as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
