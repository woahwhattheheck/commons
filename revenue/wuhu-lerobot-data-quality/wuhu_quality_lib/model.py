"""Strict JSON, safe path, and immutable-output helpers."""

from __future__ import annotations

import json
import os
import string
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from . import core as _previous
from .core import *


class _ObjectPairs(dict[str, Any]):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        obj[key] = value
    return obj


def _reject_constant(token: str) -> None:
    raise QualityError(f"non-finite JSON token is not permitted: {token}")


def load_json_strict(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise QualityError(f"cannot read UTF-8 JSON {path}: {exc}") from exc
    try:
        return json.loads(text, object_pairs_hook=_strict_object, parse_constant=_reject_constant)
    except (json.JSONDecodeError, DuplicateKeyError, QualityError) as exc:
        raise QualityError(f"invalid JSON {path}: {exc}") from exc


def load_jsonl_strict(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise QualityError(f"cannot read UTF-8 JSONL {path}: {exc}") from exc
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line, object_pairs_hook=_strict_object, parse_constant=_reject_constant)
        except (json.JSONDecodeError, DuplicateKeyError, QualityError) as exc:
            raise QualityError(f"invalid JSONL {path}:{line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise QualityError(f"JSONL row must be an object: {path}:{line_number}")
        rows.append(value)
    return rows


def _ensure_positive_int(value: Any, label: str) -> int:
    if not _is_int(value) or value <= 0:
        raise QualityError(f"{label} must be a positive integer")
    return value


def _ensure_nonnegative_int(value: Any, label: str) -> int:
    if not _is_int(value) or value < 0:
        raise QualityError(f"{label} must be a non-negative integer")
    return value


def _relative_posix(value: str, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise QualityError(f"{label} must be a non-empty string")
    if "\\" in value or chr(0) in value:
        raise QualityError(f"{label} must use a safe POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise QualityError(f"{label} escapes or ambiguously addresses the dataset root: {value!r}")
    return path


def safe_dataset_path(root: Path, relative: str, label: str = "dataset path") -> Path:
    rel = _relative_posix(relative, label)
    root_real = root.resolve(strict=True)
    current = root_real
    for part in rel.parts:
        current = current / part
        try:
            current.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise QualityError(f"cannot inspect {label} component {current}: {exc}") from exc
        if current.is_symlink():
            raise QualityError(f"{label} traverses a symbolic link: {current}")
        if current != root_real / Path(*rel.parts) and not current.is_dir():
            raise QualityError(f"{label} parent is not a directory: {current}")
    try:
        current.resolve(strict=False).relative_to(root_real)
    except ValueError as exc:
        raise QualityError(f"{label} resolves outside the dataset root: {relative}") from exc
    return current


def render_template(template: Any, *, episode_index: int, episode_chunk: int, video_key: str | None = None) -> str:
    if not isinstance(template, str) or not template:
        raise QualityError("path template must be a non-empty string")
    values: dict[str, Any] = {"episode_index": episode_index, "episode_chunk": episode_chunk}
    if video_key is not None:
        values["video_key"] = video_key
    formatter = string.Formatter()
    for _, field_name, format_spec, conversion in formatter.parse(template):
        if field_name is None:
            continue
        if field_name not in values:
            raise QualityError(f"unsupported path-template field: {field_name}")
        if conversion:
            raise QualityError("path-template conversions are not permitted")
        if format_spec and not (format_spec.endswith("d") and format_spec[:-1].replace("0", "").isdigit()):
            raise QualityError(f"unsupported path-template format: {format_spec}")
    try:
        rendered = template.format(**values)
    except (KeyError, ValueError, TypeError) as exc:
        raise QualityError(f"cannot render path template {template!r}: {exc}") from exc
    return _relative_posix(rendered, "rendered path template").as_posix()


def _optional_nonnegative_int(value: Any, label: str) -> int | None:
    if value is None:
        return None
    if not _is_int(value) or value < 0:
        raise QualityError(f"{label} must be a non-negative integer or null")
    return value


def _optional_finite(value: Any, label: str) -> float | None:
    if value is None:
        return None
    number = _finite_number(value)
    if number is None:
        raise QualityError(f"{label} must be finite or null")
    return number


def _optional_ratio(value: Any, label: str) -> float | None:
    result = _optional_finite(value, label)
    if result is not None and not 0 <= result <= 1:
        raise QualityError(f"{label} must be in [0, 1]")
    return result


def _output_inside_dataset(dataset_root: Path, out_dir: Path) -> bool:
    dataset = dataset_root.expanduser().resolve(strict=True)
    target = out_dir.expanduser().resolve(strict=False)
    try:
        target.relative_to(dataset)
    except ValueError:
        return False
    return True


def prepare_output_dir(dataset_root: Path, out_dir: Path) -> Path:
    if _output_inside_dataset(dataset_root, out_dir):
        raise QualityError("output directory must be outside the immutable dataset root")
    absolute = out_dir.expanduser().absolute()
    current = Path(absolute.anchor) if absolute.is_absolute() else Path.cwd()
    parts = absolute.parts[1:] if absolute.is_absolute() else absolute.parts
    for part in parts:
        current = current / part
        try:
            current.lstat()
        except FileNotFoundError:
            try:
                current.mkdir()
            except OSError as exc:
                raise QualityError(f"cannot create output directory component {current}: {exc}") from exc
        except OSError as exc:
            raise QualityError(f"cannot inspect output directory component {current}: {exc}") from exc
        if current.is_symlink() or not current.is_dir():
            raise QualityError(f"output directory chain must contain real directories: {current}")
    return absolute.resolve(strict=True)


def _atomic_write(path: Path, content: bytes) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


__all__ = [
    *_previous.__all__,
    "_ObjectPairs",
    "_strict_object",
    "_reject_constant",
    "load_json_strict",
    "load_jsonl_strict",
    "_ensure_positive_int",
    "_ensure_nonnegative_int",
    "_relative_posix",
    "safe_dataset_path",
    "render_template",
    "_optional_nonnegative_int",
    "_optional_finite",
    "_optional_ratio",
    "_output_inside_dataset",
    "prepare_output_dir",
    "_atomic_write",
]
