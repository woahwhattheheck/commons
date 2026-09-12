#!/usr/bin/env python3
"""Materialize WEAVE into a fresh runtime copy without weakening deadlines.

The input runtime is immutable.  Only selected_sell_core.py may differ in the
output.  The canonical WEAVE composer is source-audited before execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from clockwork_source_audit import AuditError, audit_source_root, git_blob_sha1, load_pins


class StageError(ValueError):
    pass


def _tree_snapshot(root: Path) -> dict[str, tuple[str, str]]:
    root = root.resolve()
    out: dict[str, tuple[str, str]] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise StageError(f"symlink not allowed in runtime: {rel}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise StageError(f"nonregular runtime member: {rel}")
        data = path.read_bytes()
        out[rel] = (hashlib.sha256(data).hexdigest(), git_blob_sha1(data))
    return out


def stage_runtime(
    *, input_runtime: Path, output_runtime: Path, composer: Path,
    expected_input_blob: str, expected_output_blob: str,
    required_unchanged_blobs: dict[str, str] | None = None,
) -> dict:
    src = input_runtime.resolve()
    dst = output_runtime.resolve()
    if not src.is_dir():
        raise StageError("input runtime must be a directory")
    if dst.exists():
        raise StageError("output runtime already exists")
    selected = src / "selected_sell_core.py"
    if not selected.is_file() or selected.is_symlink():
        raise StageError("input runtime lacks regular selected_sell_core.py")
    input_blob = git_blob_sha1(selected.read_bytes())
    if input_blob != expected_input_blob:
        raise StageError(f"selected_sell_core.py predecessor mismatch: {input_blob}")
    before = _tree_snapshot(src)
    required_unchanged_blobs = dict(required_unchanged_blobs or {})
    for rel, expected in sorted(required_unchanged_blobs.items()):
        observed = before.get(rel)
        if observed is None:
            raise StageError(f"required runtime member missing: {rel}")
        if observed[1] != expected:
            raise StageError(f"required runtime member drift: {rel}={observed[1]}")
    if not composer.is_file() or composer.is_symlink():
        raise StageError("composer is missing or not regular")

    dst.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=f".{dst.name}.clockwork-", dir=str(dst.parent)))
    try:
        shutil.rmtree(temp)
        shutil.copytree(src, temp, symlinks=False)
        composed = temp.parent / f".{dst.name}.selected-{os.getpid()}.py"
        if composed.exists():
            composed.unlink()
        proc = subprocess.run(
            [sys.executable, str(composer), str(selected), str(composed)],
            text=True, capture_output=True,
        )
        if proc.returncode != 0:
            raise StageError(f"composer failed rc={proc.returncode}: {proc.stderr.strip()[:400]}")
        if not composed.is_file() or composed.is_symlink():
            raise StageError("composer did not produce a regular selected core")
        output_blob = git_blob_sha1(composed.read_bytes())
        if output_blob != expected_output_blob:
            raise StageError(f"composed selected core mismatch: {output_blob}")
        shutil.move(str(composed), str(temp / "selected_sell_core.py"))
        after = _tree_snapshot(temp)
        if set(before) != set(after):
            raise StageError("runtime membership changed during staging")
        changed = [rel for rel in sorted(before) if before[rel] != after[rel]]
        if changed != ["selected_sell_core.py"]:
            raise StageError(f"unexpected runtime byte changes: {changed}")
        temp.rename(dst)
    except Exception:
        if temp.exists():
            shutil.rmtree(temp, ignore_errors=True)
        raise
    return {
        "schema": "titan-v4-clockwork-stage-v1",
        "passed": True,
        "input_runtime": str(src),
        "output_runtime": str(dst),
        "input_selected_git_blob": input_blob,
        "output_selected_git_blob": expected_output_blob,
        "changed_members": ["selected_sell_core.py"],
        "member_count": len(before),
        "deadline_files_unchanged": sorted(required_unchanged_blobs),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--input-runtime", type=Path, required=True)
    parser.add_argument("--output-runtime", type=Path, required=True)
    parser.add_argument("--pins", type=Path, default=Path(__file__).with_name("CLOCKWORK-PINS.json"))
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    try:
        audit = audit_source_root(args.source_root, args.pins)
        if not audit.get("passed"):
            raise StageError("source audit failed; refuse to compose stale inputs")
        pins = load_pins(args.pins)
        composer = args.source_root / pins["composer_path"]
        receipt = stage_runtime(
            input_runtime=args.input_runtime,
            output_runtime=args.output_runtime,
            composer=composer,
            expected_input_blob=pins["git_blobs"]["selected_sell_core.py"],
            expected_output_blob=pins["weave_output_git_blob"],
            required_unchanged_blobs={
                "main.py": pins["git_blobs"]["main.py"],
                "titan_runtime.py": pins["git_blobs"]["titan_runtime.py"],
            },
        )
        receipt["source_audit"] = audit
    except (OSError, json.JSONDecodeError, AuditError, StageError) as exc:
        receipt = {"schema": "titan-v4-clockwork-stage-v1", "passed": False, "error": str(exc)}
    text = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    if args.json:
        args.json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if receipt.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
