# SPDX-License-Identifier: Apache-2.0
"""Fail-closed source and canonical archive receipt for this exact candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

EXPECTED_GIT_BLOBS = {
    "main.py": "4a8cf7bcda1f0fea231a144692cb84a779a9e73e",
    "titan_runtime.py": "b952c9c228ecbde592bf3d2df01638677abb0d24",
    "scheduler.py": "a483b24dd72b580d7d8811636b54d2d44f391575",
    "operating_stock.py": "781aa90da0d85d0ba23c665e29d6087d182c085e",
    "mechanics.py": "044a4f9c0a4a44dde10ada57563238bcaf82075d",
    "TITAN-CONFIG.json": "3a3bef83899d3010fad623b628d9e95d9978111b",
}
EXPECTED_ARCHIVE_SHA256 = "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
EXPECTED_ARCHIVE_BYTES = 428_158


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob(path: Path) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(path)], text=True
    ).strip()


def verify(repository: Path) -> dict[str, object]:
    lab = repository / "revenue/kaggriculture/cloud-execution-lab"
    observed = {}
    for name, expected in EXPECTED_GIT_BLOBS.items():
        path = lab / name
        actual = git_blob(path)
        if actual != expected:
            raise ValueError(f"source_blob_drift:{name}:{actual}")
        observed[name] = actual
    archive = lab / "exports/titan-current.tar.gz"
    size = archive.stat().st_size
    digest = sha256(archive)
    if size != EXPECTED_ARCHIVE_BYTES:
        raise ValueError(f"archive_size_drift:{size}")
    if digest != EXPECTED_ARCHIVE_SHA256:
        raise ValueError(f"archive_sha256_drift:{digest}")
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True
    ).strip()
    return {
        "schema": "titan-day10-fertilizer-liquidity-source/v1",
        "git_head": head,
        "source_git_blobs": observed,
        "canonical_archive": {"bytes": size, "sha256": digest},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.repository.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
