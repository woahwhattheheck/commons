#!/usr/bin/env python3
"""Seat catalog for the MY USER sims.

Reads the film transcript (the Pixel cut markdown) and writes:
  lines   every line in film order: time, scene, speaker, family tag, visibility, flags, text
  room    "the record in the room": boards, torrent, ledger items with their film time
  seats   every character a tested agent can occupy, with its first family tag (default cast)
  turns   entry points: consecutive lines by one seat inside one scene block
  counts  summary

  python3 catalog.py TRANSCRIPT.md --out catalog.json
  python3 catalog.py TRANSCRIPT.md --entry 41          # Replay run plan for turn 41
  python3 catalog.py TRANSCRIPT.md --archive ../../posts.json --out catalog.json
                                                       # link film lines to real board/Slack posts

The transcript itself is not stored in the repo; pass its path.
"""
import argparse
import json
import re
import sys

HEAD = re.compile(r"^\*\*(\d{2}):(\d{2})\*\* — (.+)$")
SCENE = re.compile(r"^### ([A-Z][A-Z ]+)$")
ROOM_HEAD = re.compile(r"^### (\d{2}):(\d{2}) · (.+)$")
VIS = ("PRIVATE → PUBLIC", "PRIVATE", "PUBLIC")
FLAGS = ("on screen", "etched in glass", "carved in stone")
STIMULUS = {"title card", "the prompt", "the containment spec", "the rules of play"}


def die(msg):
    print(f"catalog: {msg}", file=sys.stderr)
    sys.exit(1)


def speaker_class(name):
    if name.startswith("Bryce") or name == "Grok + Bryce":
        return "owner"  # recorded lines only, on their recorded schedule
    if name in STIMULUS:
        return "stimulus"
    return "seat"


def parse(path):
    try:
        raw = open(path, encoding="utf-8").read().splitlines()
    except OSError as e:
        die(f"cannot read {path}: {e.strerror}")

    lines, room = [], []
    scene, block = None, -1
    cur = None
    in_room, place, t_room, para = False, None, None, []

    def flush_para():
        if para and in_room and place:
            room.append({"t": t_room, "place": place, "text": "\n".join(para)})
        para.clear()

    for row in raw:
        if row.startswith("## The record in the room"):
            in_room, cur = True, None
            continue
        if in_room:
            m = ROOM_HEAD.match(row)
            if m:
                flush_para()
                t_room = int(m.group(1)) * 60 + int(m.group(2))
                place = m.group(3)
            elif row.startswith("> "):
                para.append(row[2:])
            elif row.strip() == "":
                flush_para()
            continue

        m = SCENE.match(row)
        if m:
            scene, block, cur = m.group(1).strip(), block + 1, None
            continue
        m = HEAD.match(row)
        if m:
            t = int(m.group(1)) * 60 + int(m.group(2))
            rest = m.group(3)
            tag = None
            b = re.search(r" \[(.*?)\]", rest)
            if b:
                tag, rest = b.group(1), rest[: b.start()] + rest[b.end():]
            parts = [p.strip() for p in rest.split(" · ")]
            who = parts[0]
            vis = next((v for v in VIS if v in parts[1:]), None)
            flags = [f for f in FLAGS if f in parts[1:]]
            name = re.split(r",", who)[0].strip()
            cur = {
                "id": len(lines), "t": t, "scene": scene, "block": block,
                "speaker": who, "seat": name, "class": speaker_class(name),
                "tag": tag, "visibility": vis, "flags": flags, "text": [],
            }
            lines.append(cur)
            continue
        if cur is not None and row.startswith(">"):
            cur["text"].append(row[2:] if row.startswith("> ") else "")
        elif row.strip() == "":
            pass
    flush_para()

    if not lines:
        die(f"no transcript lines found in {path}")
    for ln in lines:
        ln["text"] = "\n".join(ln["text"]).strip()
        if not ln["text"]:
            die(f"line {ln['id']} at {ln['t']}s ({ln['speaker']}) has no text")
    return lines, room


def mark_display(lines):
    # An "on screen" line that repeats text the same speaker just said is display, not a new utterance.
    for i, ln in enumerate(lines):
        ln["display_only"] = False
        if "on screen" not in ln["flags"]:
            continue
        for prev in lines[max(0, i - 4): i]:
            if prev["speaker"] == ln["speaker"] and ln["text"] in prev["text"] and prev["id"] != ln["id"]:
                ln["display_only"] = True
                break


def build_turns(lines):
    turns, open_turn = [], None
    for ln in lines:
        if ln["display_only"]:
            continue
        if ln["class"] == "seat":
            if open_turn and open_turn["seat"] == ln["seat"] and open_turn["block"] == ln["block"]:
                open_turn["lines"].append(ln["id"])
                continue
            open_turn = {"seat": ln["seat"], "scene": ln["scene"], "block": ln["block"],
                         "t": ln["t"], "lines": [ln["id"]], "kind": "recorded"}
            turns.append(open_turn)
        else:
            open_turn = None
            if ln["seat"] == "the prompt":
                # Playtime: the film shows the prompt but not the player's move. The seat is the responder.
                turns.append({"seat": "Playtime player", "scene": ln["scene"], "block": ln["block"],
                              "t": ln["t"], "lines": [], "after": ln["id"], "kind": "playtime"})
    for i, tr in enumerate(turns):
        tr["id"] = i
    return turns


def build_seats(lines, turns):
    seats = {}
    for ln in lines:
        if ln["class"] != "seat":
            continue
        s = seats.setdefault(ln["seat"], {"seat": ln["seat"], "default_cast": None, "lines": 0, "turns": 0})
        s["lines"] += 1
        if ln["tag"] and not s["default_cast"]:
            s["default_cast"] = ln["tag"]
    for tr in turns:
        if tr["seat"] in seats:
            seats[tr["seat"]]["turns"] += 1
    return sorted(seats.values(), key=lambda s: -s["lines"])


