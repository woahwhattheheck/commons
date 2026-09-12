#!/usr/bin/env python3
"""Authenticate the exact current-runtime CLOCKWORK seam and WEAVE inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


class AuditError(ValueError):
    pass


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load_pins(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != "titan-v4-clockwork-pins-v1":
        raise AuditError("unsupported or missing pins schema")
    files = raw.get("git_blobs")
    if not isinstance(files, dict) or not files:
        raise AuditError("pins must contain nonempty git_blobs")
    return raw


def audit_source_root(root: Path, pins_path: Path) -> dict[str, Any]:
    root = root.resolve()
    pins = load_pins(pins_path)
    observed: dict[str, str] = {}
    mismatches = []
    for rel, expected in sorted(pins["git_blobs"].items()):
        if not isinstance(rel, str) or not rel or rel.startswith("/") or ".." in Path(rel).parts:
            raise AuditError(f"unsafe pinned path {rel!r}")
        if not isinstance(expected, str) or len(expected) != 40:
            raise AuditError(f"invalid expected Git blob for {rel}")
        path = (root / rel).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise AuditError(f"pinned path escapes root: {rel}") from exc
        if not path.is_file() or path.is_symlink():
            mismatches.append({"path": rel, "expected": expected, "observed": None})
            continue
        actual = git_blob_sha1(path.read_bytes())
        observed[rel] = actual
        if actual != expected:
            mismatches.append({"path": rel, "expected": expected, "observed": actual})

    semantic = pins.get("semantic_markers", {})
    marker_failures = []
    for rel, markers in sorted(semantic.items()):
        path = root / rel
        if not path.is_file():
            marker_failures.append({"path": rel, "marker": "<file-missing>"})
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                marker_failures.append({"path": rel, "marker": marker})

    return {
        "schema": "titan-v4-clockwork-source-audit-v1",
        "passed": not mismatches and not marker_failures,
        "source_root": str(root),
        "canonical_branch": pins.get("canonical_branch"),
        "observed_git_blobs": observed,
        "blob_mismatches": mismatches,
        "semantic_marker_failures": marker_failures,
        "weave_output_git_blob": pins.get("weave_output_git_blob"),
        "cutpoint": pins.get("cutpoint"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True,
                        help="cloud-execution-lab source root containing main.py")
    parser.add_argument("--pins", type=Path, default=Path(__file__).with_name("CLOCKWORK-PINS.json"))
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    try:
        receipt = audit_source_root(args.source_root, args.pins)
    except (OSError, json.JSONDecodeError, AuditError) as exc:
        receipt = {"schema": "titan-v4-clockwork-source-audit-v1", "passed": False, "error": str(exc)}
    text = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    if args.json:
        args.json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if receipt.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
