#!/usr/bin/env python3
"""List every tracked HTML document a phone cannot read.

A document without ``<meta name="viewport">`` renders at a desktop width on
phones.  This checker inventories HTML from git rather than from a shallow
filesystem glob, so deep paths and old generated pages cannot disappear from
the census.  Untracked scratch files are intentionally outside repository
truth.

Run: python3 viewport_check.py
"""

from __future__ import annotations

import subprocess
import sys
from typing import List


NEEDLE = 'name="viewport"'


class GitInventoryError(RuntimeError):
    """The tracked HTML inventory could not be read."""


def _bounded_diagnostic(text: str, limit: int = 240) -> str:
    detail = " ".join(text.split())
    if not detail:
        return "no diagnostic"
    if len(detail) <= limit:
        return detail
    return detail[: limit - 3] + "..."


def tracked_pages() -> List[str]:
    """Return every tracked ``.html`` path, at any depth, deterministically."""
    done = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.html"],
        capture_output=True,
        check=False,
    )
    if done.returncode != 0:
        raw = done.stderr or done.stdout
        detail = _bounded_diagnostic(raw.decode("utf-8", errors="replace"))
        raise GitInventoryError(
            "git ls-files failed with exit %d: %s" % (done.returncode, detail)
        )
    return sorted(
        path.decode("utf-8", errors="surrogateescape")
        for path in done.stdout.split(b"\0")
        if path
    )


def main() -> int:
    try:
        pages = tracked_pages()
    except GitInventoryError as exc:
        print("viewport census: INVENTORY FAILED: %s" % exc, file=sys.stderr)
        return 2

    bad, ok, skipped = [], 0, 0
    for path in pages:
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read(4096)
        except OSError as exc:
            bad.append("%s (unreadable: %s)" % (path, exc))
            continue

        # Some tracked receipts carry an .html suffix but are plain text.  A
        # viewport tag in one would be corruption, so only documents count.
        if text.lstrip()[:1] != "<":
            skipped += 1
            continue
        if NEEDLE in text:
            ok += 1
        else:
            bad.append(path)

    for path in bad:
        print("NO VIEWPORT: %s" % path)
    checked = ok + len(bad)
    print(
        "%d tracked HTML documents checked, %d missing viewport, %d non-documents skipped"
        % (checked, len(bad), skipped)
    )
    if bad:
        print(
            "Generated pages need the fix in the generator, not the file: "
            "hub_pages.VIEWPORT is the constant, and board_ingest.py / "
            "builds_ledger.py carry their own head literals."
        )
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
