# SPDX-License-Identifier: Apache-2.0
"""Build a deterministic playable tarball without mutating the canonical release."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

import build_integrated
from candidate_patch import (
    EXPECTED_SCHEDULER_GIT_BLOB,
    PATCH_SCHEMA_VERSION,
    patch_scheduler_bytes,
)

DEFAULT_OUTPUT = HERE / "dist" / "titan-v3-multi-lot-portfolio.tar.gz"
DEFAULT_RECEIPT = HERE / "dist" / "titan-v3-multi-lot-portfolio.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render() -> tuple[bytes, dict[str, Any]]:
    mapping = build_integrated.source_files()
    blobs = {member: (LAB / source).read_bytes() for member, source in mapping.items()}
    canonical_scheduler = blobs["scheduler.py"]
    blobs["scheduler.py"] = patch_scheduler_bytes(canonical_scheduler)
    blobs["multi_lot_portfolio.py"] = (HERE / "multi_lot_portfolio.py").read_bytes()

    source_paths = dict(mapping)
    source_paths["scheduler.py"] = (
        f"scheduler.py@{EXPECTED_SCHEDULER_GIT_BLOB}+multi-lot-patch-v{PATCH_SCHEMA_VERSION}"
    )
    source_paths["multi_lot_portfolio.py"] = str(
        (HERE / "multi_lot_portfolio.py").relative_to(LAB)
    )

    canonical_manifest = json.loads(
        (LAB / (build_integrated.RECORD + "RELEASE.json")).read_text(encoding="utf-8")
    )
    manifest = dict(canonical_manifest)
    manifest.update(
        entrypoint="main.py::agent",
        config="TITAN-CONFIG.json",
        default=json.loads(blobs["TITAN-CONFIG.json"]),
        candidate={
            "name": "TITAN-V3-MULTI-LOT-PORTFOLIO-20260910-01",
            "patch_schema_version": PATCH_SCHEMA_VERSION,
            "canonical_scheduler_git_blob": EXPECTED_SCHEDULER_GIT_BLOB,
            "canonical_release_mutated": False,
        },
        runtime={
            member: {
                "source_path": source_paths[member],
                "sha256": sha256(data),
                "bytes": len(data),
            }
            for member, data in sorted(blobs.items())
        },
    )
    source_json = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    blobs["SOURCE.json"] = source_json

    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            for member, data in sorted(blobs.items()):
                info = tarfile.TarInfo(member)
                info.size = len(data)
                info.mode = 0o644
                info.mtime = 0
                archive.addfile(info, io.BytesIO(data))
    payload = output.getvalue()
    receipt = {
        "schema_version": 1,
        "candidate": "TITAN-V3-MULTI-LOT-PORTFOLIO-20260910-01",
        "entrypoint": "main.py::agent",
        "config": "TITAN-CONFIG.json",
        "sha256": sha256(payload),
        "bytes": len(payload),
        "runtime_files": len(blobs),
        "source_manifest_sha256": sha256(source_json),
        "canonical_scheduler_git_blob": EXPECTED_SCHEDULER_GIT_BLOB,
        "canonical_release_mutated": False,
    }
    return payload, receipt


def verify_archive(payload: bytes, receipt: dict[str, Any]) -> None:
    if sha256(payload) != receipt["sha256"]:
        raise RuntimeError("archive digest mismatch")
    with gzip.GzipFile(fileobj=io.BytesIO(payload), mode="rb") as compressed:
        with tarfile.open(fileobj=compressed, mode="r:") as archive:
            names = archive.getnames()
            required = {
                "main.py",
                "scheduler.py",
                "multi_lot_portfolio.py",
                "TITAN-CONFIG.json",
                "SOURCE.json",
            }
            missing = sorted(required - set(names))
            if missing:
                raise RuntimeError(f"archive missing required members: {missing}")
            if names != sorted(names) or len(names) != len(set(names)):
                raise RuntimeError("archive member order or uniqueness drift")
            scheduler = archive.extractfile("scheduler.py")
            if scheduler is None:
                raise RuntimeError("scheduler member missing")
            compile(scheduler.read(), "scheduler.py", "exec")
            overlay = archive.extractfile("multi_lot_portfolio.py")
            if overlay is None:
                raise RuntimeError("portfolio member missing")
            compile(overlay.read(), "multi_lot_portfolio.py", "exec")
            source = archive.extractfile("SOURCE.json")
            if source is None:
                raise RuntimeError("source manifest missing")
            manifest = json.loads(source.read())
            if manifest.get("candidate", {}).get("canonical_scheduler_git_blob") != EXPECTED_SCHEDULER_GIT_BLOB:
                raise RuntimeError("source manifest scheduler binding mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    first, receipt = render()
    second, second_receipt = render()
    if first != second or receipt != second_receipt:
        raise RuntimeError("candidate build is not deterministic")
    verify_archive(first, receipt)
    if args.check:
        print(json.dumps(receipt, sort_keys=True))
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(first)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
