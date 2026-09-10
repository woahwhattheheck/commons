#!/usr/bin/env python3
"""Verify the published TITAN archive without trusting the source checkout."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(message)


def safe_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    names: set[str] = set()
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or not member.isfile():
            fail(f"unsafe or non-regular archive member: {member.name!r}")
        if member.name in names:
            fail(f"duplicate archive member: {member.name}")
        names.add(member.name)
    return members


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    archive_bytes = args.archive.read_bytes()
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    archive_hash = sha256(archive_bytes)
    if archive_hash != receipt.get("sha256"):
        fail("archive hash does not match CURRENT-ARCHIVE.json")
    if len(archive_bytes) != receipt.get("bytes"):
        fail("archive byte count does not match CURRENT-ARCHIVE.json")

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        with tarfile.open(args.archive, mode="r:gz") as archive:
            members = safe_members(archive)
            archive.extractall(root, members=members)
        source_bytes = (root / "SOURCE.json").read_bytes()
        source = json.loads(source_bytes.decode("utf-8"))
        if sha256(source_bytes) != receipt.get("source_manifest_sha256"):
            fail("embedded SOURCE.json hash does not match receipt")
        runtime = source.get("runtime")
        if not isinstance(runtime, dict):
            fail("embedded SOURCE.json runtime is not an object")
        if len(runtime) != receipt.get("runtime_files"):
            fail("embedded runtime member count does not match receipt")
        archive_names = {member.name for member in members}
        expected_names = set(runtime) | {"SOURCE.json"}
        if archive_names != expected_names:
            fail("archive member set differs from SOURCE.json runtime closure")
        for member, metadata in sorted(runtime.items()):
            payload = (root / PurePosixPath(member)).read_bytes()
            if len(payload) != metadata.get("bytes"):
                fail(f"runtime byte count mismatch: {member}")
            if sha256(payload) != metadata.get("sha256"):
                fail(f"runtime hash mismatch: {member}")

        config = json.loads((root / source["config"]).read_text(encoding="utf-8"))
        if config != source.get("default"):
            fail("packaged config differs from SOURCE.json default")

        python_files = sorted(path for path in root.rglob("*.py") if path.is_file())
        for path in python_files:
            compile(path.read_bytes(), str(path), "exec")

        entry_file, entry_symbol = source["entrypoint"].split("::", 1)
        entry_path = root / entry_file
        sys.path.insert(0, str(root))
        try:
            spec = importlib.util.spec_from_file_location("titan_extracted_entrypoint", entry_path)
            if spec is None or spec.loader is None:
                fail("unable to load extracted entrypoint")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if not callable(getattr(module, entry_symbol, None)):
                fail("extracted entrypoint symbol is not callable")
        finally:
            sys.path.remove(str(root))

    report = {
        "status": "pass",
        "archive": str(args.archive),
        "sha256": archive_hash,
        "bytes": len(archive_bytes),
        "archive_members": len(members),
        "runtime_files": len(runtime),
        "source_manifest_sha256": sha256(source_bytes),
        "python_files_compiled": len(python_files),
        "entrypoint": source["entrypoint"],
        "entrypoint_callable": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
