#!/usr/bin/env python3
"""Measure an opaque cloud generation by reconstructing its stored page bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def measure(manifest_path: Path, source_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = manifest_path.parent
    source = source_path.read_bytes()
    pages = sorted(manifest["pages"], key=lambda item: item["index"])

    chunks: list[bytes] = []
    measured_pages: list[dict[str, Any]] = []
    cursor = 0
    for page in pages:
        payload = (root / page["path"]).read_bytes()
        measured = {
            "index": page["index"],
            "declared_byte_start": page["byte_start"],
            "declared_byte_end_exclusive": page["byte_end_exclusive"],
            "measured_bytes": len(payload),
            "measured_sha256": sha256(payload),
            "starts_at_running_cursor": page["byte_start"] == cursor,
            "ends_at_running_cursor": page["byte_end_exclusive"] == cursor + len(payload),
            "matches_declared_bytes": len(payload) == page["bytes"],
            "matches_declared_sha256": sha256(payload) == page["sha256"],
        }
        measured_pages.append(measured)
        chunks.append(payload)
        cursor += len(payload)

    reconstructed = b"".join(chunks)
    record_stride = int(manifest["record"]["stride_bytes"])
    receipt = {
        "format": "MUHLCLOUD1_MEASUREMENT",
        "generation_id": manifest["generation_id"],
        "source_bytes_measured": len(source),
        "source_sha256_measured": sha256(source),
        "reconstructed_bytes_measured": len(reconstructed),
        "reconstructed_sha256_measured": sha256(reconstructed),
        "byte_equal_measured": reconstructed == source,
        "page_count_measured": len(pages),
        "page_bytes_measured": [item["measured_bytes"] for item in measured_pages],
        "coverage_starts_at_zero": bool(pages) and pages[0]["byte_start"] == 0,
        "coverage_ends_at_source_bytes": cursor == len(source),
        "all_page_boundaries_on_record_stride": all(
            page["byte_start"] % record_stride == 0
            and page["byte_end_exclusive"] % record_stride == 0
            for page in pages
        ),
        "pages": measured_pages,
    }
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(measure(args.manifest.resolve(), args.source.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
