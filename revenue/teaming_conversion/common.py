#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

INPUT_SCHEMA = "teaming-conversion-input/v1"
POLICY_SCHEMA = "teaming-conversion-policy/v1"
RECEIPT_SCHEMA = "teaming-conversion-receipt/v1"

INTERPRETATIONS = {
    "POSITIVE_CONTINUE",
    "REQUESTED_MORE_INFO",
    "CONDITIONAL_INTEREST",
    "DECLINED",
    "AMBIGUOUS",
}
SENDER_ROLES = {"PRIME_CONTACT", "BUYER_CONTACT", "PARTNER_CONTACT", "OTHER"}
SOURCE_CLASSES = {"GMAIL", "SLACK", "OTHER_RETAINED"}
PREP_STATES = {"READY", "DRAFT", "MISSING"}
RELEASE_CLASSES = {
    "PROSPECT_SAFE_SUMMARY",
    "PROSPECT_SAFE_PUBLIC_REFERENCE",
    "OWNER_APPROVAL_REQUIRED",
    "INTERNAL_ONLY",
}
GATE_STATES = {"CLEAR", "CURABLE", "BLOCKED", "UNKNOWN"}
COMMITMENT_KINDS = {
    "PRICING",
    "STAFFING",
    "REFERENCE",
    "CERTIFICATION",
    "DELIVERY_DATE",
    "SUBCONTRACT",
    "EXCLUSIVITY",
    "INSURANCE",
    "SIGNATURE",
    "SUBMISSION",
    "CONTRACT",
}
DISPOSITIONS = {
    "FOLLOWUP_READY",
    "NEEDS_CLARIFICATION",
    "ASSET_PREP_REQUIRED",
    "QUALIFICATION_BLOCKED",
    "DECLINED",
    "HOLD",
}

MAX_JSON_BYTES = 1_048_576
MAX_ITEMS = 2_000
MAX_TEXT = 512
MAX_SNIPPET = 1_000
MAX_SAFE_SNIPPETS_PER_ASSET = 20
MAX_SECONDS = 366 * 24 * 60 * 60 * 10
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SECRETISH_RE = re.compile(
    r"(?i)(?:^|[-_.:])(?:api[-_]?key|secret|token|password|passwd|private[-_]?key|bearer)(?:$|[-_.:])"
)


class ControlError(ValueError):
    pass


class DuplicateKeyError(ControlError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DuplicateKeyError(f"duplicate JSON object key: {key}")
        out[key] = value
    return out


def _parse_constant(value: str) -> Any:
    raise ControlError(f"non-finite JSON number is forbidden: {value}")


def parse_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        raise ControlError(f"{label} must be bytes")
    if len(raw) > MAX_JSON_BYTES:
        raise ControlError(f"{label} exceeds {MAX_JSON_BYTES} bytes")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ControlError(f"{label} must be strict UTF-8 JSON") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_parse_constant,
        )
    except DuplicateKeyError:
        raise
    except ControlError:
        raise
    except json.JSONDecodeError as exc:
        raise ControlError(f"{label} is not valid JSON: {exc.msg}") from exc
    return _require_dict(value, label)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def digest_object(value: Any) -> str:
    return digest_bytes(canonical_bytes(value))


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ControlError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str, *, maximum: int = MAX_ITEMS) -> list[Any]:
    if type(value) is not list:
        raise ControlError(f"{label} must be a list")
    if len(value) > maximum:
        raise ControlError(f"{label} exceeds {maximum} entries")
    return value


def _require_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ControlError(f"{label} must be a boolean")
    return value


