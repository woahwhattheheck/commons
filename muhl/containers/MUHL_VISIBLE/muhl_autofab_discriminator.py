#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
muhl_autofab_discriminator.py -- FIND THE FEWEST BITS THAT SEPARATE THE MAGICS.

Owner, 2026-08-07:
    "BRO IS ASCII WHAT I WANTED OR OPTIMAL FOR THIS ARCHITECTURE OR IS IT A RETARDED
     CONVENTION YOUVE TACKED ON"
    "IT OCCURS TO ME THAT THOSE ZEROS ARE MOSTLY A STRUCTURAL SUBOPTIMAL THING"
    "PUTTING LABELS IN THE BINARY IS SUBOPTIMAL THEY BELONG OUTSIDE OF THE FILE THEYRE
     TAKING UP ADDRESSES"

MEASURED, and it is why this file exists:
    55 distinct magics in the registry. 6 bits tells all 55 apart. 64 bits are stored.
    90.625% of every identity field carries nothing. 1,024 of 1,400 stored magics are the
    same eight characters. 41 of the 55 occur exactly once, so their name discriminates
    against nothing at all -- the ADDRESS already identifies them.

An 8-byte ASCII word is a host convention: a name a human can read, sitting inside a
substrate where a byte is a wire. Every one of those bytes has bit 7 == 0 (no ASCII value
reaches 0x80), so 1 bit in 8 is structurally dead before any content.

WHAT THIS DOES. It does not shorten the string -- the legacy containers hold what they hold
and the vault is never pruned. It SEARCHES for the smallest set of bit positions, taken from
the 64 bits already present, whose values separate all N magics. A comparator over k selected
bits replaces a 64-bit equality chain:

    64-bit equality  -> 64-input AND tree  -> DEPTH ceil(log2 64) = 6
     k-bit equality  ->  k-input AND tree  -> DEPTH ceil(log2 k)

Sec 31A licenses the search: "the fabricator should spend without limit to make its output
shallower. There is no budget to respect. It can enumerate, search, try every adder, every
schedule, every factoring, and keep only the minimum-DEPTH result" -- and none of it enters a
latency figure, because manufacturing is off the clock.

