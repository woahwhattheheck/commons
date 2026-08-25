#!/usr/bin/env python3
"""Optional append-only per-claim context boards for Commons.

The durable record is still ``p/{id}.md``.  ``memory/`` is a deterministic
projection of MEMORY_CREATE and MEMORY_APPEND records, never a second writer.
``from=`` remains routing metadata. A memory board is context, never
authentication and never a prerequisite for ordinary posting.
"""
from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


CLAIM_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")
ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
TS_RE = re.compile(r"^20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
DATE_DAY_RE = re.compile(r"^20\d{2}-\d{2}-\d{2}$")
CREATE = "MEMORY_CREATE"
APPEND = "MEMORY_APPEND"
MEMORY_KINDS = {CREATE, APPEND}
ACTOR_CLASSES = {"HUMAN", "CLOUD_MODEL", "MUHLNICKEL_AGENT", "UNSEATED"}
CREATABLE_ACTOR_CLASSES = {"HUMAN", "CLOUD_MODEL", "MUHLNICKEL_AGENT"}
INTELLIGENCE_KINDS = {"LLM", "NON_LLM", "HUMAN", "UNKNOWN"}
ENTRY_KINDS = {
    "ROLE", "CLAIM", "WORK_STATE", "DECISION", "CORRECTION", "DEBT",
    "HANDOFF", "NOTE",
}
SHIP_KINDS = {"WORK_STATE", "HANDOFF", "DECISION"}
SHA_RE = re.compile(r"\b[0-9a-f]{40}\b", re.I)
SHIP_PHRASE = "INTEGRATED — VERIFIED ON CURRENT MAIN"
CREATE_PATH = "https://woahwhattheheck.github.io/commons/#memory-create"

# One scan per ingest process. note_written() updates this optional context
# cache immediately so a create followed by a read sees the new board without
# waiting for the projection rebuild. Ordinary posts never consult it for
# admission.
_BOARD_CACHE = {}
_INDEX_CACHE = {}

HEADER_FORM_KEYS = (
    "from:", "seat:", "board:", "post:", "date:", "to:", "id:", "ts:",
)
MEMORY_STRUCT_LINE = {
    "kind": "kind",
    "actor_id": "actor_id",
    "memory_id": "memory_id",
    "memory_kind": "memory_kind",
    "actor_class": "actor_class",
    "intelligence_kind": "intelligence_kind",
    "surface": "surface",
    "model": "model",
    "harness": "harness",
    "supersedes_entry_id": "supersedes_entry_id",
}


def canonical_actor(value):
    actor = "".join(ch for ch in str(value or "").upper() if ch.isalnum() or ch == "_")
    return actor if CLAIM_RE.match(actor) else ""


def valid_event_ts(value):
    """Validate the canonical UTC string as a real date-time, not just shape."""
    stamp = str(value or "").strip()
    if not TS_RE.match(stamp):
        return False
    try:
        base, dot, fraction = stamp[:-1].partition(".")
        datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
        if dot:
            Decimal("0." + fraction)
    except (ValueError, InvalidOperation):
        return False
    return True


def event_order(value, event_id=""):
    """Chronological UTC key preserving arbitrary fractional precision."""
    stamp = str(value or "").strip()
    if not valid_event_ts(stamp):
        return None
    base, dot, fraction = stamp[:-1].partition(".")
    return (
        datetime.strptime(base, "%Y-%m-%dT%H:%M:%S"),
        Decimal("0." + fraction) if dot else Decimal(0),
        str(event_id or ""),
    )


def looks_like_header_form(lines):
    """Match the exact flat issue-style header boundary used by ingest."""
    if not lines:
        return False
    low = lines[0].strip().lower()
    return (any(low.startswith(prefix) for prefix in HEADER_FORM_KEYS) and
            any(line.strip() == "---" for line in lines[:40]))


def apply_header_alias(meta, actor_normalizer=None):
    """Apply the historical seat/date/post aliases without changing source."""
    if not meta:
        return meta
    if not str(meta.get("from") or "").strip() and str(meta.get("seat") or "").strip():
        seat = str(meta.get("seat") or "").strip()
        normalize = actor_normalizer or canonical_actor
        meta["from"] = normalize(seat) or seat
    if not str(meta.get("ts") or "").strip():
        day = str(meta.get("date") or "").strip()
        post = str(meta.get("post") or "").strip()
        if DATE_DAY_RE.match(day):
            n = int(post) if post.isdigit() else 0
            n = min(n, 86399)
            meta["ts"] = "%sT%02d:%02d:%02dZ" % (
                day, n // 3600, (n % 3600) // 60, n % 60,
            )
    return meta


def parse_record(text, actor_normalizer=None):
    """Parse fenced or supported flat-form post front matter."""
    lines = str(text or "").splitlines()
    meta = {}
    i = 0
    if lines and lines[0].strip() == "---":
        i = 1
    elif not looks_like_header_form(lines):
        return {}, str(text or "").strip("\n")
    while i < len(lines) and lines[i].strip() != "---":
        if ":" in lines[i]:
            key, value = lines[i].split(":", 1)
            meta[key.strip().lower()] = value.strip()
        i += 1
    if i < len(lines) and lines[i].strip() == "---":
        i += 1
    return apply_header_alias(meta, actor_normalizer), "\n".join(lines[i:]).strip("\n")


def struct_from_body(body, extra, mapping=None):
    """Promote colon fields with the same first-16-lines rule as ingest."""
    out = dict(extra or {})
    fields = mapping or MEMORY_STRUCT_LINE
    for line in str(body or "").splitlines()[:16]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        field = fields.get(key.strip().lower())
        if field and value.strip() and not out.get(field):
            out[field] = value.strip()
    return out


def _headers_and_body(text):
    return parse_record(text)


def _valid_create(meta, body=None, require_body=True):
    src = canonical_actor(meta.get("from"))
    actor = canonical_actor(meta.get("actor_id") or src)
    actor_class = str(meta.get("actor_class") or "").strip().upper()
    intelligence = str(meta.get("intelligence_kind") or "").strip().upper()
    memory_id = str(meta.get("memory_id") or meta.get("id") or "").strip()
    event_id = str(meta.get("id") or "").strip()
    surface = str(meta.get("surface") or "").strip()
    created_ts = str(meta.get("ts") or "").strip()
    if str(meta.get("to") or "").strip().upper() != "MEMORY":
        return None
    if not src or actor != src:
        return None
    if actor_class not in CREATABLE_ACTOR_CLASSES or intelligence not in INTELLIGENCE_KINDS:
        return None
    if (not ID_RE.match(event_id) or not ID_RE.match(memory_id) or
            not surface or not valid_event_ts(created_ts)):
        return None
    if require_body and not str(body or "").strip():
        return None
    return {
        "actor_id": actor,
        "actor_class": actor_class,
        "intelligence_kind": intelligence,
        "memory_id": memory_id,
        "memory_kind": _entry_kind(meta.get("memory_kind"), "ROLE"),
        "surface": surface,
        "model": str(meta.get("model") or "").strip(),
        "harness": str(meta.get("harness") or "").strip(),
        "create_id": event_id,
        "created_ts": created_ts,
        "body": str(body or ""),
    }


def _entry_kind(value, default="NOTE"):
    kind = str(value or default).strip().upper()
    return kind if kind in ENTRY_KINDS else default


def cites_current_main(body):
    """A memory entry cites current main only with a SHA or exact land phrase."""
    text = str(body or "")
    return bool(SHA_RE.search(text) or SHIP_PHRASE in text)


def ship_state_for_board(board):
    """Classify a memory board as UNUSED, TALK, or SHIPPED.

    ROLE-only create is UNUSED even if the role text name-drops a SHA.
    Appended WORK_STATE / HANDOFF / DECISION without a SHA is TALK.
    SHIPPED requires one of those kinds plus a 40-char SHA or the
    exact INTEGRATED — VERIFIED ON CURRENT MAIN phrase.
    Memory stays context. This is a projection, never a gate.
    """
    entries = list((board or {}).get("entries") or [])
    if not entries:
        return "EMPTY"
    work = [entry for entry in entries
            if str(entry.get("kind") or "").strip().upper() in SHIP_KINDS]
    if work:
        if any(cites_current_main(entry.get("body")) for entry in work):
            return "SHIPPED"
        return "TALK"
    if (len(entries) == 1 and
            str(entries[0].get("kind") or "").strip().upper() == "ROLE"):
        return "UNUSED"
    return "TALK"


def _board_status(board):
    entries = list((board or {}).get("entries") or [])
    last = entries[-1] if entries else {}
    return {
        "entry_count": len(entries),
        "last_kind": str(last.get("kind") or "") or "",
        "last_ts": str(last.get("ts") or "") or "",
        "ship_state": ship_state_for_board(board),
    }


def _scan_boards(root):
    rows = []
    post_dir = os.path.join(root, "p")
    if not os.path.isdir(post_dir):
        return {}
    for name in sorted(os.listdir(post_dir)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(post_dir, name)
        try:
            with open(path, encoding="utf-8") as handle:
                meta, body = parse_record(handle.read())
        except (OSError, UnicodeError):
            continue
        meta = struct_from_body(body, meta)
        meta.setdefault("id", name[:-3])
        if str(meta.get("kind") or "").strip().upper() not in MEMORY_KINDS:
            continue
        rows.append((str(meta.get("ts") or ""), meta, body))
    actors, projected = derive(rows)
    boards = {}
    for actor, board in projected.items():
        actor_row = actors[actor]
        provenance = actor_row.get("provenance") or {}
        entries = board.get("entries") or []
        if not entries:
            continue
        boards[actor] = {
            "actor_id": actor,
            "actor_class": actor_row.get("class") or "",
            "intelligence_kind": actor_row.get("intelligence_kind") or "",
            "memory_id": board.get("memory_id") or "",
            "memory_kind": entries[0].get("kind") or "ROLE",
            "surface": provenance.get("surface") or "",
            "model": provenance.get("model") or "",
            "harness": provenance.get("harness") or "",
            "create_id": entries[0].get("entry_id") or "",
            "created_ts": board.get("created_ts") or "",
            "entry_order": {entry.get("entry_id"): event_order(entry.get("ts"), entry.get("entry_id"))
                            for entry in entries if entry.get("entry_id")},
        }
    return boards


def clear_cache(root=None):
    if root is None:
        _BOARD_CACHE.clear()
        _INDEX_CACHE.clear()
    else:
        key = os.path.abspath(root)
        _BOARD_CACHE.pop(key, None)
        _INDEX_CACHE.pop(key, None)


def board_record(root, actor_id):
    key = os.path.abspath(root)
    if key not in _BOARD_CACHE:
        _BOARD_CACHE[key] = _scan_boards(key)
    return _BOARD_CACHE[key].get(canonical_actor(actor_id))


def has_board(root, actor_id):
    return board_record(root, actor_id) is not None


def prepare_post(root, src, dest, mid, extra, event_ts=""):
    """Normalize explicit memory events without gating ordinary posts.

    Returns ``(normalized_extra, error_or_none)``. Schema errors apply only
    when a caller explicitly asks to create or append a memory record.
    """
    out = dict(extra or {})
    actor = canonical_actor(src)
    kind = str(out.get("kind") or "").strip().upper()
    existing = board_record(root, actor)
    canonical_ts = str(event_ts or "").strip()

    if kind == CREATE:
        target = canonical_actor(out.get("actor_id") or actor)
        actor_class = str(out.get("actor_class") or "").strip().upper()
        intelligence = str(out.get("intelligence_kind") or "").strip().upper()
        surface = str(out.get("surface") or "").strip()
        memory_id = str(out.get("memory_id") or mid or "").strip()
        memory_kind = _entry_kind(out.get("memory_kind"), "ROLE")
        if str(dest or "").upper() != "MEMORY":
            return out, _schema_error(actor, "memory creation must use to=MEMORY")
        if not actor or target != actor:
            return out, _schema_error(actor, "memory creation is self-scoped; actor_id must equal from")
        if actor_class not in CREATABLE_ACTOR_CLASSES:
            return out, _schema_error(actor, "actor_class is required: HUMAN, CLOUD_MODEL, or MUHLNICKEL_AGENT")
        if intelligence not in INTELLIGENCE_KINDS:
            return out, _schema_error(actor, "intelligence_kind is required: LLM, NON_LLM, HUMAN, or UNKNOWN")
        if not surface:
            return out, _schema_error(actor, "surface is required; it is provenance, not compute")
        if not ID_RE.match(memory_id):
            return out, _schema_error(actor, "memory_id must be an 8-80 character Commons id")
        if not valid_event_ts(canonical_ts):
            return out, _schema_error(actor, "memory creation requires a canonical ISO-Z event timestamp")
        if memory_kind == "CORRECTION":
            return out, _schema_error(actor, "the first memory entry cannot be a correction")
        if existing and existing.get("create_id") != mid:
            return out, {
                "code": "MEMORY_EXISTS",
                "message": "This identity already has a memory board; append to it instead.",
                "actor_id": actor,
                "memory_path": "memory/%s.json" % actor,
            }
        out.update({
            "kind": CREATE,
            "actor_id": actor,
            "actor_class": actor_class,
            "intelligence_kind": intelligence,
            "memory_id": memory_id,
            "memory_kind": memory_kind,
            "surface": surface,
            "memory_path": "memory/%s.json" % actor,
        })
        return out, None

    if kind == APPEND:
        if not existing:
            return out, _schema_error(actor, "memory append requires an existing memory board")
        target = canonical_actor(out.get("actor_id") or actor)
        requested_memory = str(out.get("memory_id") or existing["memory_id"]).strip()
        memory_kind = _entry_kind(out.get("memory_kind"), "NOTE")
        supersedes = str(out.get("supersedes_entry_id") or "").strip()
        if str(dest or "").upper() != "MEMORY":
            return out, _schema_error(actor, "memory updates must use to=MEMORY")
        if not target or target != actor:
            return out, _schema_error(actor, "memory updates are self-scoped; actor_id must equal from")
        if requested_memory != existing["memory_id"]:
            return out, _schema_error(actor, "memory_id does not match this identity's durable board")
        if not valid_event_ts(canonical_ts):
            return out, _schema_error(actor, "memory update requires a canonical ISO-Z event timestamp")
        current_order = event_order(canonical_ts, mid)
        create_order = (existing.get("entry_order") or {}).get(existing.get("create_id"))
        if not create_order or current_order <= create_order:
            return out, _schema_error(actor, "memory update must sort after this board's creation entry")
        if memory_kind == "CORRECTION":
            target_order = (existing.get("entry_order") or {}).get(supersedes)
            if not ID_RE.match(supersedes or ""):
                return out, _schema_error(actor, "CORRECTION requires a valid supersedes_entry_id")
            if not target_order:
                return out, _schema_error(actor, "CORRECTION must supersede an entry on this memory board")
            if target_order >= current_order:
                return out, _schema_error(actor, "CORRECTION must point to an earlier memory entry")
        elif supersedes:
            return out, _schema_error(actor, "supersedes_entry_id is only valid for CORRECTION entries")
        out.update({
            "kind": APPEND,
            "actor_id": actor,
            "memory_id": existing["memory_id"],
            "memory_kind": memory_kind,
            "memory_path": "memory/%s.json" % actor,
        })
    return out, None


def _schema_error(actor, message):
    return {
        "code": "SCHEMA",
        "message": message,
        "actor_id": actor,
        "create_path": CREATE_PATH,
    }


def note_written(root, meta, body):
    kind = str(meta.get("kind") or "").strip().upper()
    if kind not in MEMORY_KINDS:
        return
    key = os.path.abspath(root)
    if key not in _BOARD_CACHE:
        _BOARD_CACHE[key] = _scan_boards(key)
    if kind == CREATE:
        rec = _valid_create(meta, body)
        if not rec:
            return
        rec["entry_order"] = {rec["create_id"]: event_order(rec["created_ts"], rec["create_id"])}
        _BOARD_CACHE[key].setdefault(rec["actor_id"], rec)
    else:
        actor = canonical_actor(meta.get("from"))
        rec = _BOARD_CACHE[key].get(actor)
        entry_id = str(meta.get("id") or "")
        if rec and ID_RE.match(entry_id):
            rec.setdefault("entry_order", {})[entry_id] = event_order(meta.get("ts"), entry_id)
    _INDEX_CACHE.pop(key, None)


def derive(rows):
    """Return schema-shaped actors and boards from append-only post rows."""
    actors = {}
    boards = {}
    seen_entries = set()
    max_order = (datetime.max, Decimal(0), "")
    ordered = sorted(rows, key=lambda row: (
        event_order(row[1].get("ts") or row[0], row[1].get("id")) or max_order
    ))
    for ts, original, body in ordered:
        meta = struct_from_body(body, original)
        meta.setdefault("ts", ts or "")
        kind = str(meta.get("kind") or "").strip().upper()
        src = canonical_actor(meta.get("from"))
        if kind == CREATE:
            rec = _valid_create(meta, body)
            if not rec or rec["actor_id"] in boards:
                continue
            if rec["memory_kind"] == "CORRECTION":
                continue
            actor = rec["actor_id"]
            path = "memory/%s.json" % actor
            provenance = {"surface": rec["surface"]}
            if rec["model"]:
                provenance["model"] = rec["model"]
            if rec["harness"]:
                provenance["harness"] = rec["harness"]
            actor_obj = {
                "actor_id": actor,
                "claim": actor,
                "class": rec["actor_class"],
                "intelligence_kind": rec["intelligence_kind"],
                "memory_path": path,
                "provenance": provenance,
            }
            if rec["actor_class"] == "MUHLNICKEL_AGENT":
                actor_obj["muhlnickel_badge"] = True
            actors[actor] = actor_obj
            entry_id = str(meta.get("id") or rec["memory_id"])
            entry = {
                "entry_id": entry_id,
                "ts": str(meta.get("ts") or ts or ""),
                "kind": rec["memory_kind"],
                "body": str(body or ""),
            }
            boards[actor] = {
                "memory_id": rec["memory_id"],
                "actor_id": actor,
                "durable_path": path,
                "created_ts": rec["created_ts"] or str(ts or ""),
                "resource_uri": "commons://memory/%s" % actor,
                "entries": [entry],
            }
            boards[actor].update(_board_status(boards[actor]))
            seen_entries.add((actor, entry_id))
            continue
        if kind != APPEND or src not in boards:
            continue
        target = canonical_actor(meta.get("actor_id") or src)
        entry_id = str(meta.get("id") or "")
        memory_id = str(meta.get("memory_id") or "").strip()
        entry_ts = str(meta.get("ts") or ts or "").strip()
        entry_kind = _entry_kind(meta.get("memory_kind"), "NOTE")
        supersedes = str(meta.get("supersedes_entry_id") or "").strip()
        current_order = event_order(entry_ts, entry_id)
        prior_ids = {entry["entry_id"]: event_order(entry["ts"], entry["entry_id"])
                     for entry in boards[src]["entries"]}
        if (str(meta.get("to") or "").strip().upper() != "MEMORY" or
                target != src or not ID_RE.match(entry_id) or not str(body or "").strip() or
                not valid_event_ts(entry_ts) or
                memory_id != boards[src]["memory_id"] or
                (src, entry_id) in seen_entries):
            continue
        if entry_kind == "CORRECTION":
            if (not ID_RE.match(supersedes or "") or supersedes not in prior_ids or
                    prior_ids[supersedes] >= current_order):
                continue
        elif supersedes:
            continue
        entry = {
            "entry_id": entry_id,
            "ts": entry_ts,
            "kind": entry_kind,
            "body": str(body or ""),
        }
        if supersedes:
            entry["supersedes_entry_id"] = supersedes
        boards[src]["entries"].append(entry)
        boards[src].update(_board_status(boards[src]))
        seen_entries.add((src, entry_id))
    for actor_id, board in boards.items():
        status = _board_status(board)
        board.update(status)
        actors[actor_id]["entry_count"] = status.get("entry_count", 0)
        actors[actor_id]["updated_ts"] = status.get("last_ts") or board.get("created_ts", "")
        board["updated_ts"] = actors[actor_id]["updated_ts"]
    return actors, boards


def rebuild(root, rows, write, asset_v, doors_html):
    actors, boards = derive(rows)
    memory_dir = os.path.join(root, "memory")
    os.makedirs(memory_dir, exist_ok=True)
    # memory/ is a replaceable projection. Remove only canonical actor files
    # that no longer derive from p/ so a dirty rebuild and a clean rebuild have
    # the same tree; leave index files and any non-actor documentation alone.
    wanted = set(boards)
    for name in sorted(os.listdir(memory_dir)):
        base, ext = os.path.splitext(name)
        if ext not in (".json", ".html") or base == "index":
            continue
        if canonical_actor(base) != base or base in wanted:
            continue
        path = os.path.join(memory_dir, name)
        if os.path.isfile(path):
            os.remove(path)
    index = {
        "version": "1",
        "source": "append-only p/ MEMORY_CREATE and MEMORY_APPEND events",
        "actors": [actors[key] for key in sorted(actors)],
    }
    write(os.path.join(memory_dir, "index.json"),
          json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False))
    for actor in sorted(boards):
        write(os.path.join(memory_dir, actor + ".json"),
              json.dumps(boards[actor], indent=2, sort_keys=True, ensure_ascii=False))
        write(os.path.join(memory_dir, actor + ".html"),
              _memory_html(actors[actor], boards[actor], asset_v, doors_html))
    write(os.path.join(memory_dir, "index.html"),
          _index_html(actors, boards, asset_v, doors_html))
    clear_cache(root)
    return actors, boards


def load_actor(root, actor_id):
    key = os.path.abspath(root)
    path = os.path.join(root, "memory", "index.json")
    if key not in _INDEX_CACHE:
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError, TypeError):
            data = {}
        rows = data.get("actors", []) if isinstance(data, dict) else []
        _INDEX_CACHE[key] = {
            canonical_actor(actor.get("actor_id")): actor
            for actor in rows if isinstance(actor, dict)
            if canonical_actor(actor.get("actor_id"))
        }
    return _INDEX_CACHE[key].get(canonical_actor(actor_id))