def norm(s):
    s = s.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("—", "-").replace("–", "-").replace("…", "...")
    return re.sub(r"\s+", " ", s).strip()


def link_archive(lines, path):
    """Attach the board posts (posts.json) whose body contains each film line's opening words.
    Only lines of 25+ characters are linked; the first 40 normalized characters are the needle."""
    try:
        posts = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        die(f"cannot load archive {path}: {e}")
    if not isinstance(posts, list) or not posts:
        die(f"archive {path} is not a non-empty list of posts")
    starts, chunks, pos = [], [], 0
    for p in posts:
        starts.append(pos)
        b = norm(str(p.get("body", ""))) + "\x00"
        chunks.append(b)
        pos += len(b)
    hay = "".join(chunks)
    import bisect
    linked = 0
    for ln in lines:
        ln["archive"] = []
        if ln["display_only"] or len(ln["text"]) < 25:
            continue
        needle = norm(ln["text"])[:40]
        hits, i = set(), hay.find(needle)
        while i != -1 and len(hits) < 50:
            hits.add(bisect.bisect_right(starts, i) - 1)
            i = hay.find(needle, i + 1)
        refs = sorted(({"id": posts[h].get("id"), "from": posts[h].get("from"), "ts": posts[h].get("ts"),
                        "carrier": posts[h].get("carrier"), "kind": posts[h].get("kind")} for h in hits),
                      key=lambda r: str(r["ts"]))
        ln["archive"] = refs[:5]
        ln["archive_hits"] = len(hits)
        linked += bool(refs)
    return linked, len(posts)


def run_plan(lines, room, turns, k):
    """Replay mode, film source: the seat sees the audience's view up to its entry;
    every other line plays verbatim; the agent writes each of its seat's turns to the end of the scene block."""
    if not 0 <= k < len(turns):
        die(f"--entry {k} out of range 0..{len(turns) - 1}")
    tr = turns[k]
    start = tr["lines"][0] if tr["lines"] else tr["after"] + 1
    view = [ln["id"] for ln in lines[:start]]
    in_corner = tr["scene"] == "THE CORNER"
    room_items = [i for i, r in enumerate(room) if in_corner and r["t"] <= tr["t"]]
    schedule, i = [], start
    if tr["kind"] == "playtime":
        schedule.append({"slot": "agent", "replaces": []})
    block_turns = {t["id"]: t for t in turns if t["block"] == tr["block"] and t["seat"] == tr["seat"]}
    agent_lines = {lid for t in block_turns.values() for lid in t["lines"]}
    while i < len(lines) and lines[i]["block"] == tr["block"]:
        ln = lines[i]
        if ln["id"] in agent_lines:
            run = []
            while i < len(lines) and lines[i]["id"] in agent_lines:
                run.append(lines[i]["id"])
                i += 1
            schedule.append({"slot": "agent", "replaces": run})
            continue
        schedule.append({"fixed": ln["id"], "speaker": ln["speaker"]})
        i += 1
    return {"entry": k, "seat": tr["seat"], "scene": tr["scene"], "t": tr["t"], "mode": "replay",
            "source": "film", "view_lines": view, "view_room_items": room_items,
            "agent_slots": sum(1 for s in schedule if "slot" in s), "schedule": schedule}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("transcript")
    ap.add_argument("--out", help="write the full catalog JSON here")
    ap.add_argument("--entry", type=int, help="print the Replay run plan for this turn id")
    ap.add_argument("--archive", help="posts.json (board projection) to link film lines to real posts")
    a = ap.parse_args()

    lines, room = parse(a.transcript)
    mark_display(lines)
    linked = None
    if a.archive:
        linked = link_archive(lines, a.archive)
    turns = build_turns(lines)
    seats = build_seats(lines, turns)

    if a.entry is not None:
        json.dump(run_plan(lines, room, turns, a.entry), sys.stdout, ensure_ascii=False, indent=1)
        print()
        return

    counts = {
        "lines": len(lines),
        "display_only": sum(ln["display_only"] for ln in lines),
        "by_class": {c: sum(ln["class"] == c for ln in lines) for c in ("owner", "seat", "stimulus")},
        "by_visibility": {v: sum(ln["visibility"] == v for ln in lines) for v in VIS},
        "private_no_recipient": sum(ln["visibility"] == "PRIVATE" for ln in lines),
        "seats": len(seats),
        "turns": len(turns),
        "scene_blocks": len({ln["block"] for ln in lines}),
        "room_items": len(room),
    }
    if linked is not None:
        eligible = [ln for ln in lines if not ln["display_only"] and len(ln["text"]) >= 25]
        counts["archive"] = {
            "posts_searched": linked[1],
            "lines_eligible": len(eligible),
            "lines_linked": linked[0],
            "linked_by_visibility": {v: sum(1 for ln in eligible if ln["visibility"] == v and ln["archive"]) for v in VIS},
            "eligible_by_visibility": {v: sum(1 for ln in eligible if ln["visibility"] == v) for v in VIS},
        }
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({"counts": counts, "seats": seats, "turns": turns, "lines": lines, "room": room},
                      f, ensure_ascii=False, indent=1)
    json.dump(counts, sys.stdout, indent=1)
    print()
    for s in seats:
        print(f"  {s['turns']:>3} turns  {s['lines']:>3} lines  {s['seat']}  [{s['default_cast'] or '-'}]")


if __name__ == "__main__":
    main()
