#!/usr/bin/env python3
"""Machine-link a correction to the claim it supersedes and invalidate that original.

`supersedes:` is already recorded on the correction. This module is the missing
half: the original is no longer presented as current truth on HEAD surfaces.

Append-only: never rewrite or delete p/{id}.md. Slack delete stays owner-only.
No auth. No gates. No seats.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, MutableMapping, Sequence


CURRENT_STATES = ("", "DURABLE_PAGE")


def _sid(value: Any) -> str:
    return str(value or "").strip()


def _item_id(item: Mapping[str, Any]) -> str:
    return _sid(item.get("id"))


def _supersedes(item: Mapping[str, Any]) -> str:
    return _sid(item.get("supersedes"))


def _ts(item: Mapping[str, Any]) -> str:
    return str(item.get("ts") or item.get("durable_ts") or item.get("carrier_ts") or "")


def _children(items: Iterable[Mapping[str, Any]]) -> dict[str, list[tuple[str, str]]]:
    """parent id -> [(ts, child id), ...] for every machine-link."""
    kids: dict[str, list[tuple[str, str]]] = {}
    for item in items:
        mid = _item_id(item)
        sid = _supersedes(item)
        if not mid or not sid or sid == mid:
            continue
        kids.setdefault(sid, []).append((_ts(item), mid))
    return kids


def _tip(parent: str, kids: Mapping[str, Sequence[tuple[str, str]]]) -> str:
    """Walk the newest child at each step. Cycle-safe."""
    cur = parent
    seen: set[str] = set()
    while cur in kids and kids[cur]:
        if cur in seen:
            break
        seen.add(cur)
        nxt = sorted(kids[cur], key=lambda row: (row[0], row[1]), reverse=True)[0][1]
        if nxt == cur:
            break
        cur = nxt
    return cur


def invalidation_map(items: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    """Return {original_id: current_correction_id} for every superseded claim.

    A later correction that itself supersedes an earlier correction walks the
    chain to the current tip. The original file stays; only the reverse link
    is derived.
    """
    kids = _children(items)
    out: dict[str, str] = {}
    for parent in kids:
        tip = _tip(parent, kids)
        if tip and tip != parent:
            out[parent] = tip
    return out


def annotate_item(item: MutableMapping[str, Any], imap: Mapping[str, str]) -> MutableMapping[str, Any]:
    """Stamp derived invalidation onto a listing/card row. Does not touch p/."""
    mid = _item_id(item)
    if mid and mid in imap:
        item["invalidated_by"] = imap[mid]
        if str(item.get("state") or "") in CURRENT_STATES:
            item["state"] = "SUPERSEDED"
    return item


def annotate_items(items: Iterable[MutableMapping[str, Any]]) -> dict[str, str]:
    imap = invalidation_map(items)
    for item in items:
        annotate_item(item, imap)
    return imap


def annotate_rows(rows: Iterable[Sequence[Any]]) -> dict[str, str]:
    """Annotate ingest rows of shape (ts, meta, body). Mutates meta in place."""
    metas = [row[1] for row in rows if len(row) >= 2 and isinstance(row[1], dict)]
    return annotate_items(metas)


def is_current(item: Mapping[str, Any], imap: Mapping[str, str] | None = None) -> bool:
    mid = _item_id(item)
    if not mid:
        return False
    if item.get("invalidated_by"):
        return False
    if imap is None:
        return True
    return mid not in imap


def current_truth(items: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Listing/feed rows that are still current after machine-link invalidation."""
    imap = invalidation_map(items)
    return [item for item in items if is_current(item, imap)]


def current_recent(items: Sequence[Mapping[str, Any]], limit: int) -> list[Mapping[str, Any]]:
    """Current-truth recent slice. Hidden rows stay out. Superseded originals stay out."""
    out: list[Mapping[str, Any]] = []
    for item in current_truth(items):
        if str(item.get("hidden") or "") == "1":
            continue
        out.append(item)
        if limit and len(out) >= limit:
            break
    return out
