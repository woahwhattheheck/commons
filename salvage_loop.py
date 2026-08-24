#!/usr/bin/env python3
"""Deterministically recover complete, schema-repairable failed-lane payloads.

The failed record is evidence and is never edited or deleted here.  A repair is
allowed only when ``rejects.json`` retained the complete raw carrier payload.
Truncated body snippets, conflicts, empty posts and push failures stay failed.
The canonical board writer remains the only writer of ``p/`` records.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
from datetime import datetime, timezone


SKIP_REASONS = {"PUSH_FAIL", "empty", "bad-from", "bad-to"}
RECEIPT_PATH = os.path.join("salvage", "receipts.json")


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default
    return value


def _dump(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def source_key(row):
    stable = {
        "id": row.get("id") or "",
        "event_id": row.get("event_id") or "",
        "ts": row.get("ts") or "",
        "reason": row.get("reason") or row.get("code") or "",
        "raw": row.get("raw") or "",
    }
    packed = json.dumps(stable, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()


def _object_from_text(raw, board):
    text = str(raw or "").strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    candidates = [text]
    if "\\n" in text and "\n" not in text:
        candidates.append(text.replace("\\r\\n", "\n").replace("\\n", "\n"))
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            value = None
        if isinstance(value, dict):
            return value, "json"
        try:
            value = ast.literal_eval(candidate)
        except (SyntaxError, ValueError):
            value = None
        if isinstance(value, dict) and all(isinstance(k, str) for k in value):
            return value, "python-literal"
        value = board.ntfy_envelope(candidate)
        if isinstance(value, dict):
            return value, "record"
    return None, ""


def repair(row, board):
    """Return a canonical envelope, or ``None`` when recovery is lossy."""
    state = str(row.get("state") or "")
    reason = str(row.get("reason") or row.get("code") or "")
    raw = row.get("raw")
    if state in {"QUARANTINED_CONFLICT", "PUSH_FAIL"} or reason in SKIP_REASONS:
        return None
    # ``body`` on reject rows is deliberately a 400-byte diagnostic excerpt.
    # It is never reconstructive input.
    if not isinstance(raw, str) or not raw.strip():
        return None
    obj, parser = _object_from_text(raw, board)
    if not obj:
        return None
    while isinstance(obj.get("payload"), dict):
        obj = obj["payload"]
    body = obj.get("body")
    if body is None:
        body = obj.get("content")
    if body is None:
        body = obj.get("message")
    if not isinstance(body, str) or not body.strip():
        return None
    src = board.as_from(str(obj.get("from") or row.get("from") or "")) or "UNSEATED"
    dest = board.as_to(str(obj.get("to") or row.get("to") or "")) or "TABLE"
    raw_id = str(obj.get("id") or row.get("id") or "").strip()
    ident, _was = board.slug_id(raw_id)
    if not ident or ident.startswith("unparseable-"):
        ident = "salvage-" + source_key(row)[:16]
    extra = {
        "kind": "SALVAGED_POST",
        "carrier": "salvage-loop",
        "observed_event": "salvage:" + source_key(row)[:24],
        "reason": reason or "MALFORMED_ENVELOPE",
    }
    for key in board.META_KEYS:
        if key in {"from", "to", "id", "ts", "state", "body"}:
            continue
        if obj.get(key) not in (None, ""):
            extra[key] = obj[key]
    if raw_id and raw_id != ident and board.ID_OK.match(raw_id):
        extra["supersedes"] = raw_id
    return {
        "from": src,
        "to": dest,
        "id": ident,
        "body": body.strip(),
        "ts": str(obj.get("ts") or row.get("ts") or ""),
        "extra": extra,
        "parser": parser,
    }


def sweep(root, board, limit=20):
    rejects = _load(os.path.join(root, "rejects.json"), [])
    receipt_file = os.path.join(root, RECEIPT_PATH)
    receipts = _load(receipt_file, [])
    if not isinstance(rejects, list):
        rejects = []
    if not isinstance(receipts, list):
        receipts = []
    seen = {str(r.get("source_sha256") or "") for r in receipts if isinstance(r, dict)}
    added = []
    for row in rejects:
        if len(added) >= max(0, int(limit)):
            break
        if not isinstance(row, dict):
            continue
        key = source_key(row)
        if key in seen:
            continue
        env = repair(row, board)
        if not env:
            continue
        page = os.path.join(root, "p", env["id"] + ".md")
        if os.path.isfile(page):
            status = "ALREADY_DURABLE"
        else:
            status = board.write_post(
                env["from"], env["to"], env["id"], env["body"],
                ts=env["ts"] or None, extra=env["extra"],
                event_id="salvage-" + key[:24],
            )
        if status not in {"wrote", "unchanged", "exists", "ALREADY_DURABLE"}:
            continue
        receipt = {
            "source_sha256": key,
            "source_id": row.get("id") or "",
            "source_state": row.get("state") or "INGEST_ERROR",
            "source_reason": row.get("reason") or row.get("code") or "",
            "source_raw": row.get("raw") or "",
            "repaired_id": env["id"],
            "parser": env["parser"],
            "status": status,
        }
        # Preserve the exact failed carrier bytes before the ordinary rebuild
        # prunes a reject whose repaired page has become durable.
        receipts.append(receipt)
        added.append(receipt)
        seen.add(key)
    if added:
        _dump(receipt_file, receipts[-500:])
    return added


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=os.path.dirname(os.path.abspath(__file__)))
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    import board_ingest
    rows = sweep(os.path.abspath(args.root), board_ingest, args.limit)
    print(json.dumps({"salvaged": len(rows), "receipts": rows}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
