"""Offline CLI for non-authorizing IMPO MTP 2055 owner-review packets."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

from .engine import canonical_json_bytes, compile_current, verify_current
from .schema import OpportunityInputError

MAX_JSON_BYTES = 2_000_000
MAX_MARKDOWN_BYTES = 8_000_000


class SafeFileError(RuntimeError):
    """Raised when a filesystem boundary cannot be proven safe."""


def _no_follow_flag() -> int:
    return getattr(os, "O_NOFOLLOW", 0)


def _generation_signature(metadata: os.stat_result) -> tuple[int, ...]:
    """Return metadata that changes when an ordinary file generation changes."""
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def read_regular_file(path: str | os.PathLike[str], *, max_bytes: int) -> bytes:
    raw_path = os.fspath(path)
    flags = os.O_RDONLY | _no_follow_flag()
    try:
        fd = os.open(raw_path, flags)
    except OSError as exc:
        raise SafeFileError(f"cannot open regular file {raw_path!r}: {exc}") from exc
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise SafeFileError(f"input is not a regular file: {raw_path!r}")
        if metadata.st_size > max_bytes:
            raise SafeFileError(
                f"input exceeds maximum size {max_bytes}: {raw_path!r}"
            )
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining > 0:
            chunk = os.read(fd, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) > max_bytes:
            raise SafeFileError(
                f"input exceeded maximum size while reading: {raw_path!r}"
            )
        if os.read(fd, 1):
            raise SafeFileError(f"input changed or exceeded bound while reading: {raw_path!r}")
        final_metadata = os.fstat(fd)
        if (
            _generation_signature(metadata) != _generation_signature(final_metadata)
            or len(payload) != metadata.st_size
        ):
            raise SafeFileError(f"input generation changed while reading: {raw_path!r}")

        try:
            visible_metadata = os.lstat(raw_path)
        except OSError as exc:
            raise SafeFileError(
                f"input path changed after opening {raw_path!r}: {exc}"
            ) from exc
        if (
            not stat.S_ISREG(visible_metadata.st_mode)
            or _generation_signature(visible_metadata)
            != _generation_signature(final_metadata)
        ):
            raise SafeFileError(f"input path generation changed while reading: {raw_path!r}")
        return payload
    finally:
        os.close(fd)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SafeFileError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise SafeFileError(f"non-finite JSON number is forbidden: {value}")


def load_json(path: str | os.PathLike[str]) -> Any:
    raw = read_regular_file(path, max_bytes=MAX_JSON_BYTES)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SafeFileError(f"JSON input is not UTF-8: {path!r}") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_nonfinite_constant,
        )
    except json.JSONDecodeError as exc:
        raise SafeFileError(f"invalid JSON in {path!r}: {exc}") from exc


def _open_output_directory(path: str | os.PathLike[str]) -> int:
    raw_path = os.fspath(path)
    try:
        return os.open(raw_path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | _no_follow_flag())
    except OSError as exc:
        raise SafeFileError(f"cannot open output directory {raw_path!r}: {exc}") from exc


def write_exclusive_at(directory_fd: int, name: str, payload: bytes) -> None:
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise SafeFileError(f"unsafe output filename: {name!r}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _no_follow_flag()
    try:
        fd = os.open(name, flags, 0o600, dir_fd=directory_fd)
    except OSError as exc:
        raise SafeFileError(f"cannot create output {name!r} exclusively: {exc}") from exc
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise SafeFileError(f"short write while creating {name!r}")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def compile_command(args: argparse.Namespace) -> int:
    value = load_json(args.input)
    receipt, markdown = compile_current(value)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(mode=0o700, parents=False, exist_ok=True)
    directory_fd = _open_output_directory(output_dir)
    try:
        write_exclusive_at(
            directory_fd,
            "receipt.json",
            canonical_json_bytes(receipt) + b"\n",
        )
        write_exclusive_at(directory_fd, "packet.md", markdown.encode("utf-8"))
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "submission_ready": receipt["submission_ready"],
                "evaluation_mode": receipt["evaluation_mode"],
                "receipt_sha256": receipt["receipt_sha256"],
                "output_dir": str(output_dir),
            },
            sort_keys=True,
        )
    )
    if args.require_submission_ready and not receipt["submission_ready"]:
        return 3
    return 0


def verify_command(args: argparse.Namespace) -> int:
    value = load_json(args.input)
    receipt = load_json(args.receipt)
    markdown_bytes = read_regular_file(args.markdown, max_bytes=MAX_MARKDOWN_BYTES)
    try:
        markdown = markdown_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SafeFileError("Markdown input is not UTF-8") from exc
    verify_current(value, receipt, markdown)
    print(
        json.dumps(
            {
                "verified": True,
                "status": receipt["status"],
                "submission_ready": receipt["submission_ready"],
                "evaluation_mode": receipt["evaluation_mode"],
                "receipt_sha256": receipt["receipt_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="impo-mtp2055-readiness",
        description=(
            "Compile and verify a current, non-authorizing owner-review packet for the "
            "Indianapolis MPO 2055 MTP RFP. This tool never performs external actions."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_parser = subparsers.add_parser("compile", help="compile a current owner-review packet")
    compile_parser.add_argument("input", help="path to strict candidate JSON")
    compile_parser.add_argument("--output-dir", required=True, help="new or empty output directory")
    compile_parser.add_argument(
        "--require-submission-ready",
        action="store_true",
        help=(
            "return exit code 3 unless submission_ready is true; this owner-review-only "
            "carrier deliberately never authenticates submission authority"
        ),
    )
    compile_parser.set_defaults(handler=compile_command)

    verify_parser = subparsers.add_parser("verify", help="verify exact bytes plus current process-time semantics")
    verify_parser.add_argument("input", help="path to strict candidate JSON")
    verify_parser.add_argument("receipt", help="path to compiled receipt JSON")
    verify_parser.add_argument("markdown", help="path to compiled Markdown")
    verify_parser.set_defaults(handler=verify_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (OpportunityInputError, SafeFileError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