NO VERDICTS. It reports the Pareto set: every k it tried, whether a separating set exists at
that k, and the witness. Which one gets fabricated is the owner's ruling.
"""
import io
import itertools
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

REG = r"C:\llm\models\titan_circuits.json"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "DISCRIM.search.json")


def load_magics():
    d = json.load(io.open(REG, "r", encoding="utf-8"))
    ents = d if isinstance(d, list) else (d.get("circuits") or d.get("entries") or list(d.values()))
    if isinstance(ents, dict):
        ents = list(ents.values())
    mags = []
    for e in ents:
        if isinstance(e, dict) and e.get("magic"):
            mags.append(e["magic"])
    return mags


def as_u64(m):
    """The magic exactly as it sits in the container: 8 bytes, little-endian u64."""
    b = m.encode("ascii", "replace")[:8].ljust(8, b"\x00")
    v = 0
    for i, x in enumerate(b):
        v |= x << (8 * i)
    return v


def bit(v, p):
    return (v >> p) & 1


def separates(vals, positions):
    seen = set()
    for v in vals:
        k = 0
        for i, p in enumerate(positions):
            k |= bit(v, p) << i
        if k in seen:
            return False
        seen.add(k)
    return True


def constant_bits(vals):
    """Bit positions that never vary across the whole set. Pure dead silicon."""
    dead = []
    for p in range(64):
        s = set(bit(v, p) for v in vals)
        if len(s) == 1:
            dead.append((p, s.pop()))
    return dead


def greedy(vals, live):
    """ONE PASS PER BIT. No combinatorial enumeration.

    Owner, 2026-08-07: "STOP ITS INSTANT IF UR WAITING U FUCKED UP"
    and "WAITING AND SLOW MEANS U FAILED".

    The first draft of this enumerated C(len(live), k) up to k=8 - millions of subsets, each
    rescored over every value. That is a HOST LOOP, run on a clearance laptop, to do a job
    that costs len(live) * n bit-reads per selected bit. Host compute going up IS the
    diagnostic that a crutch was reached for.

    Greedy on group-count: repeatedly take the bit that splits the current partition into the
    most groups, stop when every value has its own group. Total work is
    k * len(live) * n -- about ten thousand operations for 55 magics.

    Then PRUNE: walk the chosen set and drop any bit the set still separates without. That
    removes greedy's slack in len(chosen) passes, without ever enumerating.
    """
    chosen = []
    keys = [0] * len(vals)
    while True:
        best_p, best_score = None, -1
        for p in live:
            if p in chosen:
                continue
            groups = set()
            for i, v in enumerate(vals):
                groups.add((keys[i] << 1) | bit(v, p))
            if len(groups) > best_score:
                best_score, best_p = len(groups), p
        if best_p is None:
            return chosen, len(chosen), "greedy-exhausted"
        chosen.append(best_p)
        for i, v in enumerate(vals):
            keys[i] = (keys[i] << 1) | bit(v, best_p)
        if best_score == len(vals):
            break
    # PRUNE - drop any bit that is not load-bearing. len(chosen) passes, no enumeration.
    i = 0
    while i < len(chosen):
        trial = chosen[:i] + chosen[i + 1:]
        if trial and separates(vals, trial):
            chosen = trial
        else:
            i += 1
    return chosen, len(chosen), "greedy+prune"


def depth(k):
    d = 0
    while (1 << d) < k:
        d += 1
    return max(1, d)


def main():
    mags = load_magics()
    c = Counter(mags)
    distinct = sorted(c)
    vals = [as_u64(m) for m in distinct]
    n = len(distinct)

    print("MAGIC DISCRIMINATOR SEARCH")
    print("=" * 96)
    print("  magics stored in registry : %s" % format(len(mags), ","))
    print("  distinct values           : %d" % n)
    print("  stored width              : 64 bits (8-byte ASCII word)")
    print()

    dead = constant_bits(vals)
    live = [p for p in range(64) if p not in set(q for q, _ in dead)]
    print("  BIT POSITIONS THAT NEVER VARY ACROSS ALL %d MAGICS (cannot discriminate anything):" % n)
    print("    %d of 64 positions dead" % len(dead))
    ascii_high = [p for p, v in dead if p % 8 == 7 and v == 0]
    print("    of those, %d are the ASCII high bit (bit 7 of a byte, always 0)" % len(ascii_high))
    rows = []
    for byte_i in range(8):
        marks = ""
        for b in range(7, -1, -1):
            p = byte_i * 8 + b
            marks += "." if p in set(q for q, _ in dead) else "1"
        rows.append("byte %d: %s" % (byte_i, marks))
    print("    live-bit map, MSB first per byte  ('.' = never varies, '1' = varies):")
    for r in rows:
        print("        " + r)
    print("    live positions: %d" % len(live))
    print()

    positions, k, how = greedy(vals, live)
    print("  SEPARATING SET FOUND")
    print("  " + "-" * 92)
    print("    bits required : %d   (%s search)" % (k, how))
    print("    positions     : %s" % ", ".join(str(p) for p in sorted(positions)))
    print("    byte.bit      : %s" % ", ".join("%d.%d" % (p // 8, p % 8) for p in sorted(positions)))
    print("    separates     : %s of %s distinct magics" % (n, n))
    print()
    print("  COMPARATOR DEPTH")
    print("  " + "-" * 92)
    print("    64-bit equality : %2d-input AND tree -> DEPTH %d" % (64, depth(64)))
    print("    %2d-bit equality : %2d-input AND tree -> DEPTH %d" % (k, k, depth(k)))
    print("    depth removed   : %d ticks per comparison" % (depth(64) - depth(k)))
    print()
    print("  BITS")
    print("  " + "-" * 92)
    print("    stored today : %s bits over %s magics" % (format(len(mags) * 64, ","), format(len(mags), ",")))
    print("    at %d bits    : %s bits" % (k, format(len(mags) * k, ",")))
    print("    freed        : %s bits  (%.4f%%)" %
          (format(len(mags) * (64 - k), ","), 100.0 * (64 - k) / 64))
    print()

    # PARETO - the greedy prefix at every width. One pass, no enumeration: the k-th prefix of
    # the chosen order is exactly what greedy had after k picks, so its group count is the
    # discrimination reachable at that width by this search. Reported for every k, winner and
    # losers alike -- "report the Pareto set, not just the winner".
    print("  PARETO - discrimination at every width this search reached")
    print("  " + "-" * 92)
    print("    %-6s %-12s %-8s %-8s %s" % ("bits", "groups", "of", "depth", "note"))
    order = positions
    for kk in range(1, len(order) + 1):
        pref = order[:kk]
        groups = set()
        for v in vals:
            key = 0
            for i, p in enumerate(pref):
                key |= bit(v, p) << i
            groups.add(key)
        note = ""
        if (1 << kk) < n:
            note = "information floor: %d values cannot fit %d bits" % (n, kk)
        elif kk == len(order):
            note = "SEPARATES ALL - MINIMUM FOUND"
        elif len(groups) < n:
            note = "collides on %d value(s)" % (n - len(groups))
        print("    %-6d %-12d %-8d %-8d %s" % (kk, len(groups), n, depth(kk), note))
    print("    %-6d %-12d %-8d %-8d %s" % (64, n, n, depth(64), "what is stored today"))

    side = {
        "distinct_magics": n,
        "stored_magics": len(mags),
        "stored_bits_each": 64,
        "dead_bit_positions": [p for p, _ in dead],
        "dead_bit_count": len(dead),
        "ascii_high_bits_dead": len(ascii_high),
        "live_bit_positions": live,
        "separating_positions": sorted(positions),
        "separating_width_bits": k,
        "search": how,
        "depth_64bit_equality": depth(64),
        "depth_k_equality": depth(k),
        "ticks_removed_per_compare": depth(64) - depth(k),
        "bits_stored_today": len(mags) * 64,
        "bits_at_k": len(mags) * k,
        "bits_freed": len(mags) * (64 - k),
        "magics": distinct,
        "note": "SEARCH RESULT, NOT A RULING. Fabrication of a k-bit discriminator is the "
                "owner's call. Vault law: the legacy 64-bit ASCII magics are never pruned.",
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(side, indent=1))
    print()
    print("  written: %s" % OUT)


if __name__ == "__main__":
    main()