def _require_int(value: Any, label: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int:
        raise ControlError(f"{label} must be an integer")
    if not minimum <= value <= maximum:
        raise ControlError(f"{label} must be between {minimum} and {maximum}")
    return value


def _require_text(value: Any, label: str, *, max_len: int = MAX_TEXT) -> str:
    if type(value) is not str:
        raise ControlError(f"{label} must be a string")
    text = value.strip()
    if not text:
        raise ControlError(f"{label} must not be empty")
    if len(text) > max_len:
        raise ControlError(f"{label} exceeds {max_len} characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in text):
        raise ControlError(f"{label} contains control characters")
    return text


def _optional_text(value: Any, label: str, *, max_len: int = MAX_TEXT) -> str | None:
    if value is None:
        return None
    return _require_text(value, label, max_len=max_len)


def _require_enum(value: Any, label: str, allowed: set[str]) -> str:
    text = _require_text(value, label, max_len=64)
    if text not in allowed:
        raise ControlError(f"{label} must be one of: {', '.join(sorted(allowed))}")
    return text


def _require_ref(value: Any, label: str) -> str:
    text = _require_text(value, label, max_len=128)
    if not _REF_RE.fullmatch(text):
        raise ControlError(f"{label} must be an opaque identifier")
    if _SECRETISH_RE.search(text):
        raise ControlError(f"{label} looks secret-shaped")
    return text


def _require_sha256(value: Any, label: str) -> str:
    text = _require_text(value, label, max_len=64)
    if not _HEX64_RE.fullmatch(text):
        raise ControlError(f"{label} must be a lowercase SHA-256 hex digest")
    return text


def _parse_time(value: Any, label: str) -> datetime:
    text = _require_text(value, label, max_len=32)
    if not text.endswith("Z"):
        raise ControlError(f"{label} must be canonical UTC ending in Z")
    try:
        dt = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise ControlError(f"{label} must be ISO-8601 UTC") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ControlError(f"{label} must include UTC timezone")
    dt = dt.astimezone(timezone.utc)
    if dt.microsecond:
        raise ControlError(f"{label} must use whole seconds")
    if _format_time(dt) != text:
        raise ControlError(f"{label} must use canonical YYYY-MM-DDTHH:MM:SSZ form")
    return dt


def _require_as_of(as_of: datetime) -> datetime:
    if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ControlError("as_of must be a timezone-aware datetime")
    dt = as_of.astimezone(timezone.utc).replace(microsecond=0)
    return dt


def _format_time(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _reject_unknown(obj: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = set(obj) - allowed
    if unknown:
        raise ControlError(f"{label} has unknown fields: {', '.join(sorted(unknown))}")


def _parse_ref_list(value: Any, label: str) -> list[str]:
    raw = _require_list(value, label)
    out: list[str] = []
    seen: set[str] = set()
    for i, item in enumerate(raw):
        ref = _require_ref(item, f"{label}[{i}]")
        if ref in seen:
            raise ControlError(f"{label} contains duplicate identifier {ref!r}")
        seen.add(ref)
        out.append(ref)
    return out



def _dedupe_or_conflict(
    rows: Iterable[dict[str, Any]], *, id_key: str, extra_unique_key: str | None, label: str
) -> tuple[list[dict[str, Any]], list[str]]:
    unique: list[dict[str, Any]] = []
    by_id: dict[str, bytes] = {}
    by_extra: dict[str, tuple[str, bytes]] = {}
    conflicts: list[str] = []
    for row in rows:
        row_bytes = canonical_bytes(_json_ready(row))
        row_id = str(row[id_key])
        previous = by_id.get(row_id)
        if previous is not None:
            if previous != row_bytes:
                conflicts.append(f"{label}_id_conflict:{row_id}")
            continue
        by_id[row_id] = row_bytes
        if extra_unique_key is not None:
            extra = str(row[extra_unique_key])
            prior_extra = by_extra.get(extra)
            if prior_extra is not None:
                prior_id, prior_bytes = prior_extra
                if prior_bytes != row_bytes or prior_id != row_id:
                    conflicts.append(f"{label}_{extra_unique_key}_conflict:{extra}")
                    continue
            by_extra[extra] = (row_id, row_bytes)
        unique.append(row)
    return unique, conflicts


def _json_ready(value: Any) -> Any:
    if isinstance(value, datetime):
        return _format_time(value)
    if type(value) is dict:
        return {k: _json_ready(v) for k, v in value.items()}
    if type(value) is list:
        return [_json_ready(v) for v in value]
    return value



def read_bounded_regular(path: str | Path, *, max_bytes: int = MAX_JSON_BYTES) -> bytes:
    target = Path(path)
    try:
        pre = os.lstat(target)
    except OSError as exc:
        raise ControlError(f"cannot inspect input {target}: {exc}") from exc
    if stat.S_ISLNK(pre.st_mode) or not stat.S_ISREG(pre.st_mode):
        raise ControlError(f"input is not a regular file: {target}")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        # Prevent a lstat->open replacement with a FIFO/device from blocking before fstat.
        flags |= os.O_NONBLOCK
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        fd = os.open(target, flags)
    except OSError as exc:
        raise ControlError(f"cannot open regular input {target}: {exc}") from exc
    try:
        meta = os.fstat(fd)
        if not stat.S_ISREG(meta.st_mode):
            raise ControlError(f"input is not a regular file: {target}")
        if meta.st_size > max_bytes:
            raise ControlError(f"input exceeds {max_bytes} bytes: {target}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(65_536, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise ControlError(f"input exceeds {max_bytes} bytes: {target}")
        return b"".join(chunks)
    finally:
        os.close(fd)


def write_exclusive_regular(path: str | Path, data: bytes) -> None:
    target = Path(path)
    if type(data) is not bytes:
        raise ControlError("output data must be bytes")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(target, flags, 0o600)
    except OSError as exc:
        raise ControlError(f"refusing output target {target}: {exc}") from exc
    try:
        meta = os.fstat(fd)
        if not stat.S_ISREG(meta.st_mode):
            raise ControlError(f"output is not a regular file: {target}")
        view = memoryview(data)
        written = 0
        while written < len(data):
            n = os.write(fd, view[written:])
            if n <= 0:
                raise ControlError(f"short write to output {target}")
            written += n
        os.fsync(fd)
    except Exception:
        try:
            target.unlink(missing_ok=True)
        except Exception:
            pass
        raise
    finally:
        os.close(fd)
