#!/usr/bin/env python3
"""nring2 N-fill: journal NEW genome first, then OR 1s onto ram.fwd / ram.rev.

Law:
  new = old | mask. NEVER write a byte with fewer ones.
  Touch ONLY ram.fwd and ram.rev.
  Masks come from the live bits (zero cells), not a 0x01 inject.
  No recv, carry, gates, tick, fold, clocks. No pulse.
"""
import json
import os
import sys

TITAN = "C:/llm/models/titan.gguf"
REG = "C:/llm/models/titan_circuits.json"
GENOME = "C:/llm/models/titan_nring2_n_fill_genome.jsonl"
RESULT = "C:/Users/lucys/Desktop/MUHL_GO/nring2_n_fill_result.json"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass


def ones_byte(b):
    n = 0
    x = b
    while x:
        n += x & 1
        x >>= 1
    return n


def ones_blob(blob):
    t = 0
    for b in blob:
        t += ones_byte(b)
    return t


def mask_from_bits(old):
    """OR-mask = the zero bits in this span. Packed byte -> 0x00 (no-op)."""
    return bytes((~b) & 0xFF for b in old)


def or_span(old, mask):
    out = bytearray(len(old))
    for i in range(len(old)):
        nxt = old[i] | mask[i]
        if ones_byte(nxt) < ones_byte(old[i]):
            return None, "ones drop at byte %d: 0x%02x -> 0x%02x" % (i, old[i], nxt)
        out[i] = nxt
    return bytes(out), None


def bits_line(blob):
    return " ".join(format(b, "08b") for b in blob)


def load_named_rings(reg):
    names = []
    for k in reg:
        if k.startswith("nring2_") and k[7:].isdigit():
            names.append(k)
    names.sort(key=lambda s: int(s.split("_")[1]))
    return names


