from __future__ import annotations

import os
import stat

try:  # package import
    from .profile_import import *
except ImportError:  # direct script / cwd import
    from profile_import import *

_IMPLEMENTATION_FILES = (
    "ontology_adapter.py",
    "profile_vocab.py",
    "profile_ntriples.py",
    "profile_export.py",
    "profile_import.py",
    "profile_receipt.py",
)


def _implementation_sha256() -> str:
    """Bind the complete executable profile, not only the CLI facade."""

    digest = hashlib.sha256()
    root = Path(__file__).resolve().parent
    for name in _IMPLEMENTATION_FILES:
        encoded_name = name.encode("utf-8")
        content = (root / name).read_bytes()
        digest.update(len(encoded_name).to_bytes(4, "big"))
        digest.update(encoded_name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _engine_sha256() -> str:
    return _sha((_PARENT / "temporal_evidence.py").read_bytes())


def build_receipt(jsonl_text: str, ntriples_text: str | None = None) -> dict[str, Any]:
    try:
        source_graph = TemporalEvidenceGraph.from_jsonl(jsonl_text)
    except TemporalEvidenceError as exc:
        raise OntologyProfileError(f"invalid temporal JSONL: {exc}") from exc
    canonical_jsonl = source_graph.to_jsonl()
    expected_nt = _build_ntriples(source_graph)
    actual_nt = expected_nt if ntriples_text is None else ntriples_text
    roundtrip = import_ntriples(actual_nt)
    roundtrip_jsonl = roundtrip.to_jsonl()
    if actual_nt != expected_nt or roundtrip_jsonl != canonical_jsonl:
        raise OntologyProfileError("semantic round trip did not preserve canonical evidence")
    payload = {
        "schema": "nih-temporal-kg-ontology-conformance/v1",
        "profile": PROFILE_VERSION,
        "source_schema": SOURCE_SCHEMA,
        "jsonl_sha256": _sha(canonical_jsonl.encode("utf-8")),
        "ntriples_sha256": _sha(actual_nt.encode("utf-8")),
        "roundtrip_jsonl_sha256": _sha(roundtrip_jsonl.encode("utf-8")),
        "implementation_sha256": _implementation_sha256(),
        "temporal_engine_sha256": _engine_sha256(),
        "fact_count": len(source_graph.facts),
        "event_count": len(source_graph.events),
        "triple_count": len(actual_nt.splitlines()),
        "semantic_roundtrip": True,
        "referenced_vocabularies": list(REFERENCED_VOCABULARIES),
    }
    return {**payload, "receipt_sha256": digest_json(payload)}


def verify_receipt(receipt: Mapping[str, Any], jsonl_text: str, ntriples_text: str) -> bool:
    expected_keys = {
        "schema", "profile", "source_schema", "jsonl_sha256", "ntriples_sha256",
        "roundtrip_jsonl_sha256", "implementation_sha256", "temporal_engine_sha256",
        "fact_count", "event_count", "triple_count", "semantic_roundtrip",
        "referenced_vocabularies", "receipt_sha256",
    }
    if not isinstance(receipt, Mapping) or set(receipt) != expected_keys:
        return False
    try:
        supplied_digest = receipt["receipt_sha256"]
        if not isinstance(supplied_digest, str) or not _HEX64.fullmatch(supplied_digest):
            return False
        payload = {key: receipt[key] for key in expected_keys if key != "receipt_sha256"}
        if digest_json(payload) != supplied_digest:
            return False
        rebuilt = build_receipt(jsonl_text, ntriples_text)
        return dict(receipt) == rebuilt
    except (OntologyProfileError, TemporalEvidenceError, TypeError, ValueError, OSError):
        return False


def _read_text(path_value: str) -> str:
    path = Path(path_value)
    before_path = path.lstat()
    if stat.S_ISLNK(before_path.st_mode) or not stat.S_ISREG(before_path.st_mode):
        raise OntologyProfileError("input must be a regular non-symlink file")
    if before_path.st_size > MAX_TEXT_BYTES:
        raise OntologyProfileError("input exceeds 8 MiB profile limit")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        before_fd = os.fstat(fd)
        if not stat.S_ISREG(before_fd.st_mode):
            raise OntologyProfileError("input descriptor must identify a regular file")
        if (before_path.st_dev, before_path.st_ino) != (before_fd.st_dev, before_fd.st_ino):
            raise OntologyProfileError("input path changed before open")
        if before_fd.st_size > MAX_TEXT_BYTES:
            raise OntologyProfileError("input exceeds 8 MiB profile limit")

        chunks: list[bytes] = []
        remaining = before_fd.st_size + 1
        while remaining > 0:
            chunk = os.read(fd, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after_fd = os.fstat(fd)
        stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(before_fd, field) != getattr(after_fd, field) for field in stable_fields):
            raise OntologyProfileError("input changed while being read")
        if len(data) != before_fd.st_size:
            raise OntologyProfileError("input size changed while being read")
    finally:
        os.close(fd)

    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OntologyProfileError("input must be UTF-8") from exc


def _write_text(path_value: str, text: str) -> None:
    path = Path(path_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(temp, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
        raise

__all__ = tuple(name for name in globals() if not name.startswith("__"))
