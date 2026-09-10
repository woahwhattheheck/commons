"""Strict input primitives and byte/tree identity helpers for TITAN admission."""

from __future__ import annotations

import hashlib
import json
import re
import stat
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = 1
MAX_ABS_NUMBER = Decimal("1e18")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class AdmissionError(ValueError):
    """Raised when an input cannot be trusted enough to evaluate."""


class DuplicateKeyError(AdmissionError):
    """Raised for duplicate JSON object keys."""


@dataclass(frozen=True)
class InputPaths:
    receipt: Path
    policy: Path
    report: Path
    baseline_root: Path
    candidate_root: Path
    baseline_artifact: Path
    candidate_artifact: Path


@dataclass(frozen=True)
class ExpectedPins:
    base_commit: str
    head_commit: str
    workflow_run_id: int
    source_sha256: str
    engine_sha256: str
    evaluator_sha256: str
    baseline_archive_sha256: str
    baseline_tree_sha256: str
    candidate_archive_sha256: str
    candidate_tree_sha256: str
    report_sha256: str
    bank_sha256: str
    policy_sha256: str


@dataclass(frozen=True)
class Gate:
    name: str
    passed: bool
    observed: Any
    required: Any
    detail: str = ""

    def as_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "observed": json_ready(self.observed),
            "required": json_ready(self.required),
            "detail": self.detail,
        }


def _reject_constant(value: str) -> None:
    raise AdmissionError(f"non-standard JSON numeric constant is forbidden: {value}")


def _strict_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def load_strict_json(path: Path) -> Any:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AdmissionError(f"cannot read {path}: {exc}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AdmissionError(f"{path} is not UTF-8 JSON") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_float=Decimal,
            parse_constant=_reject_constant,
        )
    except AdmissionError:
        raise
    except (json.JSONDecodeError, InvalidOperation) as exc:
        raise AdmissionError(f"invalid JSON in {path}: {exc}") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> tuple[str, int]:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise AdmissionError(f"cannot stat {path}: {exc}") from exc
    if stat.S_ISLNK(mode):
        raise AdmissionError(f"symlink inputs are forbidden: {path}")
    if not stat.S_ISREG(mode):
        raise AdmissionError(f"expected a regular file: {path}")
    digest = hashlib.sha256()
    total = 0
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                total += len(chunk)
    except OSError as exc:
        raise AdmissionError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest(), total


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AdmissionError(f"{label} must be an object")
    return value


def require_array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AdmissionError(f"{label} must be an array")
    return value


def require_exact_keys(value: Mapping[str, Any], expected: Iterable[str], label: str) -> None:
    expected_set = set(expected)
    actual_set = set(value)
    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)
    if missing or extra:
        parts: list[str] = []
        if missing:
            parts.append(f"missing={missing}")
        if extra:
            parts.append(f"extra={extra}")
        raise AdmissionError(f"{label} has non-exact keys: {'; '.join(parts)}")


def require_string(value: Any, label: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str):
        raise AdmissionError(f"{label} must be a string")
    if nonempty and not value:
        raise AdmissionError(f"{label} must not be empty")
    if "\x00" in value:
        raise AdmissionError(f"{label} contains NUL")
    return value


def require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AdmissionError(f"{label} must be a boolean")
    return value


def require_int(value: Any, label: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AdmissionError(f"{label} must be an integer (booleans are forbidden)")
    if minimum is not None and value < minimum:
        raise AdmissionError(f"{label} must be >= {minimum}")
    return value


def require_decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool):
        raise AdmissionError(f"{label} must be numeric (booleans are forbidden)")
    if isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, Decimal):
        result = value
    else:
        raise AdmissionError(f"{label} must be a JSON number")
    if not result.is_finite():
        raise AdmissionError(f"{label} must be finite")
    if abs(result) > MAX_ABS_NUMBER:
        raise AdmissionError(f"{label} exceeds the absolute numeric bound {MAX_ABS_NUMBER}")
    return result


def require_hex(value: Any, label: str, width: int) -> str:
    text = require_string(value, label)
    pattern = HEX40 if width == 40 else HEX64
    if pattern.fullmatch(text) is None:
        raise AdmissionError(f"{label} must be exactly {width} lowercase hexadecimal characters")
    return text


def require_safe_relpath(value: Any, label: str) -> str:
    text = require_string(value, label)
    if "\\" in text:
        raise AdmissionError(f"{label} must use POSIX separators")
    pure = PurePosixPath(text)
    if pure.is_absolute() or text.startswith("/"):
        raise AdmissionError(f"{label} must be relative")
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise AdmissionError(f"{label} is not a normalized relative path")
    normalized = pure.as_posix()
    if normalized != text:
        raise AdmissionError(f"{label} is not normalized")
    return text


