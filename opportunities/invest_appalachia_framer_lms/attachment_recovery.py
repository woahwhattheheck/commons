from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import errno
import hashlib
import io
import json
import os
import re
import secrets
import stat
import urllib.request
import zipfile
from pathlib import PurePosixPath
from typing import Any

SOURCE_URL = "https://investappalachia.org/wp-content/uploads/2026/08/Zipped-RFP-Docs.zip"
MAX_ZIP_BYTES = 50 * 1024 * 1024
MAX_MEMBER_BYTES = 25 * 1024 * 1024
MAX_REGULAR_MEMBERS = 64
MAX_TOTAL_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
EXPECTED_LABELS = ("A", "B", "C", "D")
PROVENANCE_OFFICIAL_FETCH = "OFFICIAL_URL_FETCHED"
PROVENANCE_LOCAL = "LOCAL_BYTES_UNVERIFIED_PROVENANCE"
_RETRIEVED_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_ATTACHMENT = re.compile(r"(?:^|[^a-z0-9])attachment[\s._-]*([a-d])(?:[^a-z0-9]|$)", re.I)
_LEADING = re.compile(r"^([a-d])(?:[\s._-]+)", re.I)
_RENAME_NOREPLACE = 1


class AttachmentRecoveryError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_retrieved_at(value: str) -> str:
    if not isinstance(value, str) or not _RETRIEVED_AT.fullmatch(value):
        raise AttachmentRecoveryError("retrieved_at_utc must be exact UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise AttachmentRecoveryError("retrieved_at_utc must be a real UTC instant") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise AttachmentRecoveryError("retrieved_at_utc must be canonical UTC YYYY-MM-DDTHH:MM:SSZ")
    return value


def _observed_utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_name(name: str) -> str:
    if not isinstance(name, str) or not name or "\x00" in name:
        raise AttachmentRecoveryError("member name must be non-empty text without NUL")
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise AttachmentRecoveryError(f"unsafe ZIP member path: {name!r}")
    canonical = path.as_posix()
    if not canonical or canonical == ".":
        raise AttachmentRecoveryError(f"unsafe ZIP member path: {name!r}")
    return canonical


def _require_regular_member(info: zipfile.ZipInfo, name: str) -> None:
    if info.is_dir():
        return
    if info.create_system == 3:
        mode = info.external_attr >> 16
        file_type = stat.S_IFMT(mode)
        if file_type not in {0, stat.S_IFREG}:
            raise AttachmentRecoveryError(f"non-regular ZIP member is not allowed: {name}")


def _attachment_label(name: str) -> str | None:
    base = PurePosixPath(name).name
    stem = base.rsplit(".", 1)[0]
    match = _ATTACHMENT.search(stem) or _LEADING.match(stem)
    return match.group(1).upper() if match else None


def _analyze_zip_bytes(
    data: bytes,
    *,
    provenance_mode: str,
    source_url: str | None,
    retrieved_at_utc: str | None,
) -> dict[str, Any]:
    if not isinstance(data, (bytes, bytearray)):
        raise AttachmentRecoveryError("ZIP payload must be bytes")
    data = bytes(data)
    if not data:
        raise AttachmentRecoveryError("ZIP payload is empty")
    if len(data) > MAX_ZIP_BYTES:
        raise AttachmentRecoveryError("ZIP payload exceeds bounded size")

    if provenance_mode == PROVENANCE_LOCAL:
        if source_url is not None or retrieved_at_utc is not None:
            raise AttachmentRecoveryError("local-byte provenance cannot assert an official URL or retrieval time")
    elif provenance_mode == PROVENANCE_OFFICIAL_FETCH:
        if source_url != SOURCE_URL:
            raise AttachmentRecoveryError("official-fetch provenance must remain bound to the exact buyer ZIP URL")
        if retrieved_at_utc is None:
            raise AttachmentRecoveryError("official-fetch provenance requires an observed retrieval time")
        retrieved_at_utc = _validate_retrieved_at(retrieved_at_utc)
    else:
        raise AttachmentRecoveryError("unsupported provenance mode")

    members: list[dict[str, Any]] = []
    labels: dict[str, str] = {}
    unexpected: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
            regular_infos: list[tuple[zipfile.ZipInfo, str]] = []
            seen_names: set[str] = set()
            total_uncompressed = 0
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = _safe_name(info.filename)
                _require_regular_member(info, name)
                if name in seen_names:
                    raise AttachmentRecoveryError(f"duplicate ZIP member path: {name!r}")
                seen_names.add(name)
                if info.file_size < 0 or info.file_size > MAX_MEMBER_BYTES:
                    raise AttachmentRecoveryError(f"member exceeds bounded size: {name}")
                regular_infos.append((info, name))
                if len(regular_infos) > MAX_REGULAR_MEMBERS:
                    raise AttachmentRecoveryError("ZIP contains too many regular members")
                total_uncompressed += info.file_size
                if total_uncompressed > MAX_TOTAL_UNCOMPRESSED_BYTES:
                    raise AttachmentRecoveryError("ZIP cumulative uncompressed size exceeds bounded total")

            for info, name in regular_infos:
                payload = archive.read(info)
                if len(payload) != info.file_size:
                    raise AttachmentRecoveryError(f"member size mismatch: {name}")
                label = _attachment_label(name)
                members.append({
                    "name": name,
                    "attachment_label": label,
                    "compressed_size": info.compress_size,
                    "uncompressed_size": info.file_size,
                    "sha256": _sha256(payload),
                })
                if label is None:
                    unexpected.append(name)
                elif label in labels:
                    raise AttachmentRecoveryError(
                        f"duplicate attachment label {label}: {labels[label]!r} and {name!r}"
                    )
                else:
                    labels[label] = name
    except AttachmentRecoveryError:
        raise
    except (zipfile.BadZipFile, RuntimeError, OSError, ValueError) as exc:
        raise AttachmentRecoveryError(f"invalid ZIP payload: {exc}") from exc

    found = tuple(sorted(labels))
    missing = [label for label in EXPECTED_LABELS if label not in labels]
    extra_labels = [label for label in labels if label not in EXPECTED_LABELS]
    exact = not missing and not extra_labels and not unexpected and len(members) == len(EXPECTED_LABELS)
    if provenance_mode == PROVENANCE_OFFICIAL_FETCH:
        status = "OFFICIAL_FETCH_EXACT_A_D_UNREVIEWED" if exact else "OFFICIAL_FETCH_MEMBER_SET_HOLD"
    else:
        status = "LOCAL_BYTES_EXACT_A_D_UNVERIFIED_PROVENANCE" if exact else "LOCAL_BYTES_MEMBER_SET_HOLD"

    receipt: dict[str, Any] = {
        "schema": "invest_appalachia_framer_lms.attachment_recovery_receipt.v2",
        "provenance_mode": provenance_mode,
        "source_url": source_url,
        "retrieved_at_utc": retrieved_at_utc,
        "zip_sha256": _sha256(data),
        "zip_size_bytes": len(data),
        "members": sorted(members, key=lambda item: item["name"]),
        "attachment_labels_found": list(found),
        "missing_attachment_labels": missing,
        "unexpected_members": sorted(unexpected),
        "member_set_status": status,
        "attachments_complete_authorized": False,
        "qualification_or_budget_promotion_authorized": False,
        "external_contact_or_submission_authorized": False,
    }
    canonical = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    receipt["receipt_sha256"] = _sha256(canonical)
    return receipt


def analyze_zip(
    data: bytes,
    *,
    source_url: str | None = None,
    retrieved_at_utc: str | None = None,
) -> dict[str, Any]:
    """Analyze caller-supplied bytes without asserting where or when they were retrieved."""
    if source_url is not None or retrieved_at_utc is not None:
        raise AttachmentRecoveryError(
            "caller-supplied bytes cannot assert official-source provenance; use fetch_and_analyze_official_zip()"
        )
    return _analyze_zip_bytes(
        data,
        provenance_mode=PROVENANCE_LOCAL,
        source_url=None,
        retrieved_at_utc=None,
    )


def _fetch_official_zip(*, timeout_seconds: float = 30.0) -> tuple[bytes, str]:
    if timeout_seconds <= 0:
        raise AttachmentRecoveryError("timeout_seconds must be positive")
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "TJLabs-Invest-Appalachia-Attachment-Recovery/2.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            if final_url != SOURCE_URL:
                raise AttachmentRecoveryError(f"unexpected redirect target: {final_url}")
            data = response.read(MAX_ZIP_BYTES + 1)
            retrieved_at_utc = _observed_utc_now()
    except AttachmentRecoveryError:
        raise
    except Exception as exc:
        raise AttachmentRecoveryError(f"official ZIP fetch failed: {exc}") from exc
    if len(data) > MAX_ZIP_BYTES:
        raise AttachmentRecoveryError("ZIP payload exceeds bounded size")
    return data, retrieved_at_utc


def fetch_and_analyze_official_zip(*, timeout_seconds: float = 30.0) -> dict[str, Any]:
    """Fetch the exact buyer URL and bind the receipt to the observed successful retrieval event."""
    data, retrieved_at_utc = _fetch_official_zip(timeout_seconds=timeout_seconds)
    return _analyze_zip_bytes(
        data,
        provenance_mode=PROVENANCE_OFFICIAL_FETCH,
        source_url=SOURCE_URL,
        retrieved_at_utc=retrieved_at_utc,
    )


def _rename_noreplace(src_name: str, dst_name: str, *, dir_fd: int) -> None:
    """Atomically rename src to dst without replacement, or fail closed.

    Linux renameat2(RENAME_NOREPLACE) consumes the staging pathname in the same
    directory transaction that creates the final name. Platforms/libcs without
    that primitive are deliberately unsupported for durable exclusive publish.
    """
    if os.name != "posix":
        raise OSError(errno.ENOTSUP, "atomic no-replace rename is unavailable on this platform")
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = libc.renameat2
    except (OSError, AttributeError) as exc:
        raise OSError(errno.ENOTSUP, "renameat2(RENAME_NOREPLACE) is unavailable") from exc
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    ctypes.set_errno(0)
    rc = renameat2(
        dir_fd,
        os.fsencode(src_name),
        dir_fd,
        os.fsencode(dst_name),
        _RENAME_NOREPLACE,
    )
    if rc != 0:
        err = ctypes.get_errno() or errno.EIO
        raise OSError(err, os.strerror(err), dst_name)


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    offset = 0
    while offset < len(view):
        written = os.write(fd, view[offset:])
        if written <= 0:
            raise OSError(errno.EIO, "short write while staging receipt")
        offset += written


def _write_receipt_exclusive(path: str, rendered: str) -> None:
    """Durably publish one new receipt without deleting path-raced successors.

    The destination directory is opened once and retained. A unique mode-0600
    staging inode is created relative to that directory, fully written, and
    file-fsynced. Linux renameat2(RENAME_NOREPLACE) then atomically consumes the
    staging name while creating the final name; no successful path ever performs
    a later staging unlink. The final inode is identity-checked, the retained
    parent directory is fsynced, and the final inode is checked again before
    success returns.

    If failure occurs before the atomic rename, the private staging pathname is
    intentionally retained rather than unlinked by pathname: automatic cleanup
    would recreate the same stat(name)->unlink(name) foreign-successor race this
    contract exists to remove. Failure after publication likewise never deletes
    the final pathname. Callers must treat any exception as HOLD/indeterminate.
    """
    target = os.path.abspath(os.fspath(path))
    parent = os.path.dirname(target) or os.curdir
    basename = os.path.basename(target)
    if not basename:
        raise AttachmentRecoveryError("receipt output must name a file")

    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        directory_flags |= os.O_CLOEXEC
    try:
        parent_fd = os.open(parent, directory_flags)
    except OSError as exc:
        raise AttachmentRecoveryError(f"cannot open receipt output directory durably: {exc}") from exc

    fd = -1
    temp_name: str | None = None
    try:
        create_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_CLOEXEC"):
            create_flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            create_flags |= os.O_NOFOLLOW
        for _ in range(32):
            candidate = f".{basename}.{secrets.token_hex(16)}.tmp"
            try:
                fd = os.open(candidate, create_flags, 0o600, dir_fd=parent_fd)
                temp_name = candidate
                break
            except FileExistsError:
                continue
            except OSError as exc:
                raise AttachmentRecoveryError(f"cannot create private receipt staging file: {exc}") from exc
        if temp_name is None or fd < 0:
            raise AttachmentRecoveryError("cannot create unique private receipt staging file")

        try:
            if hasattr(os, "fchmod"):
                os.fchmod(fd, 0o600)
            _write_all(fd, rendered.encode("utf-8"))
            os.fsync(fd)
            owned = os.fstat(fd)
        except OSError as exc:
            raise AttachmentRecoveryError(f"cannot write receipt staging file: {exc}") from exc

        try:
            _rename_noreplace(temp_name, basename, dir_fd=parent_fd)
        except OSError as exc:
            raise AttachmentRecoveryError(f"cannot publish receipt output exclusively: {exc}") from exc

        expected_identity = (owned.st_dev, owned.st_ino)
        try:
            current = os.stat(basename, dir_fd=parent_fd, follow_symlinks=False)
        except OSError as exc:
            raise AttachmentRecoveryError(f"cannot verify receipt publication identity: {exc}") from exc
        if (current.st_dev, current.st_ino) != expected_identity:
            raise AttachmentRecoveryError("receipt publication identity changed during atomic no-overwrite rename")

        try:
            os.fsync(parent_fd)
        except OSError as exc:
            raise AttachmentRecoveryError(f"cannot durably commit receipt publication directory entry: {exc}") from exc

        try:
            current = os.stat(basename, dir_fd=parent_fd, follow_symlinks=False)
        except OSError as exc:
            raise AttachmentRecoveryError(f"cannot reverify durable receipt publication identity: {exc}") from exc
        if (current.st_dev, current.st_ino) != expected_identity:
            raise AttachmentRecoveryError("receipt publication identity changed before durable success return")
    finally:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            os.close(parent_fd)
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recover and verify Invest Appalachia Framer LMS attachment ZIP")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--zip",
        dest="zip_path",
        help="analyze local ZIP bytes as unverified provenance (never asserts an official retrieval)",
    )
    source.add_argument("--fetch", action="store_true", help="fetch and bind the exact official buyer ZIP URL")
    parser.add_argument("--output", help="optional new JSON receipt path; existing paths are never overwritten")
    args = parser.parse_args(argv)

    if args.fetch:
        receipt = fetch_and_analyze_official_zip()
    else:
        try:
            with open(args.zip_path, "rb") as handle:
                data = handle.read(MAX_ZIP_BYTES + 1)
        except OSError as exc:
            raise AttachmentRecoveryError(f"cannot read ZIP: {exc}") from exc
        receipt = analyze_zip(data)

    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        _write_receipt_exclusive(args.output, rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
