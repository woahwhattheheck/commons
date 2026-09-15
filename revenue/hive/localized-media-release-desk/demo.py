#!/usr/bin/env python3
"""Build a complete fictional/local-only release package from bundled fixtures."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from desk import ReleaseDesk, strict_json_loads


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True, help="new/existing local directory for demo DB + package")
    args = p.parse_args()
    root = Path(__file__).resolve().parent
    work = Path(args.workdir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    db = work / "localized-release.sqlite3"
    package = work / "localized-release-demo.zip"
    if package.exists():
        package.unlink()
    desk = ReleaseDesk(db)
    required = strict_json_loads((root / "demo" / "required.json").read_bytes())
    try:
        desk.create_title("demo-create", "demo-title", str(root / "demo" / "source.txt"), required)
    except Exception as exc:
        if "title already exists" not in str(exc):
            raise
    desk.set_rights_ready("demo-rights", "demo-title", True)
    for locale, territory, filename, reviewer in (
        ("es", "US", "es-US.srt", "reviewer-es"),
        ("fr", "CA", "fr-CA.srt", "reviewer-fr"),
    ):
        result = desk.add_variant(
            f"demo-add-{locale}", "demo-title", locale, territory, "subtitle", str(root / "demo" / filename)
        )
        desk.approve_variant(
            f"demo-approve-{locale}",
            "demo-title",
            locale,
            territory,
            "subtitle",
            reviewer,
            result["revision"],
            result["content_sha256"],
        )
    receipt = desk.export_package("demo-title", package)
    verification = desk.verify_package("demo-title", package)
    print(json.dumps({"status": desk.status("demo-title"), "receipt": receipt, "verification": verification}, indent=2, sort_keys=True))
    return 0 if verification["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
