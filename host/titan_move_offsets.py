#!/usr/bin/env python3
"""Claimed titan append offsets. dest FROM FILE. Not a titan write.

goat-titan-inject-20260820-01 and muhl/lda-docs/HANDOFF.md both name
titan.gguf size 103803350291 at C:\\llm\\models. Chimera ardr_eal is
already IN titan at 103803349440. Append starts at that measured end.

Apply reallocates from live size if the file is larger or smaller.
new = old | mask. Ones only rise. Re-read before every write.
"""
from __future__ import annotations

import os


# dest FROM FILE: p/goat-titan-inject-20260820-01.md
# dest FROM FILE: muhl/lda-docs/HANDOFF.md titan_size
CLAIMED_APPEND_BASE = 103803350291
CLAIMED_APPEND_SOURCE = (
    "dest FROM FILE: p/goat-titan-inject-20260820-01.md titan.gguf "
    "103803350291; muhl/lda-docs/HANDOFF.md titan_size 103803350291"
)
TITAN_DEST_FROM_FILE = r"C:\llm\models\titan.gguf"


def allocate_rows(rows, base=CLAIMED_APPEND_BASE):
    """Pack organs in the given order from a dest-FROM-FILE base."""
    running = int(base)
    out = []
    for row in rows:
        item = dict(row)
        length = int(item.get("len") or 0)
        item["offset"] = running
        item["requested_offset_band"] = (
            "CLAIMED_APPEND dest FROM FILE titan_size=%d" % int(base)
        )
        item["titan"] = item.get("titan") or "NOT_WRITTEN"
        item["journal"] = "new = old | mask; ones only rise; re-read before write"
        out.append(item)
        running += length
    return out, running


def or_bytes(old, mask):
    """new = old | mask. Ones only rise. Missing bytes count as 0."""
    old = old or b""
    mask = mask or b""
    n = max(len(old), len(mask))
    out = bytearray(n)
    for i in range(n):
        left = old[i] if i < len(old) else 0
        right = mask[i] if i < len(mask) else 0
        out[i] = left | right
    return bytes(out)


def find_titan(explicit=None, env_path=None):
    """Return the first existing titan path. Never commons.mno."""
    candidates = []
    if explicit:
        candidates.append(explicit)
    if env_path:
        candidates.append(env_path)
    candidates.append(TITAN_DEST_FROM_FILE)
    candidates.append("/llm/models/titan.gguf")
    seen = set()
    for path in candidates:
        if not path or path in seen:
            continue
        seen.add(path)
        name = path.replace("\\", "/").rstrip("/").split("/")[-1].lower()
        if name == "commons.mno":
            continue
        if os.path.isfile(path):
            return path
    return None