def main():
    if not os.path.isfile(REG):
        print("FAIL CLOSED: registry missing")
        return 1
    if not os.path.isfile(TITAN):
        print("FAIL CLOSED: titan missing")
        return 1
    if os.path.exists(GENOME):
        print("FAIL CLOSED: genome already exists (will not edit): %s" % GENOME)
        return 1

    with open(REG, encoding="utf-8") as f:
        reg = json.load(f)
    names = load_named_rings(reg)
    print("named nring2_NNN: %d" % len(names))

    placements = []
    skipped = []
    focus = ("nring2_000", "nring2_001", "nring2_003", "nring2_511", "nring2_1023")

    with open(TITAN, "rb", buffering=0) as tf:
        for name in names:
            e = reg[name]
            ram = e.get("ram")
            if not isinstance(ram, dict) or ram.get("fwd") is None or ram.get("rev") is None:
                print("FAIL CLOSED: %s missing ram.fwd/rev" % name)
                return 1
            cells = int(e.get("cells") or 0)
            if cells <= 0:
                print("FAIL CLOSED: %s cells=%s" % (name, e.get("cells")))
                return 1
            for sense, key in (("fwd", "fwd"), ("rev", "rev")):
                off = int(ram[key])
                if off < 0:
                    print("FAIL CLOSED: %s %s negative offset" % (name, sense))
                    return 1
                tf.seek(off)
                old = tf.read(cells)
                if len(old) != cells:
                    print("FAIL CLOSED: short read %s.%s" % (name, sense))
                    return 1
                before = ones_blob(old)
                cap = cells * 8
                if before == cap:
                    skipped.append({
                        "name": name, "sense": sense, "off": off,
                        "cells": cells, "ones": before, "why": "already packed",
                    })
                    continue
                mask = mask_from_bits(old)
                new, err = or_span(old, mask)
                if err:
                    print("FAIL CLOSED: %s.%s %s" % (name, sense, err))
                    return 1
                after = ones_blob(new)
                if after < before:
                    print("FAIL CLOSED: %s.%s ones drop %d -> %d" % (name, sense, before, after))
                    return 1
                if new == old:
                    skipped.append({
                        "name": name, "sense": sense, "off": off,
                        "cells": cells, "ones": before, "why": "mask no-op",
                    })
                    continue
                placements.append({
                    "name": name,
                    "sense": sense,
                    "off": off,
                    "cells": cells,
                    "old": old,
                    "mask": mask,
                    "new": new,
                    "ones_before": before,
                    "ones_after": after,
                    "ones_added": after - before,
                })

    print("spans to fill: %d" % len(placements))
    print("spans skipped packed/noop: %d" % len(skipped))
    print("FOCUS bits-before-write:")
    for p in placements:
        if p["name"] in focus:
            print("  %s.%s @ %d  ones %d -> %d" % (
                p["name"], p["sense"], p["off"], p["ones_before"], p["ones_after"]))
            print("    old  %s" % bits_line(p["old"]))
            print("    mask %s" % bits_line(p["mask"]))
            print("    new  %s" % bits_line(p["new"]))

    # JOURNAL FIRST — entire pre-image set, fsync, then (and only then) write titan.
    print("journaling %d spans -> %s" % (len(placements), GENOME))
    with open(GENOME, "w", encoding="utf-8") as gg:
        for p in placements:
            gg.write(json.dumps({
                "off": p["off"],
                "len": p["cells"],
                "name": "%s.ram.%s" % (p["name"], p["sense"]),
                "orig": p["old"].hex(),
                "mask": p["mask"].hex(),
                "ones_before": p["ones_before"],
                "ones_after": p["ones_after"],
                "tool": "nring2_n_fill",
            }) + "\n")
        gg.flush()
        os.fsync(gg.fileno())
    print("genome fsynced. writing titan OR-only.")

    wrote = 0
    with open(TITAN, "r+b") as f:
        for p in placements:
            f.seek(p["off"])
            live = f.read(p["cells"])
            if live != p["old"]:
                print("FAIL CLOSED: %s.%s bits moved under us before write" % (p["name"], p["sense"]))
                return 1
            merged, err = or_span(live, p["mask"])
            if err:
                print("FAIL CLOSED: %s.%s %s" % (p["name"], p["sense"], err))
                return 1
            if ones_blob(merged) < ones_blob(live):
                print("FAIL CLOSED: refuse fewer ones %s.%s" % (p["name"], p["sense"]))
                return 1
            f.seek(p["off"])
            f.write(merged)
            wrote += 1
        f.flush()
        os.fsync(f.fileno())
    print("wrote %d spans, titan fsynced." % wrote)

    # read-back: ones only up, bytes == old|mask
    bad = 0
    verified = []
    with open(TITAN, "rb", buffering=0) as tf:
        for p in placements:
            tf.seek(p["off"])
            got = tf.read(p["cells"])
            want = p["new"]
            go = ones_blob(got)
            if go < p["ones_before"]:
                print("FAIL: %s.%s ones dropped on readback %d < %d" % (
                    p["name"], p["sense"], go, p["ones_before"]))
                bad += 1
            if got != want:
                print("FAIL: %s.%s readback != old|mask" % (p["name"], p["sense"]))
                bad += 1
            verified.append({
                "name": p["name"],
                "sense": p["sense"],
                "off": p["off"],
                "cells": p["cells"],
                "ones_before": p["ones_before"],
                "ones_after": go,
                "ones_added": go - p["ones_before"],
                "old_hex": p["old"].hex(),
                "mask_hex": p["mask"].hex(),
                "new_hex": got.hex(),
            })
    if bad:
        print("FAIL CLOSED: %d readback errors" % bad)
        return 1

    result = {
        "titan": TITAN,
        "reg": REG,
        "genome": GENOME,
        "named_rings": len(names),
        "spans_filled": len(verified),
        "spans_skipped": skipped,
        "ones_added_total": sum(v["ones_added"] for v in verified),
        "filled": verified,
    }
    with open(RESULT, "w", encoding="utf-8") as o:
        json.dump(result, o)
        o.write("\n")
    print("readback OK. ones added total: %d" % result["ones_added_total"])
    print("result: %s" % RESULT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
