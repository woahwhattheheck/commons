from __future__ import annotations

import hashlib
import io
import os
import stat
import zipfile
from typing import Any

from .schema import RFP_FILENAME, WORKBOOK_FILENAME, QualificationError, _canonical_time

MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_XLSX_ENTRIES = 10_000
MAX_XLSX_UNCOMPRESSED_BYTES = 256 * 1024 * 1024


def _expected(source_id: str) -> tuple[str, bytes]:
    if source_id == "RFP_PDF":
        return RFP_FILENAME, b"%PDF-"
    if source_id == "REQUIREMENTS_XLSX":
        return WORKBOOK_FILENAME, b"PK\x03\x04"
    raise QualificationError("unknown source_id")


def read_regular_file(path: str | os.PathLike[str], *, maximum: int, label: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(os.fspath(path), flags)
    except OSError as exc:
        raise QualificationError(f"{label} is not a readable non-symlink file") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise QualificationError(f"{label} must be a regular file")
        if before.st_size < 0 or before.st_size > maximum:
            raise QualificationError(f"{label} size out of bounds")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(1024 * 1024, maximum + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum:
                raise QualificationError(f"{label} exceeds size bound during read")
        after = os.fstat(fd)
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if identity_before != identity_after or total != after.st_size:
            raise QualificationError(f"{label} changed during read")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _validate_pdf(raw: bytes) -> None:
    if not raw.startswith(b"%PDF-"):
        raise QualificationError("RFP_PDF magic mismatch")
    if b"%%EOF" not in raw[-4096:]:
        raise QualificationError("RFP_PDF lacks terminal PDF marker")


def _validate_xlsx(raw: bytes) -> None:
    if not raw.startswith(b"PK\x03\x04"):
        raise QualificationError("REQUIREMENTS_XLSX magic mismatch")
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
            infos = archive.infolist()
            if len(infos) > MAX_XLSX_ENTRIES:
                raise QualificationError("REQUIREMENTS_XLSX entry count out of bounds")
            total_uncompressed = 0
            names: set[str] = set()
            for info in infos:
                total_uncompressed += info.file_size
                if total_uncompressed > MAX_XLSX_UNCOMPRESSED_BYTES:
                    raise QualificationError("REQUIREMENTS_XLSX uncompressed size out of bounds")
                name = info.filename.replace("\\", "/")
                if name.startswith("/") or any(part == ".." for part in name.split("/")):
                    raise QualificationError("REQUIREMENTS_XLSX contains unsafe archive path")
                names.add(name)
            required = {"[Content_Types].xml", "_rels/.rels", "xl/workbook.xml"}
            if not required.issubset(names):
                raise QualificationError("REQUIREMENTS_XLSX missing required workbook entries")
            if archive.testzip() is not None:
                raise QualificationError("REQUIREMENTS_XLSX CRC validation failed")
    except QualificationError:
        raise
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        raise QualificationError("REQUIREMENTS_XLSX is not a valid XLSX container") from exc


def bind_source_file(source_id: str, path: str | os.PathLike[str], captured_at: str) -> dict[str, Any]:
    filename, _ = _expected(source_id)
    captured_at = _canonical_time(captured_at, name="captured_at")
    raw = read_regular_file(path, maximum=MAX_SOURCE_BYTES, label="source file")
    if not raw:
        raise QualificationError("source file is empty")
    if source_id == "RFP_PDF":
        _validate_pdf(raw)
    else:
        _validate_xlsx(raw)
    return {
        "source_id": source_id,
        "status": "BOUND",
        "filename": filename,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "captured_at": captured_at,
    }
