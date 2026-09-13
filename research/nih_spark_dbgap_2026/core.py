from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Mapping

SCHEMA_CORPUS = "nih.spark.dbgap.corpus/v1"
SCHEMA_RESOURCES = "nih.spark.dbgap.resources/v1"
SCHEMA_T1_QUERIES = "nih.spark.dbgap.track1-input/v1"
SCHEMA_T1_OUTPUT = "nih.spark.dbgap.track1-output/v1"
SCHEMA_T2_QUERIES = "nih.spark.dbgap.track2-input/v1"
SCHEMA_T2_OUTPUT = "nih.spark.dbgap.track2-output/v1"
SCHEMA_RUN_RECEIPT = "nih.spark.dbgap.run-receipt/v1"
ONT_NONE = "ONT_NONE"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ALLOWED_RESOURCE_KINDS = {"ONTOLOGY", "VOCABULARY", "PUBLIC_CORPUS", "SOFTWARE"}


class ContractError(ValueError):
    pass


def _reject_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ContractError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json_strict_bytes(data: bytes) -> Any:
    if len(data) > 16 * 1024 * 1024:
        raise ContractError("input exceeds 16 MiB")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("input must be UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_pairs,
            parse_constant=lambda x: (_ for _ in ()).throw(ContractError(f"non-finite JSON number: {x}")),
        )
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid JSON: {exc.msg}") from exc
    return value


def load_json_strict(path: str | Path) -> Any:
    p = Path(path)
    try:
        before = p.lstat()
    except OSError as exc:
        raise ContractError(f"cannot stat input: {exc}") from exc
    if not stat.S_ISREG(before.st_mode):
        raise ContractError("input must be an ordinary non-symlink file")
    if before.st_size > 16 * 1024 * 1024:
        raise ContractError("input exceeds 16 MiB")

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(p, flags)
    except OSError as exc:
        raise ContractError(f"cannot open input safely: {exc}") from exc
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise ContractError("input must remain an ordinary file")
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ContractError("input generation changed before open")
        if opened.st_size > 16 * 1024 * 1024:
            raise ContractError("input exceeds 16 MiB")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(1024 * 1024, 16 * 1024 * 1024 + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > 16 * 1024 * 1024:
                raise ContractError("input exceeds 16 MiB")
        after = os.fstat(fd)
        if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ContractError("input generation changed during read")
        if total != after.st_size:
            raise ContractError("input byte count changed during read")
        return load_json_strict_bytes(b"".join(chunks))
    finally:
        os.close(fd)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def semantic_sha256(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def _exact_keys(obj: Mapping[str, Any], keys: set[str], where: str) -> None:
    actual = set(obj)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        raise ContractError(f"{where} keys mismatch: missing={missing} extra={extra}")


def _string(value: Any, where: str, *, max_len: int = 4096, allow_empty: bool = False) -> str:
    if type(value) is not str:
        raise ContractError(f"{where} must be a string")
    if not allow_empty and not value:
        raise ContractError(f"{where} must be non-empty")
    if len(value) > max_len:
        raise ContractError(f"{where} too long")
    if _CONTROL_RE.search(value):
        raise ContractError(f"{where} contains control characters")
    return value


def _identifier(value: Any, where: str) -> str:
    text = _string(value, where, max_len=128)
    if not _ID_RE.fullmatch(text):
        raise ContractError(f"{where} is not a safe identifier")
    return text


def _sha(value: Any, where: str) -> str:
    text = _string(value, where, max_len=64)
    if not _SHA256_RE.fullmatch(text):
        raise ContractError(f"{where} must be lowercase SHA-256")
    return text


def _int(value: Any, where: str, *, minimum: int = 0, maximum: int = 2**53 - 1) -> int:
    if type(value) is not int:
        raise ContractError(f"{where} must be an integer (bool/float rejected)")
    if value < minimum or value > maximum:
        raise ContractError(f"{where} outside range")
    return value


def _array(value: Any, where: str, *, max_len: int = 100_000) -> list[Any]:
    if type(value) is not list:
        raise ContractError(f"{where} must be an array")
    if len(value) > max_len:
        raise ContractError(f"{where} too many items")
    return value


def _object(value: Any, where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ContractError(f"{where} must be an object")
    return value


def normalized_tokens(text: str) -> tuple[str, ...]:
    return tuple(token.lower() for token in _TOKEN_RE.findall(text) if token)


def text_digest(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))