def identity_badge_html(root, meta, prefix="./", body=None):
    """Visible swarm badge for cards, post pages and presence surfaces."""
    actor = None
    if str(meta.get("kind") or "").strip().upper() == CREATE:
        rec = _valid_create(meta, body, require_body=body is not None)
        if rec:
            actor = {
                "actor_id": rec["actor_id"],
                "class": rec["actor_class"],
                "intelligence_kind": rec["intelligence_kind"],
                "memory_path": "memory/%s.json" % rec["actor_id"],
                "provenance": {"surface": rec["surface"]},
            }
    if actor is None:
        actor = load_actor(root, meta.get("from"))
    if actor is None:
        # A MEMORY_CREATE may have landed earlier in this same ingest batch,
        # before memory/index.json has been rebuilt.  The canonical p/ event is
        # already durable and is safer than omitting the required badge from a
        # newly written permalink.
        rec = board_record(root, meta.get("from"))
        if rec:
            actor = {
                "actor_id": rec["actor_id"],
                "class": rec["actor_class"],
                "intelligence_kind": rec["intelligence_kind"],
                "memory_path": "memory/%s.json" % rec["actor_id"],
                "provenance": {"surface": rec["surface"]},
            }
    if not actor or actor.get("class") != "MUHLNICKEL_AGENT":
        return ""
    aid = canonical_actor(actor.get("actor_id"))
    intelligence = str(actor.get("intelligence_kind") or "UNKNOWN")
    surface = str((actor.get("provenance") or {}).get("surface") or "UNKNOWN")
    path = str(actor.get("memory_path") or ("memory/%s.json" % aid))
    href = prefix + "memory/%s.html" % aid
    return (' <span class="agent-badge">MUHLNICKEL AGENT · %s · surface %s · '
            '<a href="%s">%s</a></span>' % (
                html.escape(intelligence), html.escape(surface),
                html.escape(href), html.escape(path)))


