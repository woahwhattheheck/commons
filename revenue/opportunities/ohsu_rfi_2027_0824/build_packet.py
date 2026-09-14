#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from ohsu_ap_rfi import canonical_json, render_markdown, strict_load, validate_manifest


def exclusive_write(path: Path, data: bytes) -> None:
    if path.is_symlink():
        raise RuntimeError(f"refusing symlink output: {path}")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    finally:
        os.close(fd)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("manifest")
    p.add_argument("--as-of", required=True)
    p.add_argument("--json-out", required=True)
    p.add_argument("--md-out", required=True)
    args = p.parse_args()
    manifest_path = Path(args.manifest).resolve()
    manifest = strict_load(manifest_path)
    carrier_root = manifest_path.parent.parent
    packet = validate_manifest(manifest, args.as_of, local_root=carrier_root)
    exclusive_write(Path(args.json_out), canonical_json(packet))
    exclusive_write(Path(args.md_out), render_markdown(packet).encode("utf-8"))
    print(packet["receipt_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
