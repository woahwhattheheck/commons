"""Command-line interface for the agentic GenAI evaluation evidence gate."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .gate import (
    EvidenceError,
    compile_receipt,
    render_markdown,
    verify_receipt,
)

MAX_INPUT_BYTES = 8 * 1024 * 1024
_READ_CHUNK = 64 * 1024


def _stat_fingerprint(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _read_once(fd: int) -> bytes:
    data = bytearray()
    while len(data) <= MAX_INPUT_BYTES:
        chunk = os.read(
            fd,
            min(_READ_CHUNK, MAX_INPUT_BYTES + 1 - len(data)),
        )
        if not chunk:
            break
        data.extend(chunk)
    if len(data) > MAX_INPUT_BYTES:
        raise EvidenceError(f"input exceeds {MAX_INPUT_BYTES} bytes")
    return bytes(data)


def _read_bytes_bounded(path: Path) -> bytes:
    """Read one stable regular-file generation through a retained descriptor.

    Two descriptor reads plus immutable metadata checks prevent a successful
    parse from spanning a same-inode rewrite. ``st_ctime_ns`` is included so a
    writer cannot hide the mutation merely by restoring mtime.
    """
    flags = os.O_RDONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if nofollow:
        flags |= nofollow

    before_path = path.lstat() if not nofollow else None
    fd = os.open(path, flags)
    try:
        first = os.fstat(fd)
        if not stat.S_ISREG(first.st_mode):
            raise EvidenceError(f"{path}: expected regular file")
        if before_path is not None and (
            before_path.st_dev,
            before_path.st_ino,
        ) != (
            first.st_dev,
            first.st_ino,
        ):
            raise EvidenceError(f"{path}: file identity changed during open")
        if first.st_size > MAX_INPUT_BYTES:
            raise EvidenceError(f"{path}: input exceeds {MAX_INPUT_BYTES} bytes")

        first_bytes = _read_once(fd)
        middle = os.fstat(fd)
        if _stat_fingerprint(first) != _stat_fingerprint(middle):
            raise EvidenceError(f"{path}: file generation changed during read")
        if len(first_bytes) != first.st_size:
            raise EvidenceError(f"{path}: file length changed during read")

        os.lseek(fd, 0, os.SEEK_SET)
        second_bytes = _read_once(fd)
        last = os.fstat(fd)
        if _stat_fingerprint(first) != _stat_fingerprint(last):
            raise EvidenceError(f"{path}: file generation changed during reread")
        if first_bytes != second_bytes:
            raise EvidenceError(f"{path}: file bytes changed during retained reread")
        if len(second_bytes) != last.st_size:
            raise EvidenceError(f"{path}: file length changed during reread")

        try:
            visible = path.lstat()
        except OSError as exc:
            raise EvidenceError(
                f"{path}: visible input disappeared after retained read"
            ) from exc
        if not stat.S_ISREG(visible.st_mode):
            raise EvidenceError(
                f"{path}: visible input is no longer a regular file"
            )
        if (visible.st_dev, visible.st_ino) != (last.st_dev, last.st_ino):
            raise EvidenceError(
                f"{path}: visible input no longer names retained generation"
            )
        return second_bytes
    finally:
        os.close(fd)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _strict_json_loads(raw: bytes, *, source: str) -> Any:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise EvidenceError(f"{source}: invalid UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"invalid constant {token}")
            ),
        )
    except EvidenceError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise EvidenceError(f"{source}: invalid JSON") from exc


def _read_json(path: Path) -> Any:
    return _strict_json_loads(
        _read_bytes_bounded(path),
        source=os.fspath(path),
    )


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _require_descriptor_publication_support() -> tuple[int, int]:
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    nofollow_flag = getattr(os, "O_NOFOLLOW", 0)
    supports_dir_fd = os.open in os.supports_dir_fd and os.stat in os.supports_dir_fd
    if not directory_flag or not nofollow_flag or not supports_dir_fd:
        raise EvidenceError(
            "descriptor-relative no-follow publication is unsupported on this host"
        )
    return directory_flag, nofollow_flag


def _open_parent_no_follow(parent: Path) -> int:
    directory_flag, nofollow_flag = _require_descriptor_publication_support()
    flags = os.O_RDONLY | directory_flag | nofollow_flag
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY

    if parent.is_absolute():
        current = os.open(os.path.sep, flags)
        parts = parent.parts[1:]
    else:
        current = os.open(".", flags)
        parts = parent.parts

    try:
        for part in parts:
            if part in ("", "."):
                continue
            if part == "..":
                raise EvidenceError("output parent may not contain '..'")
            next_fd = os.open(part, flags, dir_fd=current)
            os.close(current)
            current = next_fd
        return current
    except BaseException:
        os.close(current)
        raise


@dataclass
class _PublicationTarget:
    path: Path
    parent_fd: int
    parent_identity: tuple[int, int]
    name: str
    data: bytes
    file_fd: int | None = None


def _target_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _assert_absent(parent_fd: int, name: str, path: Path) -> None:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise FileExistsError(f"{path}: output already exists")


def _drain_write(fd: int, data: bytes) -> None:
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:])
        if written <= 0:
            raise OSError("short write")
        offset += written


def _revalidate_target(target: _PublicationTarget, *, final: bool) -> None:
    if target.file_fd is None:
        raise EvidenceError(f"{target.path}: internal publication state error")
    created = os.fstat(target.file_fd)
    visible = os.stat(
        target.name,
        dir_fd=target.parent_fd,
        follow_symlinks=False,
    )
    if not stat.S_ISREG(created.st_mode) or not stat.S_ISREG(visible.st_mode):
        raise EvidenceError(f"{target.path}: published object is not regular")
    if (
        visible.st_dev,
        visible.st_ino,
        visible.st_size,
    ) != (
        created.st_dev,
        created.st_ino,
        created.st_size,
    ):
        raise EvidenceError(
            f"{target.path}: visible output no longer names created generation"
        )

    if final:
        reopened = _open_parent_no_follow(target.path.parent)
        try:
            reopened_info = os.fstat(reopened)
            if (
                reopened_info.st_dev,
                reopened_info.st_ino,
            ) != target.parent_identity:
                raise EvidenceError(
                    f"{target.path}: visible parent identity changed during publication"
                )
            final_visible = os.stat(
                target.name,
                dir_fd=reopened,
                follow_symlinks=False,
            )
            if (
                final_visible.st_dev,
                final_visible.st_ino,
                final_visible.st_size,
            ) != (
                created.st_dev,
                created.st_ino,
                created.st_size,
            ):
                raise EvidenceError(
                    f"{target.path}: final visible generation changed"
                )
            os.fsync(reopened)
        finally:
            os.close(reopened)


def _publish_exclusive(outputs: Sequence[tuple[Path, bytes]]) -> None:
    """Publish all requested outputs with global preflight and no rollback.

    All target names are proven absent before the first create. Files and parent
    directories are made durable, and final visible parent/name identities are
    checked against retained descriptors. On any failure, no pathname deletion
    is attempted: a concurrently installed foreign object is never removed.
    """
    if not outputs:
        raise EvidenceError("no publication outputs requested")

    keys: set[str] = set()
    targets: list[_PublicationTarget] = []
    try:
        for path, data in outputs:
            path = Path(path)
            if not path.name or path.name in {".", ".."}:
                raise EvidenceError(f"{path}: invalid output basename")
            key = _target_key(path)
            if key in keys:
                raise EvidenceError(f"{path}: duplicate output target")
            keys.add(key)

            parent_fd = _open_parent_no_follow(path.parent)
            parent_info = os.fstat(parent_fd)
            target = _PublicationTarget(
                path=path,
                parent_fd=parent_fd,
                parent_identity=(parent_info.st_dev, parent_info.st_ino),
                name=path.name,
                data=data,
            )
            targets.append(target)
            _assert_absent(parent_fd, path.name, path)

        _, nofollow_flag = _require_descriptor_publication_support()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow_flag
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY

        for target in targets:
            target.file_fd = os.open(
                target.name,
                flags,
                0o600,
                dir_fd=target.parent_fd,
            )
            _drain_write(target.file_fd, target.data)
            os.fsync(target.file_fd)
            _revalidate_target(target, final=False)

        for target in targets:
            os.fsync(target.parent_fd)

        for target in targets:
            _revalidate_target(target, final=True)
    finally:
        for target in targets:
            if target.file_fd is not None:
                os.close(target.file_fd)
            os.close(target.parent_fd)


def _cmd_compile(args: argparse.Namespace) -> int:
    packet = _read_json(Path(args.packet))
    receipt = compile_receipt(packet, evaluated_at=_now())
    receipt_bytes = (
        json.dumps(
            receipt,
            sort_keys=True,
            indent=2,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")

    outputs: list[tuple[Path, bytes]] = [
        (Path(args.receipt_out), receipt_bytes),
    ]
    if args.markdown_out:
        outputs.append(
            (
                Path(args.markdown_out),
                render_markdown(receipt).encode("utf-8"),
            )
        )
    _publish_exclusive(outputs)

    print(receipt["decision"])
    print(receipt["receipt_sha256"])
    return 0 if receipt["decision"] == "RELEASE_CANDIDATE" else 2


def _cmd_verify(args: argparse.Namespace) -> int:
    packet = _read_json(Path(args.packet))
    receipt = _read_json(Path(args.receipt))
    result = verify_receipt(packet, receipt, verified_at=_now())
    print(
        json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    )
    return 0 if result.get("valid") else 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    compile_parser = commands.add_parser(
        "compile",
        help="compile evaluation evidence",
    )
    compile_parser.add_argument("packet")
    compile_parser.add_argument("receipt_out")
    compile_parser.add_argument("--markdown-out")
    compile_parser.set_defaults(func=_cmd_compile)

    verify_parser = commands.add_parser(
        "verify",
        help="verify historical integrity and current fitness",
    )
    verify_parser.add_argument("packet")
    verify_parser.add_argument("receipt")
    verify_parser.set_defaults(func=_cmd_verify)
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
