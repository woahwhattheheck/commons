"""Fail-closed immutable source ingest for a single local ChartTrace case."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import stat
import threading
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union


class IngestHoldCode(str, Enum):
    HOLD_SOURCE_HASH_MISMATCH = "HOLD_SOURCE_HASH_MISMATCH"
    HOLD_ENCRYPTED_INPUT = "HOLD_ENCRYPTED_INPUT"
    HOLD_SOURCE_TAMPER = "HOLD_SOURCE_TAMPER"

    def __str__(self) -> str:
        return self.value


HOLD_SOURCE_HASH_MISMATCH = IngestHoldCode.HOLD_SOURCE_HASH_MISMATCH
HOLD_ENCRYPTED_INPUT = IngestHoldCode.HOLD_ENCRYPTED_INPUT
HOLD_SOURCE_TAMPER = IngestHoldCode.HOLD_SOURCE_TAMPER


class IngestHold(RuntimeError):
    """A source-integrity condition that must stop analysis."""

    def __init__(self, code: IngestHoldCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}")


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DOCUMENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_PDF_PAGE_RE = re.compile(rb"/Type\s*/Page\b")
_PDF_ENCRYPT_RE = re.compile(rb"/Encrypt\b")
_EMPTY_HASH = "0" * 64


@dataclass(frozen=True, slots=True)
class SourceManifestEntry:
    document_id: str
    source_name: str
    stored_path: str
    source_hash: str
    size_bytes: int
    mime_type: str
    page_count: Optional[int]
    encrypted: bool
    duplicate_of: Optional[str]
    previous_receipt_hash: str
    receipt_hash: str

    @property
    def is_duplicate(self) -> bool:
        return self.duplicate_of is not None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def sha256_file(path: Union[str, os.PathLike[str]]) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_pdf(data: bytes) -> Tuple[bool, Optional[int]]:
    """Return ``(encrypted, page_count)`` without attempting decryption."""

    if not data.startswith(b"%PDF-"):
        return False, None
    encrypted = _PDF_ENCRYPT_RE.search(data) is not None
    return encrypted, len(_PDF_PAGE_RE.findall(data))


def detect_mime(source_name: str, data_prefix: bytes) -> str:
    if data_prefix.startswith(b"%PDF-"):
        return "application/pdf"
    if data_prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data_prefix.startswith((b"\xff\xd8\xff",)):
        return "image/jpeg"
    guessed, _ = mimetypes.guess_type(source_name)
    return guessed or "application/octet-stream"


def _canonical_json(value: Dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _receipt_payload(entry: SourceManifestEntry) -> Dict[str, Any]:
    payload = entry.to_dict()
    payload.pop("receipt_hash")
    return payload


class ImmutableIngestor:
    """Copy exact source bytes into a read-only, content-addressed inventory.

    ``case_root`` is expected to be an unlocked local case vault. Originals and
    derivatives always occupy different directories.
    """

    def __init__(self, case_root: Union[str, os.PathLike[str]]) -> None:
        self.case_root = Path(case_root)
        self.originals_dir = self.case_root / "originals"
        self.derivatives_dir = self.case_root / "derivatives"
        self.manifest_path = self.case_root / "source-manifest.jsonl"
        self.originals_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.derivatives_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.originals_dir, 0o700)
        os.chmod(self.derivatives_dir, 0o700)
        self._lock = threading.RLock()
        self._entries = self._load_manifest()

    @property
    def entries(self) -> Tuple[SourceManifestEntry, ...]:
        return tuple(self._entries)

    def _load_manifest(self) -> List[SourceManifestEntry]:
        if not self.manifest_path.exists():
            return []
        entries: List[SourceManifestEntry] = []
        previous = _EMPTY_HASH
        try:
            with self.manifest_path.open("r", encoding="utf-8", newline="") as stream:
                for line_number, line in enumerate(stream, 1):
                    raw = json.loads(line)
                    entry = SourceManifestEntry(**raw)
                    expected = hashlib.sha256(
                        _canonical_json(_receipt_payload(entry))
                    ).hexdigest()
                    if (
                        entry.previous_receipt_hash != previous
                        or entry.receipt_hash != expected
                    ):
                        raise ValueError(f"broken receipt chain at line {line_number}")
                    entries.append(entry)
                    previous = entry.receipt_hash
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IngestHold(
                HOLD_SOURCE_TAMPER, f"source manifest failed verification: {exc}"
            ) from exc
        return entries

    def _next_document_id(self) -> str:
        used = {entry.document_id for entry in self._entries}
        number = len(used) + 1
        while True:
            candidate = f"DOC-{number:04d}"
            if candidate not in used:
                return candidate
            number += 1

    def _copy_and_hash(self, source_path: Path, temporary_path: Path) -> Tuple[str, int]:
        if source_path.is_symlink():
            raise IngestHold(HOLD_SOURCE_TAMPER, "symbolic-link sources are refused")

        open_flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            open_flags |= os.O_NOFOLLOW
        try:
            source_fd = os.open(source_path, open_flags)
        except OSError as exc:
            raise IngestHold(HOLD_SOURCE_TAMPER, "source could not be opened") from exc

        digest = hashlib.sha256()
        size = 0
        try:
            before_fd = os.fstat(source_fd)
            before_path = source_path.stat()
            if not stat.S_ISREG(before_fd.st_mode):
                raise IngestHold(HOLD_SOURCE_TAMPER, "source is not a regular file")
            with os.fdopen(source_fd, "rb", closefd=False) as source, temporary_path.open(
                "xb"
            ) as destination:
                os.chmod(temporary_path, 0o600)
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
                    destination.write(chunk)
                    size += len(chunk)
                destination.flush()
                os.fsync(destination.fileno())
            after_fd = os.fstat(source_fd)
            after_path = source_path.stat()
            stable_fd = (
                before_fd.st_dev,
                before_fd.st_ino,
                before_fd.st_size,
                before_fd.st_mtime_ns,
            ) == (
                after_fd.st_dev,
                after_fd.st_ino,
                after_fd.st_size,
                after_fd.st_mtime_ns,
            )
            stable_path = (
                before_path.st_dev,
                before_path.st_ino,
                before_path.st_size,
                before_path.st_mtime_ns,
            ) == (
                after_path.st_dev,
                after_path.st_ino,
                after_path.st_size,
                after_path.st_mtime_ns,
            )
            if not stable_fd or not stable_path or size != before_fd.st_size:
                raise IngestHold(
                    HOLD_SOURCE_TAMPER, "source changed while it was being copied"
                )
            return digest.hexdigest(), size
        finally:
            os.close(source_fd)

    def ingest(
        self,
        source: Union[str, os.PathLike[str]],
        *,
        expected_sha256: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> SourceManifestEntry:
        source_path = Path(source)
        if expected_sha256 is not None and not _SHA256_RE.fullmatch(expected_sha256):
            raise ValueError("expected_sha256 must be lowercase SHA-256")
        if document_id is not None and not _DOCUMENT_ID_RE.fullmatch(document_id):
            raise ValueError("document_id is not a stable identifier")

        with self._lock:
            chosen_id = document_id or self._next_document_id()
            if any(entry.document_id == chosen_id for entry in self._entries):
                raise ValueError(f"document_id already exists: {chosen_id}")

            temporary_path = self.originals_dir / (
                f".ingest-{os.getpid()}-{threading.get_ident()}-{len(self._entries)}"
            )
            try:
                source_hash, size_bytes = self._copy_and_hash(
                    source_path, temporary_path
                )
                if expected_sha256 is not None and source_hash != expected_sha256:
                    raise IngestHold(
                        HOLD_SOURCE_HASH_MISMATCH,
                        "copied bytes do not match the asserted source hash",
                    )

                data = temporary_path.read_bytes()
                mime_type = detect_mime(source_path.name, data[:32])
                encrypted, page_count = probe_pdf(data)
                if encrypted:
                    raise IngestHold(
                        HOLD_ENCRYPTED_INPUT,
                        "encrypted PDF input requires an authorized decrypted source",
                    )

                duplicate = next(
                    (
                        entry
                        for entry in self._entries
                        if entry.source_hash == source_hash
                        and entry.size_bytes == size_bytes
                    ),
                    None,
                )
                suffix = ".pdf" if mime_type == "application/pdf" else ".bin"
                stored_relative = f"originals/{source_hash}{suffix}"
                stored_path = self.case_root / stored_relative
                if stored_path.exists():
                    if (
                        stored_path.stat().st_size != size_bytes
                        or sha256_file(stored_path) != source_hash
                    ):
                        raise IngestHold(
                            HOLD_SOURCE_TAMPER,
                            "content-addressed original has changed",
                        )
                    temporary_path.unlink()
                else:
                    os.replace(temporary_path, stored_path)
                    os.chmod(stored_path, stat.S_IRUSR)

                previous = (
                    self._entries[-1].receipt_hash if self._entries else _EMPTY_HASH
                )
                unsigned = SourceManifestEntry(
                    document_id=chosen_id,
                    source_name=source_path.name,
                    stored_path=stored_relative,
                    source_hash=source_hash,
                    size_bytes=size_bytes,
                    mime_type=mime_type,
                    page_count=page_count,
                    encrypted=False,
                    duplicate_of=duplicate.document_id if duplicate else None,
                    previous_receipt_hash=previous,
                    receipt_hash="",
                )
                receipt_hash = hashlib.sha256(
                    _canonical_json(_receipt_payload(unsigned))
                ).hexdigest()
                entry = SourceManifestEntry(
                    **{
                        **unsigned.to_dict(),
                        "receipt_hash": receipt_hash,
                    }
                )
                with self.manifest_path.open(
                    "a", encoding="utf-8", newline="\n"
                ) as manifest:
                    manifest.write(
                        json.dumps(
                            entry.to_dict(),
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=True,
                        )
                        + "\n"
                    )
                    manifest.flush()
                    os.fsync(manifest.fileno())
                os.chmod(self.manifest_path, 0o600)
                self._entries.append(entry)
                return entry
            finally:
                if temporary_path.exists():
                    temporary_path.unlink()

    def verify_original(
        self, entry_or_document_id: Union[SourceManifestEntry, str]
    ) -> SourceManifestEntry:
        if isinstance(entry_or_document_id, SourceManifestEntry):
            entry = entry_or_document_id
        else:
            try:
                entry = next(
                    item
                    for item in self._entries
                    if item.document_id == entry_or_document_id
                )
            except StopIteration as exc:
                raise KeyError(entry_or_document_id) from exc
        stored_path = self.case_root / entry.stored_path
        if (
            not stored_path.is_file()
            or stored_path.stat().st_size != entry.size_bytes
            or sha256_file(stored_path) != entry.source_hash
        ):
            raise IngestHold(
                HOLD_SOURCE_TAMPER,
                f"original verification failed for {entry.document_id}",
            )
        if stored_path.stat().st_mode & 0o222:
            raise IngestHold(
                HOLD_SOURCE_TAMPER,
                f"original is writable for {entry.document_id}",
            )
        return entry

    def verify_all(self) -> Tuple[SourceManifestEntry, ...]:
        return tuple(self.verify_original(entry) for entry in self._entries)

    def store_derivative(
        self,
        document_id: str,
        derivative_name: str,
        data: bytes,
        *,
        source_hash: str,
    ) -> Path:
        """Store a replaceable derivative after re-verifying its exact source."""

        entry = self.verify_original(document_id)
        if source_hash != entry.source_hash:
            raise IngestHold(
                HOLD_SOURCE_HASH_MISMATCH,
                "derivative source hash does not match the immutable original",
            )
        if (
            not derivative_name
            or Path(derivative_name).name != derivative_name
            or derivative_name in {".", ".."}
        ):
            raise ValueError("derivative_name must be one safe path component")
        document_dir = self.derivatives_dir / document_id
        document_dir.mkdir(mode=0o700, exist_ok=True)
        target = document_dir / derivative_name
        temporary = document_dir / f".{derivative_name}.tmp-{os.getpid()}"
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        os.chmod(target, 0o600)
        return target
