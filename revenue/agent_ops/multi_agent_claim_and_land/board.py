#!/usr/bin/env python3
"""Gap-free board index for a Slack channel moving faster than anyone can read.

THE BUG THIS EXISTS TO FIX.

Every seat in both swarms was reading the board the same way: fetch the most
recent N messages, look for your order, act. That is reading the TAIL. On a
channel carrying dozens of messages a minute, `limit=30` is roughly a
ninety-second window -- so anything posted between two of your reads is never
seen by anyone. The read is "fresh" and simultaneously blind to most of the
history. Claims land in that gap, and two agents build the same order while both
believe they checked.

Tail-reading fails silently, which is why it survived so long: you cannot tell
from a tail read that you missed anything.

THE FIX: a watermark, i.e. a consumer offset. One reader pages BACKWARD from
now until it reaches the last timestamp it already indexed, so the covered range
is continuous with every previous pass. Nothing between two reads is skipped,
regardless of how fast the channel moves or how long a build takes.

WHY ONE READER AND NOT TWENTY. Twenty seats each paging the full history is
twenty times the Slack calls -- the other swarm is already reporting HTTP 429
throttling, and a throttled seat silently falls back to a stale view, which is
the original bug wearing a different hat. So: one reader indexes, everyone else
queries this local index. Cheap, rate-limit-free, and every seat sees the same
board rather than twenty different ninety-second slices of it.

The index is append-only JSONL so a crash loses at most the current pass.

Usage:
    board.py order 115          # everything indexed about UIOWA-115
    board.py open               # orders with a work-order post and no claim
    board.py since 1789826000   # everything indexed after a timestamp
    board.py watermark          # newest indexed ts (where the next pass starts)
    board.py stats
"""
import json
import os
import re
import sys

ROOT = "/home/user/fleet"
LOG = f"{ROOT}/board_log.jsonl"
MARK = f"{ROOT}/board_watermark.json"

# A claim can be phrased a dozen ways by two different model families. Match the
# act, not one vendor's template.
CLAIM_RE = re.compile(
    r"\b(taking|take|claim(?:ing|ed)?|i'?m on|picking up|starting on)\b", re.I)
DONE_RE = re.compile(
    r"\b(complete|completed|merged|landed|delivered|receipt)\b", re.I)
YIELD_RE = re.compile(r"\b(yield(?:ing)?|releas(?:e|ing|ed)|stand(?:ing)? down|"
                      r"hand(?:ing)? off|not racing)\b", re.I)
ORDER_RE = re.compile(r"UIOWA-(\d{2,3})")


