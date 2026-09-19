"""Read-only resolution of cited artifacts.

The work order requires that "every cited artifact opens and its version is
identifiable". That is a verifiable claim, so this module verifies it: it opens
each cited path, reads the bytes, and records size + sha256 + the declared
version label. It never writes, never renames, never deletes. The only
filesystem calls in here are existence checks and reads -- a property the test
suite asserts against this module's own AST.

A path that does not open becomes UNRESOLVED. It does not become a zero-byte
delivered file, and it does not quietly drop out of the index.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import Any

from schema import UNKNOWN, IndexItem

READ_CHUNK = 65536

# Resolution outcomes. Only RESOLVED counts as "the artifact opens".
RESOLVED = "RESOLVED"
UNRESOLVED_MISSING = "UNRESOLVED_MISSING"
UNRESOLVED_NOT_A_FILE = "UNRESOLVED_NOT_A_FILE"
UNRESOLVED_UNREADABLE = "UNRESOLVED_UNREADABLE"
UNRESOLVED_OUTSIDE_ROOT = "UNRESOLVED_OUTSIDE_ROOT"


@dataclass
class Resolution:
    item_id: str
    path: str
    state: str
    size_bytes: Any = UNKNOWN
    sha256: Any = UNKNOWN
    declared_version: Any = UNKNOWN
    detail: str = ""

    @property
    def opens(self) -> bool:
        return self.state == RESOLVED

    @property
    def version_identifiable(self) -> bool:
        """Both halves are required.

        A content digest alone tells you two copies differ but not which one the
        client was sent; a declared label alone is just a string somebody typed.
        The pair is what makes a delivered version identifiable after the fact.
        """
        return self.opens and self.declared_version is not UNKNOWN

    def to_json(self) -> dict:
        return {
            "item_id": self.item_id,
            "path": self.path,
            "state": self.state,
            "size_bytes": None if self.size_bytes is UNKNOWN else self.size_bytes,
            "sha256": None if self.sha256 is UNKNOWN else self.sha256,
            "declared_version": None
            if self.declared_version is UNKNOWN
            else self.declared_version,
            "version_identifiable": self.version_identifiable,
            "detail": self.detail,
        }


def _inside(root: str, candidate: str) -> bool:
    """Reject traversal out of the artifact root.

    A packet definition is data, and data supplied by whoever assembled it must
    not be able to point the resolver at /etc/shadow just because it opens.
    """
    root_abs = os.path.realpath(root)
    cand_abs = os.path.realpath(candidate)
    return cand_abs == root_abs or cand_abs.startswith(root_abs + os.sep)


def resolve_item(item: IndexItem, artifact_root: str) -> Resolution:
    joined = os.path.join(artifact_root, item.path)
    if not _inside(artifact_root, joined):
        return Resolution(
            item.item_id, item.path, UNRESOLVED_OUTSIDE_ROOT,
            declared_version=item.declared_version,
            detail="cited path escapes the artifact root; refused without reading",
        )
    if not os.path.exists(joined):
        return Resolution(
            item.item_id, item.path, UNRESOLVED_MISSING,
            declared_version=item.declared_version,
            detail="no file at the cited path; the citation cannot be verified",
        )
    if not os.path.isfile(joined):
        return Resolution(
            item.item_id, item.path, UNRESOLVED_NOT_A_FILE,
            declared_version=item.declared_version,
            detail="cited path is not a regular file",
        )
    digest = hashlib.sha256()
    size = 0
    try:
        with open(joined, "rb") as fh:          # read-only, always
            while True:
                chunk = fh.read(READ_CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        return Resolution(
            item.item_id, item.path, UNRESOLVED_UNREADABLE,
            declared_version=item.declared_version,
            detail=f"cited path exists but could not be read: {exc.__class__.__name__}",
        )
    return Resolution(
        item.item_id, item.path, RESOLVED,
        size_bytes=size, sha256=digest.hexdigest(),
        declared_version=item.declared_version,
        detail="opened and digested",
    )


def resolve_all(engagement, artifact_root: str) -> dict:
    """item_id -> Resolution, across every milestone. Deterministic order."""
    out = {}
    for ms in engagement.milestones:
        for item in ms.index_items:
            out[item.item_id] = resolve_item(item, artifact_root)
    return out