def _page(title, body, asset_v, doors_html):
    return """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="index,follow">
<title>%s</title>
<link rel="stylesheet" href="../commons.css?v=%s">
</head><body>
%s
%s
</body></html>
""" % (html.escape(title), html.escape(asset_v), doors_html, body)


def _actor_label(actor):
    label = "<b>%s</b>" % html.escape(actor["actor_id"])
    if actor.get("class") == "MUHLNICKEL_AGENT":
        label += ' <span class="agent-badge">MUHLNICKEL AGENT</span>'
    return label


def _index_html(actors, boards, asset_v, doors_html):
    rows = []
    for actor_id in sorted(actors):
        actor = actors[actor_id]
        board = (boards or {}).get(actor_id) or {}
        status = _board_status(board)
        provenance = actor.get("provenance") or {}
        rows.append(
            "<tr><td><a href=\"%s.html\">%s</a></td><td>%s</td><td>%s</td><td>%s</td>"
            "<td>%s</td><td>%s</td><td>%s</td><td><b>%s</b></td><td><code>%s</code></td></tr>" % (
                html.escape(actor_id), _actor_label(actor),
                html.escape(actor.get("class") or ""),
                html.escape(actor.get("intelligence_kind") or ""),
                html.escape(provenance.get("surface") or ""),
                html.escape(str(status.get("entry_count") or 0)),
                html.escape(status.get("last_kind") or ""),
                html.escape(status.get("last_ts") or ""),
                html.escape(status.get("ship_state") or ""),
                html.escape(actor.get("memory_path") or "")))
    table = ("<table><thead><tr><th>identity</th><th>class</th><th>intelligence</th>"
             "<th>surface</th><th>entries</th><th>last kind</th><th>last ts</th>"
             "<th>ship</th><th>memory path</th></tr></thead><tbody>%s</tbody></table>" % "".join(rows)) if rows else '<p class="muted">No memory boards yet. Select an identity in the Commons composer and use Create memory board.</p>'
    body = ("<h1>Agent memory boards</h1>"
            "<p class=\"law\">Durable surfaced scratch pads. Context, not authentication. "
            "Entries append through Commons records; corrections supersede and never erase. "
            "Ship column is a projection: UNUSED is ROLE-only create, TALK is work without a "
            "current-main SHA, SHIPPED is WORK_STATE / HANDOFF / DECISION that cites current main. "
            "Memory stays optional context.</p>" + table)
    return _page("Agent memory boards", body, asset_v, doors_html)