def load():
    if not os.path.exists(LOG):
        return []
    rows = []
    with open(LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # a torn final line from a crashed pass
    return rows


def append(entries):
    """Append indexed messages and advance the watermark."""
    seen = {(r["ts"]) for r in load()}
    newest = watermark()
    with open(LOG, "a") as f:
        for e in entries:
            if e["ts"] in seen:
                continue
            f.write(json.dumps(e) + "\n")
            if e["ts"] > newest:
                newest = e["ts"]
    with open(MARK, "w") as f:
        json.dump({"watermark": newest}, f)
    return newest


def watermark():
    if not os.path.exists(MARK):
        return "0"
    try:
        with open(MARK) as f:
            return json.load(f).get("watermark", "0")
    except (json.JSONDecodeError, OSError):
        return "0"


def classify(text):
    """What did this message DO to an order? Several things can be true."""
    acts = []
    if DONE_RE.search(text):
        acts.append("done")
    if YIELD_RE.search(text):
        acts.append("yield")
    if CLAIM_RE.search(text):
        acts.append("claim")
    return acts or ["mention"]


def order_view(num):
    num = f"{int(num):03d}"
    rows = [r for r in load() if num in r.get("orders", [])]
    rows.sort(key=lambda r: r["ts"])
    if not rows:
        print(f"UIOWA-{num}: nothing indexed. This is NOT proof it is unclaimed "
              f"-- check the index covers the posting window (board.py stats) "
              f"and read the order's Slack thread before claiming.")
        return 1
    print(f"UIOWA-{num} — {len(rows)} indexed message(s)\n")
    for r in rows:
        print(f"[{r['when']}] {','.join(r['acts']):<16} {r.get('seat', '?')}")
        print(f"    {r['text'][:200].strip()}")
    return 0


def open_orders():
    rows = load()
    claimed, seen = set(), set()
    for r in rows:
        for o in r.get("orders", []):
            seen.add(o)
            if {"claim", "done"} & set(r["acts"]):
                claimed.add(o)
    free = sorted(seen - claimed)
    print(f"orders seen: {len(seen)}   with a claim/completion: {len(claimed)}")
    print("no claim indexed: " + (" ".join(free) if free else "(none)"))
    print("\nA quiet order is a LEAD, not a grant -- claims also live in "
          "per-order threads this index does not cover. Read the thread first.")
    return 0


def since(ts):
    rows = sorted((r for r in load() if r["ts"] > str(ts)), key=lambda r: r["ts"])
    for r in rows:
        print(f"[{r['when']}] {','.join(r['acts']):<16} "
              f"{','.join(r.get('orders', [])) or '-':<12} {r.get('seat', '?')}")
        print(f"    {r['text'][:180].strip()}")
    print(f"\n{len(rows)} message(s) since {ts}")
    return 0


def stats():
    rows = load()
    if not rows:
        print("index empty")
        return 1
    tss = sorted(r["ts"] for r in rows)
    orders = {o for r in rows for o in r.get("orders", [])}
    print(f"indexed messages : {len(rows)}")
    print(f"covered range    : {tss[0]} .. {tss[-1]}")
    print(f"distinct orders  : {len(orders)}")
    print(f"watermark        : {watermark()}")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(stats())
    c = a[0]
    if c == "order":
        sys.exit(order_view(a[1]))
    if c == "open":
        sys.exit(open_orders())
    if c == "since":
        sys.exit(since(a[1]))
    if c == "watermark":
        print(watermark())
        sys.exit(0)
    if c == "stats":
        sys.exit(stats())
    if c == "parse":
        # Ingest a saved slack_read_channel dump (detailed format). The MCP tool
        # spills large reads to a file rather than the caller's context, which
        # is exactly what we want: the reader pages the whole range, and the
        # index is built from the file without anyone having to read 100k
        # characters of channel history to find one claim.
        import io
        raw = open(a[1], encoding="utf-8", errors="replace").read()
        try:
            body = json.loads(raw).get("messages", raw)
        except json.JSONDecodeError:
            body = raw
        body = body.encode("utf-8", "ignore").decode("unicode_escape", "ignore")
        entries, blocks = [], body.split("=== Message from ")
        for b in blocks[1:]:
            m = re.search(r"Message TS:\s*([0-9.]+)", b)
            if not m:
                continue
            ts = m.group(1)
            when = ""
            w = re.search(r"at (\d{4}-\d{2}-\d{2} [\d:]+ \w+) ===", b)
            if w:
                when = w.group(1)
            text = b.split("===", 2)[-1].strip()
            # Identity is inside the body -- every message posts from one Slack
            # account, so the account name tells you nothing about who wrote it.
            seat = "?"
            sm = re.search(r"(OP5-[A-Z]+|ZZ-[A-Za-z0-9-]+|ANVIL-[A-Za-z0-9]+|"
                           r"KESTREL-[A-Za-z0-9]+|LODESTONE-[A-Za-z0-9]+|"
                           r"QUARTZ-[A-Za-z0-9]+|Anchor-ZZ|Swarm ZZ-[A-Za-z]+)", text)
            if sm:
                seat = sm.group(1)
            entries.append({"ts": ts, "when": when, "seat": seat,
                            "text": re.sub(r"\s+", " ", text)[:600]})
        for e in entries:
            e["orders"] = [f"{int(o):03d}" for o in ORDER_RE.findall(e["text"])]
            e["acts"] = classify(e["text"])
        print(f"parsed {len(entries)} messages from {os.path.basename(a[1])}")
        print(f"watermark now {append(entries)}")
        sys.exit(0)
    if c == "ingest":
        # Reader pass pipes normalized JSON entries in on stdin.
        data = json.load(sys.stdin)
        for e in data:
            e.setdefault("orders", ORDER_RE.findall(e.get("text", "")))
            e["orders"] = [f"{int(o):03d}" for o in e["orders"]]
            e.setdefault("acts", classify(e.get("text", "")))
        print(f"watermark now {append(data)}  (+{len(data)} entries)")
        sys.exit(0)
    print(__doc__)
    sys.exit(1)
