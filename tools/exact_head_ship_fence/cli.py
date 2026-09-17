"""CLI for exact-head ship fence."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat
import sys
from typing import Any

from .fence import (
    EvidenceError,
    MAX_JSON_BYTES,
    canonical_json_bytes,
    compile_current,
    parse_json_bytes,
    render_markdown,
    verify_current,
)


def _read_regular(path: Path, max_bytes: int = MAX_JSON_BYTES) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise EvidenceError(f"not a regular file: {path}")
        if st.st_size > max_bytes:
            raise EvidenceError(f"file too large: {path}")
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            part = os.read(fd, min(65536, remaining))
            if not part:
                break
            chunks.append(part)
            remaining -= len(part)
        data = b"".join(chunks)
        if len(data) > max_bytes:
            raise EvidenceError(f"file too large: {path}")
        st2 = os.fstat(fd)
        if (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns) != (
            st2.st_dev,
            st2.st_ino,
            st2.st_size,
            st2.st_mtime_ns,
        ):
            raise EvidenceError(f"file changed while reading: {path}")
        return data
    finally:
        os.close(fd)


def _write_exclusive(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_bundle(output_dir: Path, report: dict[str, Any]) -> None:
    os.mkdir(output_dir, 0o700)
    created: list[Path] = []
    try:
        json_path = output_dir / "report.json"
        md_path = output_dir / "report.md"
        _write_exclusive(json_path, canonical_json_bytes(report) + b"\n")
        created.append(json_path)
        _write_exclusive(md_path, render_markdown(report).encode("utf-8"))
        created.append(md_path)
    except BaseException:
        for path in reversed(created):
            try:
                path.unlink()
            except OSError:
                pass
        try:
            output_dir.rmdir()
        except OSError:
            pass
        raise


def _compile(args: argparse.Namespace) -> int:
    snapshot = parse_json_bytes(_read_regular(Path(args.snapshot)))
    report = compile_current(snapshot)
    _write_bundle(Path(args.output_dir), report)
    print(report["receipt_sha256"])
    return 0


def _verify(args: argparse.Namespace) -> int:
    snapshot = parse_json_bytes(_read_regular(Path(args.snapshot)))
    bundle = Path(args.output_dir)
    report = parse_json_bytes(_read_regular(bundle / "report.json"))
    md = _read_regular(bundle / "report.md").decode("utf-8", "strict")
    if not verify_current(report, snapshot):
        raise EvidenceError("semantic verification failed")
    if md != render_markdown(report):
        raise EvidenceError("Markdown projection mismatch")
    print("VERIFIED")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="exact-head-ship-fence")
    sub = parser.add_subparsers(dest="command", required=True)
    p_compile = sub.add_parser("compile", help="compile snapshot to create-exclusive bundle")
    p_compile.add_argument("snapshot")
    p_compile.add_argument("output_dir")
    p_compile.set_defaults(func=_compile)
    p_verify = sub.add_parser("verify", help="verify bundle against source snapshot")
    p_verify.add_argument("snapshot")
    p_verify.add_argument("output_dir")
    p_verify.set_defaults(func=_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return int(args.func(args))
    except (EvidenceError, OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