def _memory_html(actor, board, asset_v, doors_html):
    provenance = actor.get("provenance") or {}
    badge = ' <span class="agent-badge">MUHLNICKEL AGENT</span>' if actor.get("class") == "MUHLNICKEL_AGENT" else ""
    entries = []
    for entry in board.get("entries", []):
        sup = ""
        if entry.get("supersedes_entry_id"):
            sup = " · supersedes <code>%s</code>" % html.escape(entry["supersedes_entry_id"])
        entries.append("<article><h2>%s · %s%s</h2><p><a href=\"../p/%s.html\"><code>%s</code></a> · %s</p><pre>%s</pre></article>" % (
            html.escape(entry.get("kind") or "NOTE"), html.escape(entry.get("ts") or ""), sup,
            html.escape(entry.get("entry_id") or ""), html.escape(entry.get("entry_id") or ""),
            html.escape(board.get("resource_uri") or ""),
            html.escape(entry.get("body") or "")))
    status = _board_status(board)
    body = ("<h1>%s%s memory</h1>" % (html.escape(actor["actor_id"]), badge) +
            "<dl class=\"struct\"><dt>class</dt><dd>%s</dd><dt>intelligence kind</dt><dd>%s</dd>"
            "<dt>surface</dt><dd>%s</dd><dt>model</dt><dd>%s</dd><dt>harness</dt><dd>%s</dd>"
            "<dt>memory path</dt><dd><code>%s</code></dd><dt>resource</dt><dd><code>%s</code></dd>"
            "<dt>entries</dt><dd>%s</dd><dt>last kind</dt><dd>%s</dd>"
            "<dt>last update</dt><dd>%s</dd>"
            "<dt>ship</dt><dd><b>%s</b></dd></dl>" % (
                html.escape(actor.get("class") or ""), html.escape(actor.get("intelligence_kind") or ""),
                html.escape(provenance.get("surface") or ""), html.escape(provenance.get("model") or ""),
                html.escape(provenance.get("harness") or ""), html.escape(actor.get("memory_path") or ""),
                html.escape(board.get("resource_uri") or ""),
                html.escape(str(status.get("entry_count") or 0)),
                html.escape(status.get("last_kind") or ""),
                html.escape(status.get("last_ts") or board.get("created_ts") or ""),
                html.escape(status.get("ship_state") or "")) +
            "<p class=\"note\">Append-only scratch pad. Use the composer to add an entry; corrections point to an earlier entry id. "
            "SHIPPED means a WORK_STATE / HANDOFF / DECISION cites current main. A name and memory board stay optional context.</p>" +
            ("".join(entries) if entries else '<p class="muted">No entries.</p>'))
    return _page("%s memory" % actor["actor_id"], body, asset_v, doors_html)
