#!/usr/bin/env python3
"""Materialize the exact one-line weed-OFF V2 factor with source closure."""
from __future__ import annotations

import argparse
import hashlib
import json
import py_compile
import shutil
from pathlib import Path

TARGET = Path("spatial_tempo.py")
OLD = "        if self._continue_weed(obs,selected,controller,end):return selected\n"
NEW = "        if (self.pathing or self.tempo) and self._continue_weed(obs,selected,controller,end):return selected\n"
EXPECTED_SOURCE_SHA256 = "1ace1547a0f091ce36de1bbb8e023baa7b9699346968ebbc1468433733dbd50d"
EXPECTED_OUTPUT_SHA256 = "f4f31b62b006b7cf9754e924a9dc80a2e71baa60b504caa6ad352aaea3a33e74"
EXPECTED_BASE_TREE_SHA256 = "98cd13d3c2cc6d16639be4bd932d313bfd6bfd1d084c0183113021ec3dad8ac2"
EXPECTED_OUTPUT_TREE_SHA256 = "18d73e996405a88186922140717e9b39195d476827419ba1477c4308ebe11158"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest(root: Path) -> list[dict[str, object]]:
    rows = []
    for path in sorted((item for item in root.rglob("*") if item.is_file() and
                        "__pycache__" not in item.parts and path_suffix(item) != ".pyc"),
                       key=lambda item: item.relative_to(root).as_posix()):
        data = path.read_bytes()
        rows.append({"path": path.relative_to(root).as_posix(), "sha256": sha256(data), "bytes": len(data)})
    return rows


def path_suffix(path: Path) -> str:
    return path.suffix.lower()


def tree_digest(rows: list[dict[str, object]]) -> str:
    payload = "".join(f'{row["path"]}\0{row["sha256"]}\0{row["bytes"]}\n' for row in rows).encode()
    return sha256(payload)


def patch_text(text: str) -> str:
    if text.count(OLD) != 1:
        raise ValueError(f"expected exactly one weed-continuation anchor, found {text.count(OLD)}")
    result = text.replace(OLD, NEW)
    if OLD in result or result.count(NEW) != 1:
        raise ValueError("weed-OFF postcondition failed")
    return result


def materialize(source: Path, output: Path, *, enforce_exact: bool = True) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(output)
    base_rows = manifest(source)
    base_tree = tree_digest(base_rows)
    target = source / TARGET
    source_bytes = target.read_bytes()
    source_sha = sha256(source_bytes)
    if enforce_exact and (source_sha != EXPECTED_SOURCE_SHA256 or base_tree != EXPECTED_BASE_TREE_SHA256):
        raise ValueError(f"unexpected V2 source identity: target={source_sha}, tree={base_tree}")
    shutil.copytree(source, output)
    patched = patch_text(source_bytes.decode("utf-8")).encode("utf-8")
    (output / TARGET).write_bytes(patched)
    py_compile.compile(str(output / TARGET), doraise=True)
    py_compile.compile(str(output / "titan_runtime.py"), doraise=True)
    output_rows = manifest(output)
    output_tree = tree_digest(output_rows)
    output_sha = sha256(patched)
    before = {row["path"]: row["sha256"] for row in base_rows}
    after = {row["path"]: row["sha256"] for row in output_rows}
    changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    if changed != [TARGET.as_posix()]:
        raise ValueError(f"non-factor source delta: {changed}")
    if enforce_exact and (output_sha != EXPECTED_OUTPUT_SHA256 or output_tree != EXPECTED_OUTPUT_TREE_SHA256):
        raise ValueError(f"unexpected weed-OFF identity: target={output_sha}, tree={output_tree}")
    return {
        "schema_version": 1,
        "operation": "exact one-factor weed continuation OFF materialization",
        "base_tree_sha256": base_tree,
        "output_tree_sha256": output_tree,
        "base_file_count": len(base_rows),
        "output_file_count": len(output_rows),
        "changed_paths": changed,
        "target": TARGET.as_posix(),
        "source_sha256": source_sha,
        "output_sha256": output_sha,
        "old": OLD.rstrip("\n"),
        "new": NEW.rstrip("\n"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--allow-nonexact-fixture", action="store_true", help="Tests only; source closure still enforced")
    args = parser.parse_args()
    receipt = materialize(args.source, args.output, enforce_exact=not args.allow_nonexact_fixture)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
