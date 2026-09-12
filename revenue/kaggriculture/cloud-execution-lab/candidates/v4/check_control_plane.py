#!/usr/bin/env python3
"""Strict byte/custody preflight for the sole canonical TITAN V4 control plane.

This wrapper does not replace the existing composition/integration validators. It
first rejects ambiguous control bytes and trust-path tricks, snapshots the exact
validator sources and strict ledger inputs used by this run, then delegates to
the existing validators without reopening those ledger trust bytes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import tempfile
import types
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_FILES = ("CANONICAL.json", "INTEGRATION.json", "COMPOSITION.json")
GIT_BLOB_ID = re.compile(r"git-blob:[0-9a-f]{40}\Z")
RELATION_FIELDS = ("requires", "before", "after", "conflicts")
DECLARED_PATH_FIELDS = ("receipt", "composition_receipt")
DELEGATE_FILES = ("check_integration_ledger.py", "check_composition_graph.py")


class ControlPlaneError(ValueError):
    pass


def _object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ControlPlaneError(f"duplicate object key {key!r}")
        out[key] = value
    return out


def _reject_constant(token: str) -> Any:
    raise ControlPlaneError(f"non-finite JSON constant {token!r}")


def _read_regular_bytes(path: Path, label: str) -> bytes:
    if path.is_symlink():
        raise ControlPlaneError(f"{label} must not be a symlink")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ControlPlaneError(f"cannot open {label}: {exc}") from exc
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise ControlPlaneError(f"{label} must be a regular file")
        with os.fdopen(fd, "rb") as stream:
            fd = -1
            return stream.read()
    finally:
        if fd >= 0:
            os.close(fd)


def strict_load(path: Path) -> dict[str, Any]:
    raw = _read_regular_bytes(path, path.name)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ControlPlaneError(f"{path.name} is not UTF-8: {exc}") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_no_duplicates,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, ControlPlaneError) as exc:
        raise ControlPlaneError(f"{path.name} invalid JSON: {exc}") from exc
    if type(value) is not dict:
        raise ControlPlaneError(f"{path.name} must contain one JSON object")
    return value


def _safe_relpath(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    p = PurePosixPath(value)
    return not p.is_absolute() and "." not in p.parts and ".." not in p.parts


def _symlink_prefix(root: Path, rel: str) -> str | None:
    cur = root
    for part in PurePosixPath(rel).parts:
        cur = cur / part
        if cur.is_symlink():
            try:
                return cur.relative_to(root).as_posix()
            except ValueError:
                return str(cur)
    return None


def _check_trust_path(
    root: Path,
    rel: Any,
    label: str,
    errors: list[str],
    *,
    require_file: bool = False,
) -> None:
    if not _safe_relpath(rel):
        errors.append(f"{label}: unsafe relative path {rel!r}")
        return
    assert isinstance(rel, str)
    symlink = _symlink_prefix(root, rel)
    if symlink is not None:
        errors.append(f"{label}: symlink ancestry is forbidden at {symlink!r}")
        return
    if require_file:
        target = root / PurePosixPath(rel)
        if not target.is_file():
            errors.append(f"{label}: declared file is missing at {rel!r}")


def _duplicate_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def _walk_identity_fields(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in {"input_identity", "output_identity"}:
                if not isinstance(child, str) or GIT_BLOB_ID.fullmatch(child) is None:
                    errors.append(
                        f"COMPOSITION identity {child_path}: expected git-blob:<40 lowercase hex>, got {child!r}"
                    )
            _walk_identity_fields(child, child_path, errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_identity_fields(child, f"{path}[{index}]", errors)


def _harden_composition(root: Path, composition: dict[str, Any], errors: list[str]) -> None:
    components = composition.get("components")
    if isinstance(components, list):
        for index, component in enumerate(components):
            if not isinstance(component, dict):
                continue
            cid = component.get("id")
            label = cid if isinstance(cid, str) and cid else f"index:{index}"

            if "package" in component:
                _check_trust_path(root, component.get("package"), f"component {label} package", errors)
            entrypoints = component.get("entrypoints")
            if isinstance(entrypoints, list):
                for ep_index, entrypoint in enumerate(entrypoints):
                    _check_trust_path(
                        root,
                        entrypoint,
                        f"component {label} entrypoint[{ep_index}]",
                        errors,
                    )

            for field in DECLARED_PATH_FIELDS:
                if field in component:
                    _check_trust_path(
                        root,
                        component.get(field),
                        f"component {label} {field}",
                        errors,
                        require_file=True,
                    )

            for field in RELATION_FIELDS:
                values = component.get(field)
                if isinstance(values, list) and all(isinstance(v, str) for v in values):
                    for duplicate in _duplicate_values(values):
                        errors.append(
                            f"component {label} {field}: duplicate relation target {duplicate!r}"
                        )

    discovery = composition.get("discovery")
    if isinstance(discovery, dict):
        roots = discovery.get("roots")
        if isinstance(roots, list):
            for index, scan_root in enumerate(roots):
                _check_trust_path(root, scan_root, f"discovery roots[{index}]", errors)
        ignore = discovery.get("ignore")
        if isinstance(ignore, list):
            for index, item in enumerate(ignore):
                path = item.get("path") if isinstance(item, dict) else item
                if isinstance(path, str):
                    _check_trust_path(root, path, f"discovery ignore[{index}]", errors)

    _walk_identity_fields(composition, "", errors)


def _harden_integration(
    root: Path,
    integration: dict[str, Any],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    manifest_snapshots: dict[str, dict[str, Any]] = {}
    blocked = integration.get("custody_blocked")
    if not isinstance(blocked, list):
        return manifest_snapshots
    for index, row in enumerate(blocked):
        if not isinstance(row, dict):
            continue
        lane = row.get("lane")
        label = lane if isinstance(lane, str) and lane else f"index:{index}"
        custody_path = row.get("custody_path")
        _check_trust_path(root, custody_path, f"custody {label}", errors)
        if row.get("status") != "awaiting_raw_payload" or not _safe_relpath(custody_path):
            continue
        assert isinstance(custody_path, str)
        manifest_rel = (PurePosixPath(custody_path) / "MANIFEST.json").as_posix()
        _check_trust_path(root, manifest_rel, f"custody {label} manifest", errors, require_file=True)
        if any(item.startswith(f"custody {label} manifest:") for item in errors):
            continue
        try:
            manifest_snapshots[manifest_rel] = strict_load(root / PurePosixPath(manifest_rel))
        except ControlPlaneError as exc:
            errors.append(f"custody {label} manifest: {exc}")
    return manifest_snapshots


def _read_regular_utf8(path: Path) -> str:
    raw = _read_regular_bytes(path, f"validator module {path.name}")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ControlPlaneError(f"validator module {path.name} is not UTF-8: {exc}") from exc


def _load_module_snapshot(path: Path, module_name: str):
    source = _read_regular_utf8(path)
    try:
        code = compile(source, str(path), "exec")
    except (SyntaxError, ValueError) as exc:
        raise ControlPlaneError(f"cannot compile validator module {path.name}: {exc}") from exc
    module = types.ModuleType(module_name)
    module.__file__ = str(path)
    module.__package__ = None
    exec(code, module.__dict__, module.__dict__)
    return module


def _dump_snapshot(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _populate_integration_snapshot(
    live_root: Path,
    snapshot_root: Path,
    canonical: dict[str, Any],
    integration: dict[str, Any],
    manifest_snapshots: dict[str, dict[str, Any]],
) -> None:
    _dump_snapshot(snapshot_root / "CANONICAL.json", canonical)
    _dump_snapshot(snapshot_root / "INTEGRATION.json", integration)

    blocked = integration.get("custody_blocked")
    if isinstance(blocked, list):
        for row in blocked:
            if not isinstance(row, dict):
                continue
            custody_path = row.get("custody_path")
            if not _safe_relpath(custody_path):
                continue
            assert isinstance(custody_path, str)
            live_path = live_root / PurePosixPath(custody_path)
            if live_path.is_dir():
                (snapshot_root / PurePosixPath(custody_path)).mkdir(parents=True, exist_ok=True)

    for manifest_rel, manifest in manifest_snapshots.items():
        _dump_snapshot(snapshot_root / PurePosixPath(manifest_rel), manifest)


def _delegate(
    root: Path,
    canonical: dict[str, Any],
    integration: dict[str, Any],
    composition: dict[str, Any],
    manifest_snapshots: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    try:
        ledger = _load_module_snapshot(
            root / DELEGATE_FILES[0],
            "_titan_v4_integration_validator",
        )
        graph = _load_module_snapshot(
            root / DELEGATE_FILES[1],
            "_titan_v4_composition_validator",
        )
    except Exception as exc:
        errors.append(f"delegate load failure: {type(exc).__name__}: {exc}")
        return

    try:
        with tempfile.TemporaryDirectory(prefix="titan-v4-ledger-snapshot-") as td:
            snapshot_root = Path(td)
            _populate_integration_snapshot(
                root,
                snapshot_root,
                canonical,
                integration,
                manifest_snapshots,
            )
            ledger_errors = ledger.validate(snapshot_root)
    except Exception as exc:
        errors.append(f"integration delegate failure: {type(exc).__name__}: {exc}")
    else:
        if not isinstance(ledger_errors, list):
            errors.append("integration delegate returned non-list errors")
        else:
            errors.extend(f"integration: {item}" for item in ledger_errors)

    try:
        graph_result = graph.validate_manifest(composition, root)
    except Exception as exc:
        errors.append(f"composition delegate failure: {type(exc).__name__}: {exc}")
    else:
        if not isinstance(graph_result, dict) or not isinstance(graph_result.get("errors"), list):
            errors.append("composition delegate returned malformed result")
        else:
            for item in graph_result["errors"]:
                errors.append(
                    "composition: " + json.dumps(item, sort_keys=True, separators=(",", ":"))
                )


def validate_control_plane(root: Path, *, delegate: bool = True) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []
    loaded: dict[str, dict[str, Any]] = {}

    for name in EXPECTED_FILES:
        try:
            loaded[name] = strict_load(root / name)
        except ControlPlaneError as exc:
            errors.append(str(exc))

    canonical = loaded.get("CANONICAL.json")
    composition = loaded.get("COMPOSITION.json")
    integration = loaded.get("INTEGRATION.json")
    manifest_snapshots: dict[str, dict[str, Any]] = {}
    if composition is not None:
        _harden_composition(root, composition, errors)
    if integration is not None:
        manifest_snapshots = _harden_integration(root, integration, errors)

    if (
        delegate
        and canonical is not None
        and composition is not None
        and integration is not None
        and not errors
    ):
        _delegate(
            root,
            canonical,
            integration,
            composition,
            manifest_snapshots,
            errors,
        )

    errors = sorted(errors)
    return {
        "ok": not errors,
        "delegate": delegate,
        "checked_files": list(EXPECTED_FILES),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-delegate", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    result = validate_control_plane(Path(args.root), delegate=not args.no_delegate)
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print("TITAN V4 control plane OK" if result["ok"] else "TITAN V4 control plane INVALID")
        for error in result["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