def dec_text(value: Decimal) -> str:
    """Canonical, non-exponent decimal text with no negative zero."""
    if value == 0:
        return "0"
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return dec_text(value)
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    return value


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            json_ready(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def digest_canonical(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def mean(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise AdmissionError("cannot compute a mean over an empty group")
    return sum(values, Decimal(0)) / Decimal(len(values))


def outcome(own: Decimal, rival: Decimal) -> str:
    margin = own - rival
    if margin > 0:
        return "W"
    if margin < 0:
        return "L"
    return "T"


def validate_manifest(manifest: Any, label: str) -> dict[str, Any]:
    obj = require_object(manifest, label)
    require_exact_keys(
        obj,
        {"archive_sha256", "archive_bytes", "entrypoint", "tree_sha256", "files"},
        label,
    )
    archive_sha = require_hex(obj["archive_sha256"], f"{label}.archive_sha256", 64)
    archive_bytes = require_int(obj["archive_bytes"], f"{label}.archive_bytes", minimum=1)
    entrypoint = require_safe_relpath(obj["entrypoint"], f"{label}.entrypoint")
    tree_sha = require_hex(obj["tree_sha256"], f"{label}.tree_sha256", 64)
    raw_files = require_array(obj["files"], f"{label}.files")
    if not raw_files:
        raise AdmissionError(f"{label}.files must not be empty")

    files: list[dict[str, Any]] = []
    paths: list[str] = []
    for index, raw_file in enumerate(raw_files):
        file_label = f"{label}.files[{index}]"
        file_obj = require_object(raw_file, file_label)
        require_exact_keys(file_obj, {"path", "sha256", "bytes"}, file_label)
        path = require_safe_relpath(file_obj["path"], f"{file_label}.path")
        sha = require_hex(file_obj["sha256"], f"{file_label}.sha256", 64)
        size = require_int(file_obj["bytes"], f"{file_label}.bytes", minimum=0)
        files.append({"path": path, "sha256": sha, "bytes": size})
        paths.append(path)

    if paths != sorted(paths):
        raise AdmissionError(f"{label}.files must be sorted lexicographically by path")
    if len(paths) != len(set(paths)):
        raise AdmissionError(f"{label}.files contains duplicate paths")
    if entrypoint not in set(paths):
        raise AdmissionError(f"{label}.entrypoint is absent from the transitive file manifest")

    computed_tree = digest_canonical({"schema_version": SCHEMA_VERSION, "files": files})
    if computed_tree != tree_sha:
        raise AdmissionError(
            f"{label}.tree_sha256 mismatch: declared={tree_sha} computed={computed_tree}"
        )
    return {
        "archive_sha256": archive_sha,
        "archive_bytes": archive_bytes,
        "entrypoint": entrypoint,
        "tree_sha256": tree_sha,
        "files": files,
    }


def scan_root(root: Path, label: str) -> list[dict[str, Any]]:
    try:
        root_mode = root.lstat().st_mode
    except OSError as exc:
        raise AdmissionError(f"cannot stat {label} root {root}: {exc}") from exc
    if stat.S_ISLNK(root_mode):
        raise AdmissionError(f"{label} root may not be a symlink")
    if not stat.S_ISDIR(root_mode):
        raise AdmissionError(f"{label} root is not a directory: {root}")

    records: list[dict[str, Any]] = []
    try:
        descendants = sorted(root.rglob("*"), key=lambda path: path.relative_to(root).as_posix())
    except OSError as exc:
        raise AdmissionError(f"cannot enumerate {label} root {root}: {exc}") from exc

    for path in descendants:
        rel = path.relative_to(root).as_posix()
        try:
            mode = path.lstat().st_mode
        except OSError as exc:
            raise AdmissionError(f"cannot stat {label} member {rel}: {exc}") from exc
        if stat.S_ISLNK(mode):
            raise AdmissionError(f"{label} tree contains a symlink: {rel}")
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise AdmissionError(f"{label} tree contains a non-regular member: {rel}")
        sha, size = file_digest(path)
        records.append({"path": rel, "sha256": sha, "bytes": size})
    return records


def verify_root(root: Path, manifest: Mapping[str, Any], label: str) -> None:
    actual = scan_root(root, label)
    declared = manifest["files"]
    if actual != declared:
        actual_map = {record["path"]: record for record in actual}
        declared_map = {record["path"]: record for record in declared}
        missing = sorted(set(declared_map) - set(actual_map))
        extra = sorted(set(actual_map) - set(declared_map))
        changed = sorted(
            path
            for path in set(actual_map) & set(declared_map)
            if actual_map[path] != declared_map[path]
        )
        raise AdmissionError(
            f"{label} extracted tree does not match its manifest: "
            f"missing={missing} extra={extra} changed={changed}"
        )
    computed_tree = digest_canonical({"schema_version": SCHEMA_VERSION, "files": actual})
    if computed_tree != manifest["tree_sha256"]:
        raise AdmissionError(f"{label} extracted tree digest mismatch")

