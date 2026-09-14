from __future__ import annotations

import argparse
import os
import stat
import sys
from datetime import datetime, timezone

from .core import (
    ValidationError,
    canonical_json_bytes,
    compile_cockpit,
    load_json_bytes,
    render_markdown,
    verify_cockpit,
)

MAX_INPUT_BYTES = 2_000_000


def _read_regular(path: str | os.PathLike[str], limit: int = MAX_INPUT_BYTES) -> bytes:
    path = os.fspath(path)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValidationError(f"cannot open regular input {path}: {exc}") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValidationError(f"input is not a regular file: {path}")
        if before.st_size > limit:
            raise ValidationError(f"input exceeds {limit} bytes: {path}")
        chunks = []
        total = 0
        while True:
            chunk = os.read(fd, min(65536, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > limit:
                raise ValidationError(f"input exceeds {limit} bytes: {path}")
        after = os.fstat(fd)
        fingerprint_before = (before.st_dev, before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        fingerprint_after = (after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        if fingerprint_before != fingerprint_after:
            raise ValidationError(f"input changed while reading: {path}")
        raw = b"".join(chunks)
        if len(raw) != after.st_size:
            raise ValidationError(f"input size changed while reading: {path}")
        return raw
    finally:
        os.close(fd)


def _preflight_absent(path: str | os.PathLike[str]) -> None:
    path = os.fspath(path)
    parent = os.path.dirname(path) or "."
    try:
        st = os.stat(parent, follow_symlinks=False)
    except OSError as exc:
        raise ValidationError(f"output parent unavailable: {parent}") from exc
    if not stat.S_ISDIR(st.st_mode):
        raise ValidationError(f"output parent is not a directory: {parent}")
    if os.path.lexists(path):
        raise ValidationError(f"output already exists: {path}")


def _write_exclusive(path: str | os.PathLike[str], data: bytes) -> None:
    path = os.fspath(path)
    _preflight_absent(path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = None
    identity = None
    success = False
    try:
        fd = os.open(path, flags, 0o600)
        created = os.fstat(fd)
        if not stat.S_ISREG(created.st_mode):
            raise ValidationError(f"output is not a regular file: {path}")
        identity = (created.st_dev, created.st_ino)
        view = memoryview(data)
        offset = 0
        while offset < len(view):
            written = os.write(fd, view[offset:])
            if written <= 0:
                raise ValidationError(f"short write: {path}")
            offset += written
        os.fsync(fd)
        after = os.fstat(fd)
        if after.st_size != len(data):
            raise ValidationError(f"output size mismatch: {path}")
        success = True
    except FileExistsError as exc:
        raise ValidationError(f"output already exists: {path}") from exc
    except OSError as exc:
        raise ValidationError(f"output write failed: {path}: {exc}") from exc
    finally:
        if fd is not None:
            os.close(fd)
        if not success and identity is not None:
            try:
                visible = os.stat(path, follow_symlinks=False)
                if (visible.st_dev, visible.st_ino) == identity:
                    os.unlink(path)
            except OSError:
                pass


def _load(path: str) -> object:
    return load_json_bytes(_read_regular(path))


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def cmd_compile(args: argparse.Namespace) -> int:
    packet = _load(args.input)
    policy = _load(args.policy)
    out = compile_cockpit(packet, policy, as_of=_now())
    json_bytes = canonical_json_bytes(out) + b"\n"
    md_bytes = render_markdown(out).encode("utf-8")
    outputs = [args.output]
    if args.markdown:
        outputs.append(args.markdown)
    for path in outputs:
        _preflight_absent(path)
    _write_exclusive(args.output, json_bytes)
    if args.markdown:
        _write_exclusive(args.markdown, md_bytes)
    print(out["receipt_sha256"])
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    packet = _load(args.input)
    policy = _load(args.policy)
    compiled = _load(args.output)
    ok = verify_cockpit(packet, policy, compiled, current_as_of=_now())
    if ok:
        print("VERIFIED")
        return 0
    print("NOT_VERIFIED", file=sys.stderr)
    return 2


def cmd_render(args: argparse.Namespace) -> int:
    packet = _load(args.input)
    policy = _load(args.policy)
    compiled = _load(args.output)
    if not verify_cockpit(packet, policy, compiled, current_as_of=_now()):
        raise ValidationError("compiled output is not currently verified")
    _preflight_absent(args.markdown)
    _write_exclusive(args.markdown, render_markdown(compiled).encode("utf-8"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline cross-bid owner-action cockpit")
    sub = parser.add_subparsers(dest="command", required=True)

    compile_p = sub.add_parser("compile", help="compile normalized blocker evidence")
    compile_p.add_argument("--input", required=True)
    compile_p.add_argument("--policy", required=True)
    compile_p.add_argument("--output", required=True)
    compile_p.add_argument("--markdown")
    compile_p.set_defaults(func=cmd_compile)

    verify_p = sub.add_parser("verify", help="verify exact historical bytes and current semantics")
    verify_p.add_argument("--input", required=True)
    verify_p.add_argument("--policy", required=True)
    verify_p.add_argument("--output", required=True)
    verify_p.set_defaults(func=cmd_verify)

    render_p = sub.add_parser("render", help="render only after current verification")
    render_p.add_argument("--input", required=True)
    render_p.add_argument("--policy", required=True)
    render_p.add_argument("--output", required=True)
    render_p.add_argument("--markdown", required=True)
    render_p.set_defaults(func=cmd_render)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return int(args.func(args))
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
