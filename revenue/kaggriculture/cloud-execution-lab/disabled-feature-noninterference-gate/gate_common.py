"""Shared validation, hashing, and atomic receipt primitives."""
from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = 1
GATE_NAME = "disabled-feature-noninterference"
_VERDICTS = frozenset({"PASS", "BLOCK", "ERROR"})
_DOTTED = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class GateError(ValueError):
    """Raised for malformed, ambiguous, drifting, or unsafe inputs."""


@dataclass(frozen=True, order=True)
class Finding:
    code: str
    line: int
    column: int
    kind: str
    target: str
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "line": self.line,
            "column": self.column,
            "kind": self.kind,
            "target": self.target,
            "detail": self.detail,
        }


def _reject_constant(token: str) -> None:
    raise GateError(f"non-finite JSON constant is forbidden: {token}")


def load_json(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GateError(f"cannot read {path}: {exc}") from exc
    try:
        return json.loads(text, parse_constant=_reject_constant)
    except GateError:
        raise
    except json.JSONDecodeError as exc:
        raise GateError(f"malformed JSON in {path}: {exc}") from exc


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise GateError(f"value is not canonical finite JSON: {exc}") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()  # noqa: S324 - Git object identity


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GateError(f"{label} must be an object")
    return value


def _require_exact_keys(
    value: Mapping[str, Any], *, required: set[str], optional: set[str], label: str
) -> None:
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required - optional)
    if missing:
        raise GateError(f"{label} missing keys: {', '.join(missing)}")
    if unknown:
        raise GateError(f"{label} has unknown keys: {', '.join(unknown)}")


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GateError(f"{label} must be a non-empty string")
    return value


def _require_verdict(value: Any, label: str, *, allow_error: bool = False) -> str:
    verdict = _require_nonempty_string(value, label)
    allowed = _VERDICTS if allow_error else frozenset({"PASS", "BLOCK"})
    if verdict not in allowed:
        raise GateError(f"{label} must be one of {sorted(allowed)}")
    return verdict


def _safe_relative_path(value: Any, label: str) -> str:
    text = _require_nonempty_string(value, label)
    candidate = Path(text)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise GateError(f"{label} must be a repository-relative path without '..'")
    return candidate.as_posix()


def _resolve_under(root: Path, relative: str, label: str) -> Path:
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise GateError(f"{label} escapes repository root") from exc
    return candidate


def _validate_finite_json(value: Any, label: str = "value") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GateError(f"{label} contains a non-finite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_finite_json(item, f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise GateError(f"{label} contains a non-string object key")
            _validate_finite_json(item, f"{label}.{key}")
        return
    raise GateError(f"{label} contains unsupported JSON type {type(value).__name__}")


def _attribute_path(node: ast.AST) -> str | None:
    parts: list[str] = []
    cursor = node
    while isinstance(cursor, ast.Attribute):
        parts.append(cursor.attr)
        cursor = cursor.value
    if isinstance(cursor, ast.Name):
        parts.append(cursor.id)
        return ".".join(reversed(parts))
    return None


def _node_location(node: ast.AST) -> tuple[int, int]:
    return int(getattr(node, "lineno", 0)), int(getattr(node, "col_offset", 0))


def _contains_direct_reference(node: ast.AST, targets: set[str]) -> str | None:
    for child in ast.walk(node):
        path = _attribute_path(child)
        if path in targets:
            return path
    return None


def _same_resolved_path(left: Path, right: Path) -> bool:
    return left.resolve() == right.resolve()


def write_receipt(output: Path, receipt: Mapping[str, Any], protected_inputs: Sequence[Path]) -> None:
    for input_path in protected_inputs:
        if _same_resolved_path(output, input_path):
            raise GateError(f"output path aliases protected input {input_path}")
    payload = canonical_bytes(receipt) + b"\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, output)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise

