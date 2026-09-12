#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the canonical immutable TITAN V5 candidate-identity manifest.

This is an evidence-only producer. It reads source/configuration bytes once,
hashes those exact bytes, encodes activation values with type preservation, and
emits the closed ``titan-v5-candidate-identity/v1`` shape consumed by
``promotion_gate.py``. It never executes candidate code or changes gameplay,
CURRENT pointers, archives, defaults, or Kaggle state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import sys
import uuid
from typing import Any, Mapping

IDENTITY_SCHEMA = "titan-v5-candidate-identity/v1"
SPEC_SCHEMA = "titan-v5-candidate-spec/v1"
_SPEC_KEYS = frozenset(("schema", "base_id", "engine_id", "opponent_pack_id", "components"))
_COMPONENT_KEYS = frozenset(("name", "source", "activation"))


class IdentityError(ValueError):
    """Candidate identity input is malformed, ambiguous, or unsafe."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise IdentityError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_constant(token: str) -> None:
    raise IdentityError(f"non-finite JSON constant is forbidden: {token}")


def _loads_strict(raw: bytes, *, source: str) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IdentityError(f"{source}: input is not UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise IdentityError(f"{source}: invalid JSON: {exc.msg}") from exc


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise IdentityError("value is not canonical-JSON serializable") from exc


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _nonempty_text(value: Any, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise IdentityError(f"{field} must be a non-empty string")
    return value


def _safe_rel(value: Any, field: str) -> str:
    if type(value) is not str or not value or "\\" in value:
        raise IdentityError(f"{field} must be a canonical relative POSIX path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or value == "."
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise IdentityError(f"{field} must be a canonical relative POSIX path")
    return value


def _typed(value: Any, field: str) -> dict[str, Any]:
    """Encode JSON-compatible values without collapsing bool/int/float identity."""
    if value is None:
        return {"t": "none"}
    if type(value) is bool:
        return {"t": "bool", "v": value}
    if type(value) is int:
        return {"t": "int", "v": str(value)}
    if type(value) is float:
        if not math.isfinite(value):
            raise IdentityError(f"{field} contains a non-finite float")
        return {"t": "float", "v": value.hex()}
    if type(value) is str:
        return {"t": "str", "v": value}
    if type(value) is list:
        return {
            "t": "list",
            "v": [_typed(item, f"{field}[{index}]") for index, item in enumerate(value)],
        }
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise IdentityError(f"{field} object keys must be strings")
        return {
            "t": "dict",
            "v": [
                [key, _typed(value[key], f"{field}.{key}")]
                for key in sorted(value)
            ],
        }
    raise IdentityError(f"{field} has unsupported JSON value type {type(value).__name__}")


def _activation(value: Any, field: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise IdentityError(f"{field} must be an object")
    mode = value.get("mode")
    if mode == "unconditional":
        if set(value) != {"mode"}:
            raise IdentityError(f"{field} unconditional activation has noncanonical keys")
        return {"mode": "unconditional"}
    if mode != "config" or set(value) != {"mode", "equals"}:
        raise IdentityError(f"{field} must be canonical unconditional or config activation")
    equals = value["equals"]
    if type(equals) is not dict or not equals:
        raise IdentityError(f"{field}.equals must be a non-empty config mapping")
    reserved = sorted(key for key in equals if type(key) is str and key.startswith("_"))
    if reserved:
        raise IdentityError(f"{field}.equals cannot use reserved metadata keys: {reserved!r}")
    return {"mode": "config", "equals": _typed(equals, f"{field}.equals")}


def _read_repo_source(repo_root: Path, source: str) -> bytes:
    root = repo_root.resolve(strict=True)
    candidate = (root / Path(*PurePosixPath(source).parts)).resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise IdentityError(f"component source escapes repo root: {source}") from exc
    if not candidate.is_file():
        raise IdentityError(f"component source is not a regular file: {source}")
    try:
        return candidate.read_bytes()
    except OSError as exc:
        raise IdentityError(f"cannot read component source: {source}") from exc


def build_manifest(
    spec: Mapping[str, Any],
    *,
    repo_root: Path,
    config_raw: bytes,
) -> dict[str, Any]:
    """Build one deterministic identity manifest from exact source/config bytes."""
    if type(spec) is not dict or set(spec) != _SPEC_KEYS:
        missing = sorted(_SPEC_KEYS - set(spec)) if type(spec) is dict else sorted(_SPEC_KEYS)
        extra = sorted(set(spec) - _SPEC_KEYS) if type(spec) is dict else []
        raise IdentityError(f"candidate spec keys mismatch; missing={missing!r} extra={extra!r}")
    if spec["schema"] != SPEC_SCHEMA:
        raise IdentityError(f"candidate spec schema must be {SPEC_SCHEMA}")
    base_id = _nonempty_text(spec["base_id"], "candidate spec base_id")
    engine_id = _nonempty_text(spec["engine_id"], "candidate spec engine_id")
    opponent_pack_id = spec["opponent_pack_id"]
    if opponent_pack_id is not None:
        opponent_pack_id = _nonempty_text(opponent_pack_id, "candidate spec opponent_pack_id")
    components_spec = spec["components"]
    if type(components_spec) is not list or not components_spec:
        raise IdentityError("candidate spec components must be a non-empty list")

    components: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    seen_sources: set[str] = set()
    for index, component in enumerate(components_spec):
        field = f"candidate spec components[{index}]"
        if type(component) is not dict or set(component) != _COMPONENT_KEYS:
            raise IdentityError(f"{field} must have exact name/source/activation keys")
        name = _nonempty_text(component["name"], f"{field}.name")
        source = _safe_rel(component["source"], f"{field}.source")
        if name in seen_names:
            raise IdentityError(f"duplicate candidate component name: {name}")
        if source in seen_sources:
            raise IdentityError(f"duplicate candidate component source: {source}")
        seen_names.add(name)
        seen_sources.add(source)
        raw = _read_repo_source(repo_root, source)
        components.append(
            {
                "name": name,
                "source": source,
                "source_sha256": _sha(raw),
                "activation": _activation(component["activation"], f"{field}.activation"),
            }
        )
    components.sort(key=lambda item: item["name"])

    body = {
        "schema": IDENTITY_SCHEMA,
        "base_id": base_id,
        "engine_id": engine_id,
        "opponent_pack_id": opponent_pack_id,
        "config_sha256": _sha(config_raw),
        "components": components,
    }
    return {**body, "candidate_id": "v5c:" + _sha(_canonical_bytes(body))}


def _publish(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = -1
    try:
        fd = os.open(temp, flags, 0o644)
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    candidate = sub.add_parser("candidate", help="build a canonical candidate identity manifest")
    candidate.add_argument("spec", type=Path, help=f"strict {SPEC_SCHEMA} JSON spec")
    candidate.add_argument("--repo-root", type=Path, required=True)
    candidate.add_argument("--config", type=Path, required=True, help="exact candidate config bytes")
    candidate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        if args.command != "candidate":
            raise IdentityError("unsupported command")
        spec_raw = args.spec.read_bytes()
        config_raw = args.config.read_bytes()
        spec = _loads_strict(spec_raw, source=str(args.spec))
        manifest = build_manifest(spec, repo_root=args.repo_root, config_raw=config_raw)
        _publish(args.output, manifest)
    except (IdentityError, OSError) as exc:
        print(f"candidate identity error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"candidate_id": manifest["candidate_id"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
