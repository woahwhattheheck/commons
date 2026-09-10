#!/usr/bin/env python3
"""Reassemble, verify, safely extract, and optionally test the exact evidence package."""
from __future__ import annotations

import argparse
import base64
import hashlib
from pathlib import Path
import subprocess
import sys
import tarfile

ARCHIVE_SHA256 = "89c89ba44ec0841a04e69bcfaa0d4f5209aaaa9e9847b84eaeac76e2c2cf454d"
ARMOR_SHA256 = "4c387fc243b78da94dba41c1d3efe0360606e62ccbde27052d9b61bd26eb29e4"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(archive, "r:gz") as tf:
        for member in tf.getmembers():
            if member.issym() or member.islnk():
                raise ValueError(f"refusing link member: {member.name}")
            target = (destination / member.name).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"refusing traversal member: {member.name}")
        tf.extractall(destination)


def run(command: list[str], cwd: Path) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".evidence"))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    parts = sorted((here / "bundle").glob("part-*.b64"))
    if not parts:
        raise FileNotFoundError("no bundle/part-*.b64 files")
    armor = b"".join(part.read_bytes() for part in parts)
    if sha256(armor) != ARMOR_SHA256:
        raise ValueError("armored package digest mismatch")
    raw = base64.b64decode(armor, validate=False)
    if sha256(raw) != ARCHIVE_SHA256:
        raise ValueError("archive digest mismatch")

    archive = args.output.with_suffix(".tar.gz")
    archive.write_bytes(raw)
    safe_extract(archive, args.output)
    print(f"verified archive {ARCHIVE_SHA256}; extracted to {args.output}")

    if args.verify:
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], args.output)
        run([sys.executable, "analyze_weed_factor.py",
             "--on-dir", "results/raw/on", "--off-dir", "results/raw/off",
             "--output", "/tmp/weed-factor-replay.json",
             "--expect", "results/weed_factor_64.json"], args.output)
        run([sys.executable, "analyze_capital_firewall.py",
             "--on-dir", "results/raw/on", "--firewall-dir", "results/raw/firewall",
             "--output", "/tmp/firewall-factor-replay.json",
             "--expect", "results/capital_firewall_64.json"], args.output)
        run(["sha256sum", "-c", "SHA256SUMS"], args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
