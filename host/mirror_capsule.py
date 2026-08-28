# mirror_capsule.py — portable content-addressed Commons snapshot
#
# Own only this module plus mirror-capsule.html, test_mirror_capsule.py,
# and files under mirror-capsule/. Everything else is a read-only input.
#
# Law: git HEAD is canonical. A capsule is a bake. Reachable is not
# canonical. ntfy 200 is mail. p/{id}.md on HEAD is the post.
# Never claim independent hosting or writeback without a live receipt.

from __future__ import annotations

import hashlib
import io
import json
import posixpath
import re
import tarfile
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA = "commons-mirror-capsule-v1"
ENVELOPE_SCHEMA = "commons-envelope-v1"
QUEUE_SCHEMA = "commons-capsule-writeback-queue-v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
CLAIM_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")

MEDIA_TYPES = {
    ".md": "text/markdown; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".json": "application/json",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".woff2": "font/woff2",
}

DEFAULT_SELECTION = (
    "START.md",
    "ENTRY.md",
    "CRAWLERS.md",
    "ISSUE.md",
    "mirrors.json",
    "mirror.html",
    "ground/HEAD.md",
    "ground/OPEN_DOOR.md",
    "ground/EXECUTE.md",
    "ground/LAND.md",
    "relay-manifest.schema.json",
)

CLAIM_BOUNDARY = {
    "portable_snapshot": True,
    "canonical": False,
    "moving_main_sync": False,
    "provider_writeback": False,
    "independent_origin": False,
    "canonical_durability": False,
    "live_hosting": False,
    "reachable_is_not_canonical": True,
}


class CapsuleError(ValueError):
    """Typed capsule failure."""


class PathRejected(CapsuleError):
    """Traversal, symlink, or ambiguous path."""


class HashCorrupt(CapsuleError):
    """Declared hash does not match bytes."""


class AmbiguousSource(CapsuleError):
    """Source SHA missing, malformed, or mixed."""


class ImportState(CapsuleError):
    """Import classified as a typed non-ok state."""

    def __init__(self, state: str, detail: str):
        super().__init__("%s: %s" % (state, detail))
        self.state = state
        self.detail = detail


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: Any) -> bytes:
    return (json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def media_type(path: str) -> str:
    ext = posixpath.splitext(path)[1].lower()
    return MEDIA_TYPES.get(ext, "application/octet-stream")
